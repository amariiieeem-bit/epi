"""Our own wrist recordings of look-alike movements (report §3 table, §5.1, §5.6).

Format, kept as simple as possible so any phone/watch logging app can produce it:

    data/lookalike/<activity>__<free text>.csv     one recording of one activity
        columns: t (seconds, or Unix seconds), x, y, z (g or m/s^2; detected), optional hr (bpm)

e.g. ``brushing_teeth__amine_1.csv``, ``running__park.csv``, ``bus__line12.csv``. The activity
name is what comes before the double underscore. Rows need not be at a perfectly fixed rate:
the signal is interpolated on a regular grid at the median rate, then resampled to 32 Hz.

Used twice: as a false-alarm test set (alarms per hour of each activity) and, in training, as
hard negatives (``Detector.fit(..., extra_negatives=...)``). Never both for the same files.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .config import Config
from .evaluation import RunPred
from .io_seizeit2 import to_g
from .preprocessing import process_signal

ACTIVITIES = ["brushing_teeth", "clapping", "running", "shaking_bottle", "bus", "car", "shivering",
              "instrument", "tremor", "walking", "typing", "cooking"]


def read_recording(path: str | Path) -> tuple[np.ndarray, float, tuple | None]:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    t = df["t"].to_numpy(float)
    t = t - t[0]
    dt = np.median(np.diff(t))
    fs = round(1.0 / dt, 3)
    grid = np.arange(0, t[-1], 1.0 / fs)
    acc = np.column_stack([np.interp(grid, t, df[c].to_numpy(float)) for c in ("x", "y", "z")])
    hr = (t, df["hr"].to_numpy(float)) if "hr" in df else None
    return to_g(acc), fs, hr


def load_lookalikes(folder: str | Path, cfg: Config | None = None) -> list[dict]:
    """Every recording as a subject-like dict (feats, y = 0, windows, runs) named by activity."""
    cfg = cfg or Config()
    out = []
    for f in sorted(Path(folder).glob("*.csv")):
        act = f.stem.split("__")[0]
        acc, fs, hr = read_recording(f)
        d = process_signal(acc, fs, cfg.pre, hr_series=hr)
        n = len(d["t_start"])
        out.append({"subject": act, "file": f.name, "feats": d["feats"], "t_start": d["t_start"],
                    "y": np.zeros(n, np.int8), "windows": d["windows"], "mag": d["signal"][:, 3],
                    "duration_s": len(acc) / fs})
    return out


def lookalike_preds(recs: list[dict], detector, cfg: Config) -> list[RunPred]:
    empty = pd.DataFrame(columns=["onset", "offset", "convulsive", "eventType"])
    return [RunPred(r["subject"], r["file"], r["t_start"], detector.predict(r), empty, r["duration_s"],
                    r["mag"], cfg.pre.fs) for r in recs]
