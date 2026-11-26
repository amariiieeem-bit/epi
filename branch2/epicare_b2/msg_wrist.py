"""Branch 1 + Branch 2 on the same patients: the detector on My Seizure Gauge wrist data.

My Seizure Gauge (Branch 1's dataset) has a real wrist accelerometer (Empatica E4, 32 Hz, in g)
plus heart rate and EDA, for the same patients whose risk Branch 1 forecasts. Running the
SeizeIT2-trained detector there gives, per Branch 1 patient:

  * the wrist placement check of report §5.6 (a model trained on a chest sensor, run on a wrist);
  * false alarms per day of real everyday wear, with and without the Branch 1 prior;
  * the alarms the app shows in the Détection tab, under the same patient ids as Branch 1.

The prior is Branch 1's *out-of-sample* hourly risk, read from its app export (``timeline`` of
``app/data/app_data.json``): r = p1 of that hour, r_bar = mean p1 of the patient. By default the
detector runs only on that period, so every alarm has a real prior.

My Seizure Gauge seizures carry only an onset time and no type (mostly focal, recorded by an
implanted EEG): an alarm within [onset - 60 s, onset + 5 min] is reported as "near a seizure"
and not counted as false, but there is no sensitivity to compute on these patients.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .config import BRANCH2_ROOT, Config
from .decision import detect
from .preprocessing import process_signal

BRANCH1_ROOT = BRANCH2_ROOT.parent / "branch1"
NEAR_BEFORE_S, NEAR_AFTER_S = 60.0, 300.0


def _branch1():
    if str(BRANCH1_ROOT) not in sys.path:
        sys.path.insert(0, str(BRANCH1_ROOT))
    from epicare_b1 import io_msg  # noqa: WPS433
    return io_msg


def branch1_hourly_prior(b1_patient: dict, tz: str, cap: float = 1.0) -> tuple[np.ndarray, np.ndarray, float]:
    """(hour starts in Unix s, capped shift per hour, r_bar) from a Branch 1 patient block."""
    tl = b1_patient.get("timeline") or {}
    p1 = np.array([np.nan if v is None else v for v in tl.get("p1", [])], float)
    if not len(p1) or not tl.get("start"):
        return np.zeros(0), np.zeros(0), np.nan
    t0 = pd.Timestamp(tl["start"]).tz_localize(tz).tz_convert("UTC").value // 10 ** 9
    hours = t0 + 3600 * np.arange(len(p1))
    r_bar = float(np.nanmean(p1))
    shift = np.clip(np.log(np.maximum(np.nan_to_num(p1, nan=r_bar), 1e-9) / max(r_bar, 1e-9)), -cap, cap)
    return hours, shift, r_bar


def run_archive(archive_path: str | Path, final: dict, cfg: Config, b1_patient: dict | None = None,
                tz: str = "America/Chicago", period: str = "timeline", max_sessions: int | None = None,
                verbose: bool = True) -> dict:
    """Detector on every E4 session of one archive. Returns alarms (with/without prior), hours, seizures."""
    io_msg = _branch1()
    det, dec = final["detector"], final["decision"]
    hours, shift_h, r_bar = branch1_hourly_prior(b1_patient or {}, tz, cfg.decision.prior_shift_cap)
    lo, hi = (hours[0], hours[-1] + 3600) if (period == "timeline" and len(hours)) else (-np.inf, np.inf)
    rows, worn_s, n_sess = [], 0.0, 0
    with io_msg.Archive(archive_path) as arc:
        pid = arc.patient_id
        seizures = io_msg.load_seizure_times(arc)
        for ref in io_msg.list_sessions(arc):
            if max_sessions and n_sess >= max_sessions:
                break
            if ref.start > hi or ref.start + 86400 < lo:
                continue
            s = io_msg.load_session(arc, ref)
            acc = s.signals.get("ACC")
            if acc is None or len(acc.values) < acc.fs * 60:
                continue
            a0 = acc.t0
            hr = s.signals.get("HR")
            eda = s.signals.get("EDA")
            ser = lambda g: (g.t0 - a0 + np.arange(len(g.values)) / g.fs, g.values) if g is not None else None
            d = process_signal(acc.values, acc.fs, cfg.pre, hr_series=ser(hr), eda_series=ser(eda))
            if not len(d["t_start"]):
                continue
            t_abs = a0 + d["t_start"]
            keep = (t_abs >= lo) & (t_abs < hi)
            if not keep.any():
                continue
            n_sess += 1
            sub = {"feats": d["feats"][keep], "windows": d["windows"][keep]}
            p = det.predict(sub)
            ts = d["t_start"][keep]
            worn_s += len(ts) * cfg.pre.step_s
            sh = None
            if len(hours):
                k = np.clip(((t_abs[keep] - hours[0]) // 3600).astype(int), 0, len(hours) - 1)
                sh = shift_h[k]
            for use_prior in (False, True):
                al = detect(ts, p, cfg.decision, cfg.pre.window_s, cfg.pre.step_s,
                            shift=sh if use_prior else None, mag=d["signal"][:, 3], fs=cfg.pre.fs,
                            threshold=dec["threshold"], min_positive_s=dec["min_positive_s"])
                for r in al.itertuples():
                    rows.append({"prior": use_prior, "t": a0 + r.time, "confidence": r.confidence,
                                 "shift": r.shift, "still": r.still})
            if verbose and n_sess % 20 == 0:
                print(f"  {pid}: {n_sess} sessions, {worn_s / 3600:.0f} h")
    al = pd.DataFrame(rows, columns=["prior", "t", "confidence", "shift", "still"])
    if len(al):
        near = np.zeros(len(al), bool)
        for s in seizures:
            near |= (al.t >= s - NEAR_BEFORE_S) & (al.t <= s + NEAR_AFTER_S)
        al["near_seizure"] = near
    else:
        al["near_seizure"] = []
    sz_in = seizures[(seizures >= lo) & (seizures < hi)] if np.isfinite(lo) else seizures
    return {"id": pid, "alarms": al, "hours": worn_s / 3600, "seizures": sz_in, "r_bar": r_bar,
            "period": (lo, hi), "sessions": n_sess, "tz": tz}


def patient_block(run: dict) -> dict:
    """The per-patient Branch 2 block the app shows next to Branch 1 (same ``id``)."""
    tz = run["tz"]
    al = run["alarms"]
    iso = lambda t: pd.to_datetime(float(t), unit="s", utc=True).tz_convert(tz).strftime("%Y-%m-%dT%H:%M")
    days = run["hours"] / 24

    def fa(prior):
        a = al[(al.prior == prior) & ~al.near_seizure] if len(al) else al
        return round(len(a) / days, 3) if days > 0 else None

    w = al[al.prior] if len(al) else al
    lo, hi = run["period"]
    return {
        "id": str(run["id"]),
        "source": "Poignet (Empatica E4, My Seizure Gauge) · détecteur entraîné sur SeizeIT2",
        "period": {"start": iso(lo) if np.isfinite(lo) else None, "end": iso(hi) if np.isfinite(hi) else None},
        "hours_worn": round(run["hours"], 1),
        "detections": [{"time": iso(r.t), "confidence": round(float(r.confidence), 3),
                        "prior_shift_applied": round(float(r.shift), 3),
                        "true_seizure": bool(r.near_seizure), "still_after": None if pd.isna(r.still) else bool(r.still)}
                       for r in w.sort_values("t").itertuples()],
        "metrics": {"fa_per_day": fa(True), "fa_per_day_no_prior": fa(False), "sensitivity": None,
                    "n_seizures_in_period": int(len(run["seizures"])),
                    "n_alarms_near_seizure": int(w.near_seizure.sum()) if len(w) else 0,
                    "r_bar": None if not np.isfinite(run["r_bar"]) else round(run["r_bar"], 5)},
    }


def run_branch1_patients(archives: list[str | Path], final: dict, cfg: Config,
                         b1_json: str | Path = BRANCH2_ROOT.parent / "app" / "data" / "app_data.json",
                         period: str = "timeline", max_sessions: int | None = None) -> list[dict]:
    doc = json.loads(Path(b1_json).read_text(encoding="utf-8")) if Path(b1_json).exists() else {}
    b1 = (doc.get("branches") or {}).get("branch1") or {}
    by_id = {str(p["id"]): p for p in b1.get("patients", [])}
    tz = b1.get("local_tz", "America/Chicago")
    out = []
    for a in archives:
        pid = Path(a).stem.replace("Mayo_", "")
        if period == "timeline" and pid not in by_id:
            print(f"{pid}: not in Branch 1's export, skipped (use period='all')")
            continue
        r = run_archive(a, final, cfg, by_id.get(pid), tz, period, max_sessions)
        blk = patient_block(r)
        m = blk["metrics"]
        print(f"{blk['id']}: {blk['hours_worn']} h worn, FA/day {m['fa_per_day_no_prior']} -> {m['fa_per_day']} "
              f"with prior, {m['n_alarms_near_seizure']} alarm(s) near the {m['n_seizures_in_period']} seizure(s)")
        out.append(blk)
    return out
