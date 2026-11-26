"""Hand-made features of a 10 s window (report §5.3, baseline model).

Seizure movement is rhythmic (a few beats per second), long, and followed by stillness; most
everyday movements are less regular. The features measure exactly that on the dynamic
magnitude, plus a few per-axis and context features. Physiology (heart-rate change, EDA change)
is appended by ``window_feature_matrix`` when available, NaN otherwise.
"""
from __future__ import annotations

import numpy as np

ACC_FEATURES = [
    "dom_freq_hz",        # frequency of the spectral peak (0.5-12 Hz)
    "power_2_8",          # power in the 2-8 Hz band (g^2)
    "ratio_2_8",          # 2-8 Hz power / total power
    "spec_entropy",       # flat spectrum = 1, single rhythm = 0
    "peak_sharpness",     # power within +-0.3 Hz of the peak / total
    "acf_peak",           # regularity: highest autocorrelation at lags 0.12-2 s
    "acf_lag_s",          # lag of that peak (period of the rhythm)
    "rms",                # energy of the dynamic magnitude (g)
    "log_rms",
    "zero_cross_rate",    # zero crossings per second
    "p95_abs",            # 95th percentile of |magnitude| (g)
    "freq_slope",         # dominant frequency, 2nd half - 1st half (clonic jerks slow down)
    "rms_ratio_halves",   # rms 2nd half / 1st half
    "axis_rms_max",       # largest per-axis rms (g)
    "axis_corr_max",      # strongest correlation between two axes (whole-limb rhythmic jerks)
]
CONTEXT_FEATURES = ["rms_prev_30s", "rhythmic_run_s"]   # past only: no added alert delay
PHYS_FEATURES = ["hr", "hr_change", "eda_change"]


def _spectrum(x: np.ndarray, fs: float):
    """x: (n_win, w). Hann-windowed power spectrum, frequencies limited to 0.5-12 Hz."""
    w = x.shape[1]
    win = np.hanning(w)
    P = np.abs(np.fft.rfft((x - x.mean(1, keepdims=True)) * win, axis=1)) ** 2 / (win ** 2).sum() / fs
    f = np.fft.rfftfreq(w, 1 / fs)
    band = (f >= 0.5) & (f <= 12)
    return f[band], P[:, band]


def _dom(f, P):
    return f[np.argmax(P, axis=1)]


def acc_features(win: np.ndarray, fs: float) -> np.ndarray:
    """win: (n_win, 4, w) = x, y, z, dynamic magnitude. Returns (n_win, len(ACC_FEATURES))."""
    n, _, w = win.shape
    if n == 0:
        return np.zeros((0, len(ACC_FEATURES)), np.float32)
    m = win[:, 3, :].astype(np.float64)
    f, P = _spectrum(m, fs)
    tot = P.sum(1) + 1e-12
    dom = _dom(f, P)
    b28 = (f >= 2) & (f <= 8)
    df = f[1] - f[0]
    p28 = P[:, b28].sum(1) * df
    pn = P / tot[:, None]
    ent = -(pn * np.log(pn + 1e-12)).sum(1) / np.log(P.shape[1])
    near = np.abs(f[None, :] - dom[:, None]) <= 0.3
    sharp = (P * near).sum(1) / tot
    # autocorrelation regularity
    mc = m - m.mean(1, keepdims=True)
    F = np.fft.rfft(mc, n=2 * w, axis=1)
    ac = np.fft.irfft(np.abs(F) ** 2, axis=1)[:, :w]
    ac = ac / (ac[:, :1] + 1e-12)
    lo, hi = int(0.12 * fs), min(int(2.0 * fs), w - 1)
    seg = ac[:, lo:hi]
    acf_peak = seg.max(1)
    acf_lag = (seg.argmax(1) + lo) / fs
    rms = np.sqrt((m ** 2).mean(1))
    zc = (np.diff(np.signbit(m), axis=1) != 0).sum(1) / (w / fs)
    p95 = np.quantile(np.abs(m), 0.95, axis=1)
    h = w // 2
    f1, P1 = _spectrum(m[:, :h], fs)
    f2, P2 = _spectrum(m[:, h:], fs)
    slope = _dom(f2, P2) - _dom(f1, P1)
    rms1 = np.sqrt((m[:, :h] ** 2).mean(1)) + 1e-6
    rms2 = np.sqrt((m[:, h:] ** 2).mean(1)) + 1e-6
    ax = win[:, :3, :].astype(np.float64)
    ax_rms = np.sqrt((ax ** 2).mean(2)).max(1)
    axc = ax - ax.mean(2, keepdims=True)
    sd = np.sqrt((axc ** 2).sum(2)) + 1e-12
    cmax = np.zeros(n)
    for i, j in ((0, 1), (0, 2), (1, 2)):
        cmax = np.maximum(cmax, np.abs((axc[:, i] * axc[:, j]).sum(1) / (sd[:, i] * sd[:, j])))
    out = np.column_stack([dom, p28, p28 / (tot * df), ent, sharp, acf_peak, acf_lag, rms,
                           np.log(rms + 1e-6), zc, p95, slope, rms2 / rms1, ax_rms, cmax])
    return out.astype(np.float32)


def context_features(F: np.ndarray, step_s: float, rhythmic_acf: float = 0.5) -> np.ndarray:
    """Features from neighbouring windows of the same run (windows must be contiguous in time).

    rms_prev_30s: mean rms of the 30 s before (a jump from rest); rhythmic_run_s: how long the
    movement has been rhythmic up to this window. Only past windows are used, so the features
    add no delay to the alert; stillness *after* an alarm is checked in ``decision``.
    """
    n = len(F)
    rms = F[:, ACC_FEATURES.index("rms")].astype(np.float64)
    k = max(1, int(round(30 / step_s)))
    c = np.concatenate([[0], np.cumsum(rms)])
    i = np.arange(n)
    a, b = np.maximum(0, i - k), i
    prev = np.where(b > a, (c[b] - c[a]) / np.maximum(b - a, 1), np.nan)
    rhythmic = (F[:, ACC_FEATURES.index("acf_peak")] > rhythmic_acf) & \
               (F[:, ACC_FEATURES.index("ratio_2_8")] > 0.3)
    run = np.zeros(n)
    for j in range(n):
        run[j] = (run[j - 1] + step_s if j else step_s) if rhythmic[j] else 0.0
    return np.column_stack([prev, run]).astype(np.float32)


def feature_names(use_physiology: bool = True) -> list[str]:
    return ACC_FEATURES + CONTEXT_FEATURES + (PHYS_FEATURES if use_physiology else [])


def window_feature_matrix(win: np.ndarray, fs: float, step_s: float, hr=None, hr_change=None,
                          eda_change=None) -> np.ndarray:
    """All features of one run's windows, in ``feature_names(True)`` order (NaN = not measured)."""
    n = len(win)
    Fa = acc_features(win, fs)
    Fc = context_features(Fa, step_s) if n else np.zeros((0, len(CONTEXT_FEATURES)), np.float32)
    nan = np.full(n, np.nan, np.float32)
    phys = np.column_stack([nan if hr is None else hr, nan if hr_change is None else hr_change,
                            nan if eda_change is None else eda_change]).astype(np.float32)
    return np.concatenate([Fa, Fc, phys.reshape(n, 3)], axis=1)
