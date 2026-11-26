"""Event-level evaluation (report §5.6, §7).

* sensitivity per convulsive seizure: detected if an alarm falls in
  [onset - pre_margin, offset + post_margin];
* false alarms per 24 h of recording: alarms that match no seizure of any type (an alarm during
  a non-convulsive seizure is not counted as false, nor as a detection);
* delay: alarm time - seizure onset (s), for detected seizures.
Thresholds and the positive duration are tuned on validation predictions only, never on test.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import DecisionConfig, EvalConfig
from .decision import detect


@dataclass
class RunPred:
    """Detector output for one run: what the decision and the evaluation need."""
    subject: str
    run: str
    t_start: np.ndarray          # window starts (s)
    p: np.ndarray                # P(convulsive | window)
    events: pd.DataFrame         # seizures of the run (onset, offset, convulsive, eventType)
    duration_s: float            # recorded time (for false alarms per 24 h)
    mag: np.ndarray | None = None
    fs: float = 32.0
    shift: np.ndarray | None = None


def match_alarms(alarms: pd.DataFrame, events: pd.DataFrame, ecfg: EvalConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Mark each alarm (true / false / other seizure) and each convulsive seizure (detected, delay)."""
    a = alarms.copy()
    a["kind"] = "false"
    a["seizure"] = -1
    ev = events.reset_index(drop=True)
    conv = ev[ev.convulsive.astype(bool)]
    rows = []
    for i, e in conv.iterrows():
        lo, hi = e.onset - ecfg.pre_margin_s, e.offset + ecfg.post_margin_s
        hit = a.index[(a.time >= lo) & (a.time <= hi)]
        if len(hit):
            a.loc[hit, "kind"] = "true"
            a.loc[hit, "seizure"] = i
        first = a.loc[hit, "time"].min() if len(hit) else np.nan
        rows.append({"seizure": i, "eventType": e.eventType, "onset": e.onset,
                     "duration": e.offset - e.onset, "detected": bool(len(hit)),
                     "delay_s": float(first - e.onset) if len(hit) else np.nan})
    for i, e in ev[~ev.convulsive.astype(bool)].iterrows():
        m = (a.kind == "false") & (a.time >= e.onset - ecfg.pre_margin_s) & (a.time <= e.offset + ecfg.post_margin_s)
        a.loc[m, "kind"] = "other_seizure"
    cols = ["seizure", "eventType", "onset", "duration", "detected", "delay_s"]
    return a, pd.DataFrame(rows, columns=cols)


def evaluate_runs(preds: list[RunPred], dcfg: DecisionConfig, ecfg: EvalConfig, threshold=None,
                  min_positive_s=None, use_prior: bool = True, window_s=10.0, step_s=5.0) -> dict:
    """Alarms and seizure matches for all runs, plus per-subject and overall metrics."""
    all_alarms, all_sz, per = [], [], []
    for r in preds:
        al = detect(r.t_start, r.p, dcfg, window_s, step_s, shift=r.shift if use_prior else None,
                    mag=r.mag, fs=r.fs, threshold=threshold, min_positive_s=min_positive_s)
        al, sz = match_alarms(al, r.events, ecfg)
        all_alarms.append(al.assign(subject=r.subject, run=r.run))
        all_sz.append(sz.assign(subject=r.subject, run=r.run))
        per.append({"subject": r.subject, "run": r.run, "hours": r.duration_s / 3600})
    alarms = pd.concat(all_alarms, ignore_index=True) if all_alarms else pd.DataFrame()
    seiz = pd.concat(all_sz, ignore_index=True) if all_sz else pd.DataFrame()
    hours = pd.DataFrame(per)
    return {"alarms": alarms, "seizures": seiz, "hours": hours,
            "overall": summarize(alarms, seiz, hours), "per_subject": per_subject(alarms, seiz, hours)}


def summarize(alarms: pd.DataFrame, seiz: pd.DataFrame, hours: pd.DataFrame) -> dict:
    h = float(hours["hours"].sum()) if len(hours) else 0.0
    n_sz = int(len(seiz))
    n_det = int(seiz["detected"].sum()) if n_sz else 0
    n_fa = int((alarms["kind"] == "false").sum()) if len(alarms) else 0
    d = seiz.loc[seiz["detected"], "delay_s"] if n_sz else pd.Series(dtype=float)
    return {"n_seizures": n_sz, "n_detected": n_det,
            "sensitivity": n_det / n_sz if n_sz else np.nan,
            "n_false_alarms": n_fa, "hours": h,
            "fa_per_day": n_fa / h * 24 if h else np.nan,
            "delay_median_s": float(d.median()) if len(d) else np.nan,
            "delay_p90_s": float(d.quantile(0.9)) if len(d) else np.nan,
            "n_alarms": int(len(alarms))}


def per_subject(alarms, seiz, hours) -> pd.DataFrame:
    rows = []
    for s in hours["subject"].unique() if len(hours) else []:
        rows.append({"subject": s, **summarize(alarms[alarms.subject == s] if len(alarms) else alarms,
                                               seiz[seiz.subject == s] if len(seiz) else seiz,
                                               hours[hours.subject == s])})
    return pd.DataFrame(rows)


def tune_decision(preds: list[RunPred], dcfg: DecisionConfig, ecfg: EvalConfig, **kw) -> tuple[dict, pd.DataFrame]:
    """Grid search on VALIDATION predictions. Rule: the most sensitive setting whose false-alarm
    rate meets the target; if none does, the setting with the fewest false alarms per day.
    Ties are broken by fewer false alarms, then shorter delay."""
    rows = []
    for thr in dcfg.threshold_grid:
        for mp in dcfg.min_positive_grid:
            o = evaluate_runs(preds, dcfg, ecfg, threshold=thr, min_positive_s=mp, use_prior=False, **kw)["overall"]
            rows.append({"threshold": thr, "min_positive_s": mp, **o})
    g = pd.DataFrame(rows)
    ok = g[g.fa_per_day <= dcfg.target_fa_per_day]
    if len(ok) and ok.sensitivity.notna().any():
        best = ok.sort_values(["sensitivity", "fa_per_day", "delay_median_s"], ascending=[False, True, True]).iloc[0]
    else:
        best = g.sort_values(["fa_per_day", "sensitivity"], ascending=[True, False]).iloc[0]
    return {"threshold": float(best.threshold), "min_positive_s": float(best.min_positive_s)}, g


def lookalike_alarms(preds: list[RunPred], dcfg: DecisionConfig, threshold=None, min_positive_s=None,
                     window_s=10.0, step_s=5.0) -> pd.DataFrame:
    """False alarms per hour of each look-alike activity (our own recordings, report §5.6).

    Each RunPred here is one activity segment: ``subject`` = activity name, no seizures."""
    rows = []
    for r in preds:
        al = detect(r.t_start, r.p, dcfg, window_s, step_s, threshold=threshold, min_positive_s=min_positive_s)
        rows.append({"activity": r.subject, "recording": r.run, "hours": r.duration_s / 3600, "alarms": len(al)})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    g = df.groupby("activity")[["hours", "alarms"]].sum()
    g["alarms_per_hour"] = g["alarms"] / g["hours"].clip(lower=1e-9)
    return g.reset_index()
