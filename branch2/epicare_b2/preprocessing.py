"""Runs -> windows, features and labels, saved per subject (report §3 step 6, §5.2).

Output, one folder per subject in ``data/processed/<subject>/``:
    windows.npz   feats (n, F), t_start (n,), run (n,) run index, y (n,) 0/1/2, sid (n,) seizure
                  index in events.csv (-1 none), names (F,) feature names
    events.csv    seizures of all runs (run, onset, offset, eventType, convulsive)
    runs.csv      run name, recorded duration (s), accelerometer labels used, ECG present
    signal_<run>.npy   (optional, --keep-signal) the 32 Hz 4-channel signal, float16, for the CNN
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import Config, PreprocessConfig
from .features import feature_names, window_feature_matrix
from .io_seizeit2 import find_runs, load_run
from .signals import heart_rate_per_window, label_windows, make_windows, prepare_acc, r_peaks


def process_signal(acc_g: np.ndarray, fs: float, cfg: PreprocessConfig, events: pd.DataFrame | None = None,
                   ecg: np.ndarray | None = None, ecg_fs: float = 0.0, hr_series=None, eda_series=None) -> dict:
    """One continuous recording -> windows dict. Works for any source (SeizeIT2, E4, phone).

    hr_series / eda_series: optional (times_s, values) measured by the device (e.g. Empatica E4
    HR.csv and EDA.csv), times in seconds from the accelerometer start. hr_series is used when
    there is no ECG.
    """
    x = prepare_acc(acc_g, fs, cfg)
    win, t0 = make_windows(x, cfg)
    ev = events if events is not None else pd.DataFrame(columns=["onset", "offset", "convulsive", "eventType"])
    y, sid = label_windows(t0, ev, cfg)
    n_base = max(1, int(cfg.hr_baseline_s / cfg.step_s))

    def per_window(series):
        ts, v = (np.asarray(a, float) for a in series)
        lvl = np.interp(t0 + cfg.window_s / 2, ts, v, left=np.nan, right=np.nan).astype(np.float32)
        base = pd.Series(lvl).shift(1).rolling(n_base, min_periods=1).median().to_numpy()
        return lvl, (lvl - base).astype(np.float32)

    hr = hr_change = eda_change = None
    if ecg is not None and ecg_fs:
        hr, hr_change = heart_rate_per_window(t0, r_peaks(ecg, ecg_fs, cfg.ecg_min_rr_s), cfg)
    elif hr_series is not None:
        hr, hr_change = per_window(hr_series)
    if eda_series is not None:
        _, eda_change = per_window(eda_series)
    F = window_feature_matrix(win, cfg.fs, cfg.step_s, hr, hr_change, eda_change)
    return {"feats": F, "t_start": t0, "y": y, "sid": sid, "signal": x, "windows": win}


def process_subject(root: str | Path, subject: str, cfg: Config | None = None, out: str | Path | None = None,
                    keep_signal: bool = False, with_ecg: bool = True, verbose: bool = True) -> Path:
    cfg = cfg or Config()
    out = Path(out or cfg.data_processed) / subject
    out.mkdir(parents=True, exist_ok=True)
    runs = find_runs(root, [subject])
    parts, evs, info = [], [], []
    for ri, r in enumerate(runs):
        rs = load_run(r, cfg.pre.sensor_preference, with_ecg, cfg.pre.calibrate_gravity)
        if rs.acc is None:
            if verbose:
                print(f"  {r.key}: no accelerometer, skipped")
            continue
        ev = rs.events.assign(run=r.run)
        d = process_signal(rs.acc, rs.acc_fs, cfg.pre, rs.events, rs.ecg, rs.ecg_fs)
        sid = np.where(d["sid"] >= 0, d["sid"] + sum(len(e) for e in evs), -1)
        evs.append(ev)
        parts.append((d["feats"], d["t_start"], np.full(len(d["y"]), ri, np.int16), d["y"], sid))
        info.append({"run": r.run, "run_index": ri, "duration_s": len(rs.acc) / rs.acc_fs,
                     "acc_labels": "|".join(rs.acc_labels), "acc_fs": rs.acc_fs, "gravity_raw": round(rs.gravity, 4), "ecg": rs.ecg is not None,
                     "n_windows": len(d["y"]), "n_conv_windows": int((d["y"] == 1).sum())})
        if keep_signal:
            np.save(out / f"signal_{r.run}.npy", d["signal"].astype(np.float16))
        if verbose:
            n_conv = int(rs.events.convulsive.sum()) if len(rs.events) else 0
            print(f"  {r.key}: {info[-1]['duration_s'] / 3600:.1f} h, {len(rs.events)} seizures "
                  f"({n_conv} convulsive), {len(d['y'])} windows")
    if not parts:
        raise RuntimeError(f"{subject}: no usable run in {root}")
    F, T, R, Y, S = (np.concatenate(z) for z in zip(*parts))
    np.savez_compressed(out / "windows.npz", feats=F, t_start=T, run=R, y=Y, sid=S,
                        names=np.array(feature_names(True)))
    pd.concat(evs, ignore_index=True).to_csv(out / "events.csv", index=False)
    pd.DataFrame(info).to_csv(out / "runs.csv", index=False)
    (out / "preprocess.json").write_text(json.dumps(cfg.pre.__dict__, default=str, indent=1))
    return out


def process_dataset(root: str | Path, cfg: Config | None = None, subjects: list[str] | None = None,
                    out: str | Path | None = None, **kw) -> list[Path]:
    cfg = cfg or Config()
    subs = subjects or sorted({r.subject for r in find_runs(root)})
    done = []
    for s in subs:
        print(s)
        try:
            done.append(process_subject(root, s, cfg, out, **kw))
        except (RuntimeError, OSError, ValueError) as e:
            print(f"  {s}: {e}")
    return done


def load_subject(folder: str | Path) -> dict:
    folder = Path(folder)
    w = dict(np.load(folder / "windows.npz", allow_pickle=False))
    w["events"] = pd.read_csv(folder / "events.csv") if (folder / "events.csv").stat().st_size > 1 else pd.DataFrame()
    w["runs"] = pd.read_csv(folder / "runs.csv")
    w["subject"] = folder.name
    w["folder"] = folder
    return w
