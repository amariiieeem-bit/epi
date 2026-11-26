"""Signal processing (report §5.2): 32 Hz, magnitude, gravity removed, 10 s windows, 50 % overlap.

Every source (SeizeIT2 chest/neck sensor at 25 Hz, Empatica E4 wrist at 32 Hz, a phone or a
watch at 50-100 Hz) goes through the same functions, so the detector sees the same input.
"""
from __future__ import annotations

from fractions import Fraction

import numpy as np
import pandas as pd
from scipy import signal as sps

from .config import PreprocessConfig


def resample(x: np.ndarray, fs_in: float, fs_out: float) -> np.ndarray:
    """Polyphase resampling along axis 0 (exact for rational ratios, e.g. 25 -> 32 Hz)."""
    if abs(fs_in - fs_out) < 1e-6 or len(x) == 0:
        return np.asarray(x, np.float32)
    fr = Fraction(fs_out / fs_in).limit_denominator(1000)
    return sps.resample_poly(np.asarray(x, np.float64), fr.numerator, fr.denominator, axis=0).astype(np.float32)


def prepare_acc(acc_g: np.ndarray, fs_in: float, cfg: PreprocessConfig) -> np.ndarray:
    """(n, 3) accelerometer in g -> (n', 4) at cfg.fs: x, y, z high-passed + dynamic magnitude.

    The magnitude is computed on the raw axes (independent of how the sensor is worn), then its
    gravity component (~1 g) is removed by the same high-pass filter.
    """
    a = resample(np.nan_to_num(acc_g, nan=0.0), fs_in, cfg.fs)
    if len(a) < cfg.fs * 2:
        return np.zeros((0, 4), np.float32)
    mag = np.linalg.norm(a, axis=1, keepdims=True)
    x = np.concatenate([a, mag], axis=1).astype(np.float64)
    nyq = cfg.fs / 2
    sos = sps.butter(4, [cfg.highpass_hz / nyq, min(cfg.lowpass_hz / nyq, 0.99)], "bandpass", output="sos")
    return sps.sosfiltfilt(sos, x, axis=0).astype(np.float32)


def window_starts(n_samples: int, cfg: PreprocessConfig) -> np.ndarray:
    w, s = int(cfg.window_s * cfg.fs), int(cfg.step_s * cfg.fs)
    if n_samples < w:
        return np.zeros(0, int)
    return np.arange(0, n_samples - w + 1, s)


def make_windows(x: np.ndarray, cfg: PreprocessConfig) -> tuple[np.ndarray, np.ndarray]:
    """(n, c) signal -> (n_win, c, w) windows and their start times (s from the signal start)."""
    w = int(cfg.window_s * cfg.fs)
    st = window_starts(len(x), cfg)
    if len(st) == 0:
        return np.zeros((0, x.shape[1], w), np.float32), np.zeros(0)
    idx = st[:, None] + np.arange(w)[None, :]
    return np.transpose(x[idx], (0, 2, 1)).astype(np.float32), st / cfg.fs


def label_windows(t_start: np.ndarray, events: pd.DataFrame, cfg: PreprocessConfig) -> tuple[np.ndarray, np.ndarray]:
    """Per window: label (0 none, 1 convulsive, 2 other seizure) and the seizure index (-1 none)."""
    y = np.zeros(len(t_start), np.int8)
    sid = np.full(len(t_start), -1, np.int32)
    t_end = t_start + cfg.window_s
    for i, e in enumerate(events.itertuples()):
        ov = np.minimum(t_end, e.offset) - np.maximum(t_start, e.onset)
        hit = ov >= (cfg.min_overlap_s if e.convulsive else 0.0)
        if not e.convulsive:
            hit &= ov > 0
            y[hit & (y == 0)] = 2
        else:
            y[hit] = 1
        sid[hit & (sid < 0)] = i
    return y, sid


# ------------------------------------------------------------------ heart rate from ECG
def r_peaks(ecg: np.ndarray, fs: float, min_rr_s: float = 0.3) -> np.ndarray:
    """Simple QRS detector (band-pass 5-20 Hz, squared slope, adaptive threshold). Returns times (s)."""
    if ecg is None or len(ecg) < fs * 5:
        return np.zeros(0)
    nyq = fs / 2
    sos = sps.butter(3, [5 / nyq, min(20 / nyq, 0.99)], "bandpass", output="sos")
    f = sps.sosfiltfilt(sos, np.nan_to_num(ecg.astype(np.float64)))
    e = np.gradient(f) ** 2
    e = np.convolve(e, np.ones(int(0.12 * fs)) / int(0.12 * fs), mode="same")
    # threshold on a 10 s running high quantile, robust to amplitude changes
    blk = int(10 * fs)
    nb = max(1, len(e) // blk)
    q = np.array([np.quantile(e[i * blk:(i + 1) * blk], 0.98) for i in range(nb)])
    thr = 0.3 * np.repeat(q, blk)[: len(e)]
    thr = np.pad(thr, (0, len(e) - len(thr)), mode="edge")
    pk, _ = sps.find_peaks(e, height=thr, distance=int(min_rr_s * fs))
    return pk / fs


def heart_rate_per_window(t_start: np.ndarray, peaks_s: np.ndarray, cfg: PreprocessConfig) -> tuple[np.ndarray, np.ndarray]:
    """Heart rate (bpm) per window and its change from the median of the previous 5 minutes."""
    hr = np.full(len(t_start), np.nan, np.float32)
    if len(peaks_s) > 3:
        rr = np.diff(peaks_s)
        tm = peaks_s[1:]
        ok = (rr > 0.3) & (rr < 2.0)
        rr, tm = rr[ok], tm[ok]
        lo = np.searchsorted(tm, t_start)
        hi = np.searchsorted(tm, t_start + cfg.window_s)
        for i, (a, b) in enumerate(zip(lo, hi)):
            if b - a >= 3:
                hr[i] = 60.0 / np.median(rr[a:b])
    n_base = max(1, int(cfg.hr_baseline_s / cfg.step_s))
    base = pd.Series(hr).shift(1).rolling(n_base, min_periods=max(1, n_base // 4)).median().to_numpy()
    return hr, (hr - base).astype(np.float32)


def stillness_after(mag: np.ndarray, fs: float, t_s: float, dur_s: float) -> float:
    """RMS of the dynamic magnitude during ``dur_s`` seconds after time ``t_s`` (NaN if no data)."""
    a, b = int(t_s * fs), int((t_s + dur_s) * fs)
    seg = mag[a:b]
    return float(np.sqrt(np.mean(seg ** 2))) if len(seg) > fs else float("nan")
