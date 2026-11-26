"""From window probabilities to alarms (report §5.4) and the Branch 1 prior (§5.5).

    logit P(seizure | x, r) = logit P(seizure | x) + clip(log(r / r_bar), -cap, +cap)

A seizure is declared when the shifted probability stays above the threshold for
``min_positive_s`` seconds of consecutive windows. One alarm per episode (refractory period),
and at most ``max_alarms_per_hour`` alarms per hour (alert-policy rule, §6.2).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DecisionConfig


def logit(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.asarray(z, float)))


def prior_shift(r, r_bar, cap: float = 1.0) -> np.ndarray:
    """Branch 1 risk r and the patient's average risk r_bar -> capped log-odds shift."""
    r = np.maximum(np.asarray(r, float), 1e-9)
    return np.clip(np.log(r / max(float(r_bar), 1e-9)), -cap, cap)


def apply_prior(p: np.ndarray, shift: np.ndarray | float | None, cap: float = 1.0) -> np.ndarray:
    """Shift the detector's log-odds; the cap is re-applied so it can never be exceeded (§6.2)."""
    if shift is None:
        return np.asarray(p, float)
    return sigmoid(logit(p) + np.clip(shift, -cap, cap))


def detect(t_start: np.ndarray, p: np.ndarray, cfg: DecisionConfig, window_s: float = 10.0,
           step_s: float = 5.0, shift=None, mag: np.ndarray | None = None, fs: float = 32.0,
           threshold: float | None = None, min_positive_s: float | None = None) -> pd.DataFrame:
    """Alarms of one continuous run.

    Returns one row per alarm: time (s, end of the window that completed the run, i.e. when the
    alert could start), onset_est (start of the first positive window), confidence (mean shifted
    probability of the run), shift (prior shift at that time), still (stillness confirmed after
    the alarm, NaN if no signal given).
    """
    thr = cfg.threshold if threshold is None else threshold
    need = cfg.min_positive_s if min_positive_s is None else min_positive_s
    q = apply_prior(p, shift, cfg.prior_shift_cap)
    pos = q >= thr
    # number of consecutive positive windows needed: the windows must cover `need` seconds
    k = max(1, int(np.ceil(max(need - window_s, 0) / step_s)) + 1)
    out, run, last_alarm = [], 0, -np.inf
    per_hour: list[float] = []
    sh = np.zeros(len(p)) if shift is None else np.broadcast_to(np.asarray(shift, float), (len(p),))
    for i in range(len(p)):
        if i and t_start[i] - t_start[i - 1] > step_s * 1.5:   # gap in the recording
            run = 0
        run = run + 1 if pos[i] else 0
        if run < k:
            continue
        t_alarm = t_start[i] + window_s
        if t_alarm - last_alarm < cfg.refractory_s:
            continue
        per_hour = [t for t in per_hour if t_alarm - t < 3600]
        if len(per_hour) >= cfg.max_alarms_per_hour:
            continue
        j0 = i - run + 1
        still = np.nan
        if mag is not None:
            from .signals import stillness_after
            rms = stillness_after(mag, fs, t_alarm + 30.0, cfg.stillness_s)
            still = float(rms < cfg.stillness_rms_g) if np.isfinite(rms) else np.nan
        out.append({"time": float(t_alarm), "onset_est": float(t_start[j0]),
                    "confidence": float(q[j0:i + 1].mean()), "shift": float(sh[i]), "still": still})
        last_alarm = t_alarm
        per_hour.append(t_alarm)
    return pd.DataFrame(out, columns=["time", "onset_est", "confidence", "shift", "still"])
