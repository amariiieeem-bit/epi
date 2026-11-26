"""Download SeizeIT2 straight from OpenNeuro's public S3 bucket (no account, no extra package).

Only what Branch 2 needs: motion (mov), ECG and events files, optionally for chosen subjects.
Files already complete (same size) are skipped; partial files are resumed.
"""
from __future__ import annotations

import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from .config import OPENNEURO_ID

BUCKET = "https://s3.amazonaws.com/openneuro.org"
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
WANTED = re.compile(r"(_mov\.(edf|json)|_ecg\.(edf|json)|_events\.tsv|^participants\.tsv|^events\.json"
                    r"|^dataset_description\.json)$")


def list_files(prefix: str = "", dataset: str = OPENNEURO_ID) -> list[tuple[str, int]]:
    """(relative path, size in bytes) of every object under ``dataset/prefix``."""
    out, token = [], None
    while True:
        url = f"{BUCKET}?list-type=2&prefix={dataset}/{prefix}&max-keys=1000"
        if token:
            url += "&continuation-token=" + urllib.request.quote(token, safe="")
        root = ET.fromstring(urllib.request.urlopen(url, timeout=60).read())
        for c in root.iter(NS + "Contents"):
            out.append((c.find(NS + "Key").text[len(dataset) + 1:], int(c.find(NS + "Size").text)))
        nxt = root.find(NS + "NextContinuationToken")
        if nxt is None:
            return out
        token = nxt.text


def select(files, subjects=None, modalities=("mov", "ecg", "events")) -> list[tuple[str, int]]:
    keep = []
    for path, size in files:
        name = path.rsplit("/", 1)[-1]
        if not WANTED.search(name):
            continue
        if "/" in path:
            if subjects and path.split("/", 1)[0] not in subjects:
                continue
            mod = "events" if name.endswith("_events.tsv") else name.rsplit("_", 1)[-1].split(".")[0]
            if mod not in modalities:
                continue
        keep.append((path, size))
    return keep


def fetch(path: str, size: int, out: Path, dataset: str = OPENNEURO_ID, retries: int = 5) -> Path:
    dest = out / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(retries):
        have = dest.stat().st_size if dest.exists() else 0
        if have == size:
            return dest
        if have > size:
            dest.unlink(); have = 0
        req = urllib.request.Request(f"{BUCKET}/{dataset}/{path}", headers={"Range": f"bytes={have}-"} if have else {})
        try:
            with urllib.request.urlopen(req, timeout=120) as r, open(dest, "ab" if have else "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
        except OSError as e:
            print(f"  retry {attempt + 1} {path}: {e}")
            time.sleep(2 * (attempt + 1))
    if dest.stat().st_size != size:
        raise OSError(f"incomplete download: {path}")
    return dest


def download(out: str | Path, subjects=None, modalities=("mov", "ecg", "events"), dry_run: bool = False,
             workers: int = 4) -> list[Path]:
    """Download in parallel. ``subjects``: list (kept in that order), or None for all."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    out = Path(out)
    files = select(list_files(), subjects, modalities)
    if subjects:
        order = {s: i for i, s in enumerate(subjects)}
        files.sort(key=lambda f: (order.get(f[0].split("/", 1)[0], -1), f[0]))
    total = sum(s for _, s in files)
    print(f"{len(files)} files, {total / 1e9:.2f} GB -> {out}", flush=True)
    if dry_run:
        return []
    done, got = [], 0
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(fetch, p, s, out): (p, s) for p, s in files}
        for i, f in enumerate(as_completed(futs)):
            p, s = futs[f]
            done.append(f.result())
            got += s
            if s > 1e6 or i == len(files) - 1:
                print(f"  [{i + 1}/{len(files)}] {got / 1e9:.2f}/{total / 1e9:.2f} GB  {p}", flush=True)
    return done
