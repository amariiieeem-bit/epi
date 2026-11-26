"""Minimal EDF / EDF+ reader and writer (numpy only, no pyedflib needed).

SeizeIT2 stores every modality as EDF. The reader returns physical values per channel and
skips "EDF Annotations" channels. The writer exists for the synthetic dataset and the tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class EdfSignal:
    label: str
    fs: float
    unit: str
    data: np.ndarray          # physical values, float32


@dataclass
class EdfHeader:
    start: str                # "dd.mm.yy hh.mm.ss" as stored
    n_records: int
    record_s: float
    labels: list
    units: list
    fs: list                  # samples per second, per channel
    n_samples: list           # samples per record, per channel

    @property
    def duration_s(self) -> float:
        return self.n_records * self.record_s


def _field(raw: bytes, a: int, width: int, n: int) -> list[str]:
    return [raw[a + i * width: a + (i + 1) * width].decode("latin-1").strip() for i in range(n)]


def read_header(path: str | Path) -> tuple[EdfHeader, dict]:
    with open(path, "rb") as f:
        head = f.read(256)
        ns = int(head[252:256].decode().strip())
        sig = f.read(ns * 256)
    n_records = int(head[236:244].decode().strip())
    record_s = float(head[244:252].decode().strip())
    start = head[168:176].decode().strip() + " " + head[176:184].decode().strip()
    o = 0
    labels = _field(sig, o, 16, ns); o += 16 * ns
    o += 80 * ns                                    # transducer
    units = _field(sig, o, 8, ns); o += 8 * ns
    pmin = np.array(_field(sig, o, 8, ns), float); o += 8 * ns
    pmax = np.array(_field(sig, o, 8, ns), float); o += 8 * ns
    dmin = np.array(_field(sig, o, 8, ns), float); o += 8 * ns
    dmax = np.array(_field(sig, o, 8, ns), float); o += 8 * ns
    o += 80 * ns                                    # prefiltering
    nsamp = [int(x) for x in _field(sig, o, 8, ns)]
    fs = [n / record_s if record_s > 0 else float(n) for n in nsamp]
    h = EdfHeader(start, n_records, record_s, labels, units, fs, nsamp)
    scale = {"pmin": pmin, "pmax": pmax, "dmin": dmin, "dmax": dmax, "header_bytes": 256 + ns * 256}
    return h, scale


def read_edf(path: str | Path, channels: list[str] | None = None) -> tuple[EdfHeader, list[EdfSignal]]:
    """Read an EDF file. ``channels``: labels to keep (default all but annotations)."""
    h, s = read_header(path)
    rec_len = sum(h.n_samples)
    raw = np.fromfile(path, dtype="<i2", offset=s["header_bytes"])
    n_rec = min(h.n_records if h.n_records > 0 else 10 ** 12, raw.size // rec_len)
    raw = raw[: n_rec * rec_len].reshape(n_rec, rec_len)
    out, o = [], 0
    for i, lab in enumerate(h.labels):
        n = h.n_samples[i]
        keep = "annotation" not in lab.lower() and (channels is None or lab in channels)
        if keep:
            dig = raw[:, o: o + n].reshape(-1).astype(np.float32)
            span_d = s["dmax"][i] - s["dmin"][i]
            gain = (s["pmax"][i] - s["pmin"][i]) / span_d if span_d else 1.0
            phys = (dig - s["dmin"][i]) * gain + s["pmin"][i]
            out.append(EdfSignal(lab, h.fs[i], h.units[i], phys.astype(np.float32)))
        o += n
    return h, out


def write_edf(path: str | Path, signals: list[EdfSignal], record_s: float = 1.0,
              start: str = "01.01.00 00.00.00") -> Path:
    """Write signals (each with an integer number of samples per record) to a plain EDF file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ns = len(signals)
    nsamp = [int(round(sg.fs * record_s)) for sg in signals]
    n_rec = min(len(sg.data) // n for sg, n in zip(signals, nsamp))

    def pad(x, w):
        return str(x)[:w].ljust(w).encode("latin-1")

    def num(x, w=8):
        s = f"{x:.6g}"
        return pad(s if len(s) <= w else f"{x:.2e}", w)

    head = (pad("0", 8) + pad("X X X X", 80) + pad("Startdate X X X X", 80) + pad(start[:8], 8)
            + pad(start[9:17], 8) + pad(256 + ns * 256, 8) + pad("", 44) + pad(n_rec, 8)
            + pad(f"{record_s:g}", 8) + pad(ns, 4))
    pmin, pmax = [], []
    for sg in signals:
        lo, hi = float(np.min(sg.data)), float(np.max(sg.data))
        if hi - lo < 1e-9:
            lo, hi = lo - 1.0, hi + 1.0
        pmin.append(lo); pmax.append(hi)
    sig = b"".join(pad(sg.label, 16) for sg in signals) + b"".join(pad("", 80) for _ in signals)
    sig += b"".join(pad(sg.unit, 8) for sg in signals)
    sig += b"".join(num(v) for v in pmin) + b"".join(num(v) for v in pmax)
    # store back the values actually written (rounded), so scaling matches on read
    pmin = [float(num(v).decode()) for v in pmin]
    pmax = [float(num(v).decode()) for v in pmax]
    sig += b"".join(pad(-32768, 8) for _ in signals) + b"".join(pad(32767, 8) for _ in signals)
    sig += b"".join(pad("", 80) for _ in signals) + b"".join(pad(n, 8) for n in nsamp)
    sig += b"".join(pad("", 32) for _ in signals)
    blocks = []
    for sg, n, lo, hi in zip(signals, nsamp, pmin, pmax):
        x = np.clip(np.asarray(sg.data[: n_rec * n], float), lo, hi)
        d = np.round((x - lo) / (hi - lo) * 65535 - 32768).astype("<i2")
        blocks.append(d.reshape(n_rec, n))
    with open(path, "wb") as f:
        f.write(head)
        f.write(sig)
        f.write(np.concatenate(blocks, axis=1).tobytes())
    return path
