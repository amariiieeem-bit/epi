"""Synthetic dataset in the *same layout* as SeizeIT2 (BIDS, EDF, events.tsv), and synthetic
look-alike recordings in our CSV format. Purpose: run and test all of Branch 2 before the real
download. Not for any result.

Built-in ground truth:
  * convulsive seizures (eventType sz_foc_f2b): ~10 s tonic phase (small fast tremor), then
    30-90 s of very regular clonic jerks whose rate slows from ~5 to ~1.5 Hz, then post-ictal
    stillness; heart rate +30-50 bpm;
  * non-convulsive focal seizures (sz_foc_ia_nm): small slow movements, modest heart-rate rise;
  * everyday activity: rest, sleep, walking, running, plus short rhythmic look-alikes (clapping,
    shaking, brushing teeth) that the detector must ignore.
Runs are short and few (default 2 x 1 h per subject) to keep files small.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .config import SEIZEIT2_TASK
from .edf import EdfSignal, write_edf

MOV_FS, ECG_FS = 25, 256
AXES = "XYZ"
MOV_LABELS = [f"{sd} {kind} {ax}" for sd in ("EEG SD", "ECGEMG SD") for kind in ("ACC", "GYR") for ax in AXES]


@dataclass
class SynthConfig:
    subjects: tuple = ("sub-001", "sub-002", "sub-003", "sub-004", "sub-005", "sub-006",
                       "sub-097", "sub-098", "sub-099", "sub-100")
    runs_per_subject: int = 2
    run_h: float = 1.0
    convulsive_per_run: tuple = (0, 2)   # random in [a, b]
    focal_per_run: tuple = (0, 1)
    lookalike_bursts_per_h: float = 12.0
    seed: int = 0


# ------------------------------------------------------------------ motion primitives (in g)
def _rhythm(n, fs, f0, f1, amp, rng, jitter=0.0):
    """Rhythmic jerks with a frequency going linearly from f0 to f1 (Hz); 3 axes."""
    t = np.arange(n) / fs
    f = np.linspace(f0, f1, n) * (1 + jitter * np.cumsum(rng.normal(0, 0.02, n)) / np.sqrt(np.arange(1, n + 1)))
    ph = 2 * np.pi * np.cumsum(f) / fs
    jerk = np.sign(np.sin(ph)) * np.abs(np.sin(ph)) ** 0.5     # sharp, jerk-like waveform
    d = rng.normal(size=3); d /= np.linalg.norm(d)
    return amp * jerk[:, None] * d[None, :] + 0.1 * amp * rng.normal(size=(n, 3))


def _segment(kind, n, fs, rng):
    if kind == "rest":
        return rng.normal(0, 0.004, (n, 3))
    if kind == "sleep":
        return rng.normal(0, 0.002, (n, 3))
    if kind == "walk":
        f = rng.uniform(1.6, 2.1)
        return _rhythm(n, fs, f, f, rng.uniform(0.08, 0.18), rng, jitter=1.0) + rng.normal(0, 0.03, (n, 3))
    if kind == "run":
        f = rng.uniform(2.4, 3.0)
        return _rhythm(n, fs, f, f, rng.uniform(0.3, 0.6), rng, jitter=1.0) + rng.normal(0, 0.06, (n, 3))
    if kind in ("clap", "shake", "brush"):
        f = {"clap": rng.uniform(2.5, 4.0), "shake": rng.uniform(3.5, 5.5), "brush": rng.uniform(3.5, 5.0)}[kind]
        amp = {"clap": 0.15, "shake": 0.2, "brush": 0.05}[kind]
        return _rhythm(n, fs, f, f, amp * rng.uniform(0.6, 1.4), rng, jitter=2.0) + rng.normal(0, 0.03, (n, 3))
    raise ValueError(kind)


def _convulsive(fs, rng):
    tonic = int(rng.uniform(5, 15) * fs)
    clonic = int(rng.uniform(30, 90) * fs)
    post = int(rng.uniform(120, 300) * fs)
    a = [rng.normal(0, 0.03, (tonic, 3)) + _rhythm(tonic, fs, 9, 9, 0.03, rng),
         _rhythm(clonic, fs, rng.uniform(4, 5.5), rng.uniform(1.2, 2.0), rng.uniform(0.3, 0.8), rng),
         rng.normal(0, 0.0015, (post, 3))]
    return np.concatenate(a), (tonic + clonic) / fs


def _focal(fs, rng):
    n = int(rng.uniform(30, 90) * fs)
    return _rhythm(n, fs, 1.0, 0.8, 0.04, rng, jitter=3.0) + rng.normal(0, 0.01, (n, 3)), n / fs


# ------------------------------------------------------------------ one run
def make_run(cfg: SynthConfig, rng) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    n = int(cfg.run_h * 3600 * MOV_FS)
    acc = np.zeros((n, 3))
    hr = np.full(n, rng.uniform(60, 80))
    i = 0
    while i < n:   # background activity
        kind = rng.choice(["rest", "sleep", "walk", "run"], p=[0.45, 0.25, 0.22, 0.08])
        m = min(n - i, int(rng.uniform(60, 600) * MOV_FS))
        acc[i:i + m] = _segment(kind, m, MOV_FS, rng)
        hr[i:i + m] += {"rest": 0, "sleep": -8, "walk": 20, "run": 50}[kind]
        i += m
    for _ in range(rng.poisson(cfg.lookalike_bursts_per_h * cfg.run_h)):  # short look-alikes
        kind = rng.choice(["clap", "shake", "brush"])
        m = int(rng.uniform(5, 15) * MOV_FS) if kind != "brush" else int(rng.uniform(60, 120) * MOV_FS)
        s = rng.integers(0, max(1, n - m))
        acc[s:s + m] = _segment(kind, m, MOV_FS, rng)
    rows = []
    slots = rng.permutation(np.arange(300, int(cfg.run_h * 3600) - 600, 600))
    k = 0
    for typ, (a, b) in (("sz_foc_f2b", cfg.convulsive_per_run), ("sz_foc_ia_nm", cfg.focal_per_run)):
        for _ in range(rng.integers(a, b + 1)):
            if k >= len(slots):
                break
            t0 = float(slots[k] + rng.uniform(0, 60)); k += 1
            seg, dur = (_convulsive if typ == "sz_foc_f2b" else _focal)(MOV_FS, rng)
            s = int(t0 * MOV_FS); m = min(len(seg), n - s)
            acc[s:s + m] = seg[:m]
            rise = 40 if typ == "sz_foc_f2b" else 15
            ramp = np.clip(np.arange(m) / (20 * MOV_FS), 0, 1) * np.exp(-np.maximum(np.arange(m) / MOV_FS - dur, 0) / 300)
            hr[s:s + m] += rise * ramp
            rows.append({"onset": round(t0, 2), "duration": round(dur, 2), "eventType": typ})
    # gravity: a slowly turning orientation (1 g)
    th = np.cumsum(rng.normal(0, 0.0005, n)); ph = np.cumsum(rng.normal(0, 0.0005, n))
    grav = np.column_stack([np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th)])
    acc = acc + grav
    ev = pd.DataFrame(rows)
    return acc, hr, ev


def _ecg(hr_25: np.ndarray, rng) -> np.ndarray:
    n = int(len(hr_25) / MOV_FS * ECG_FS)
    hr = np.interp(np.arange(n) / ECG_FS, np.arange(len(hr_25)) / MOV_FS, hr_25)
    phase = np.cumsum(hr / 60.0 / ECG_FS)
    beats = np.flatnonzero(np.diff(np.floor(phase)) > 0)
    x = rng.normal(0, 0.03, n)
    k = np.arange(-8, 9)
    qrs = np.exp(-(k / 2.5) ** 2)
    for b in beats:
        lo, hi = max(0, b - 8), min(n, b + 9)
        x[lo:hi] += qrs[lo - b + 8: hi - b + 8]
    return x + 0.1 * np.sin(2 * np.pi * 0.25 * np.arange(n) / ECG_FS)


def make_dataset(root: str | Path, cfg: SynthConfig | None = None) -> Path:
    """Write <root>/sub-XXX/ses-01/{eeg,ecg,mov}/... and participants.tsv."""
    cfg = cfg or SynthConfig()
    root = Path(root)
    rng = np.random.default_rng(cfg.seed)
    for sub in cfg.subjects:
        for r in range(1, cfg.runs_per_subject + 1):
            acc, hr, ev = make_run(cfg, rng)
            stem = f"{sub}_ses-01_task-{SEIZEIT2_TASK}_run-{r:02d}"
            base = root / sub / "ses-01"
            other = acc + rng.normal(0, 0.01, acc.shape)         # second module (neck), same body
            gyr = rng.normal(0, 5, acc.shape)
            chans = []
            for lab in MOV_LABELS:
                src = (other if lab.startswith("EEG") else acc) if "ACC" in lab else gyr
                chans.append(EdfSignal(lab, MOV_FS, "g" if "ACC" in lab else "deg/s", src[:, AXES.index(lab[-1])]))
            write_edf(base / "mov" / f"{stem}_mov.edf", chans)
            write_edf(base / "ecg" / f"{stem}_ecg.edf", [EdfSignal("ECG", ECG_FS, "mV", _ecg(hr, rng))])
            dur = len(acc) / MOV_FS
            rows = [{"onset": 100.0, "duration": 8.0, "eventType": "impd"}] + ev.to_dict("records")
            e = pd.DataFrame(rows)
            for c, v in (("lateralization", "n/a"), ("localization", "n/a"), ("vigilance", "awake"),
                         ("confidence", "n/a"), ("channels", "n/a"), ("dateTime", "2000-01-01 00:00:00"),
                         ("recordingDuration", dur)):
                e[c] = v
            (base / "eeg").mkdir(parents=True, exist_ok=True)
            e.to_csv(base / "eeg" / f"{stem}_events.tsv", sep="\t", index=False)
    pd.DataFrame({"participant_id": list(cfg.subjects), "sex": ["f", "m"] * (len(cfg.subjects) // 2) +
                  ["f"] * (len(cfg.subjects) % 2)}).to_csv(root / "participants.tsv", sep="\t", index=False)
    return root


def make_lookalikes(folder: str | Path, seconds: float = 300.0, fs: float = 50.0, seed: int = 1) -> Path:
    """Wrist recordings of look-alike activities in our CSV format (larger amplitudes than chest)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    n = int(seconds * fs)
    spec = {"brushing_teeth": ("brush", 4.0), "clapping": ("clap", 3.0), "running": ("run", 1.0),
            "shaking_bottle": ("shake", 3.0), "walking": ("walk", 1.0)}
    for act, (kind, gain) in spec.items():
        x = np.zeros((n, 3))
        i = 0
        while i < n:   # bursts of the activity separated by rest, as a person would do it
            m = min(n - i, int(rng.uniform(20, 90) * fs))
            x[i:i + m] = _segment(kind, m, fs, rng) * gain
            i += m
            r = min(n - i, int(rng.uniform(5, 20) * fs))
            x[i:i + r] = _segment("rest", r, fs, rng)
            i += r
        x[:, 2] += 1.0
        t = np.arange(n) / fs
        pd.DataFrame({"t": t, "x": x[:, 0] * 9.80665, "y": x[:, 1] * 9.80665, "z": x[:, 2] * 9.80665}).round(4) \
            .to_csv(folder / f"{act}__synthetic.csv", index=False)
    return folder
