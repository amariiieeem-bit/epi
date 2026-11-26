"""Export Branch 2 results for the EpiCare app, in the shared schema ``epicare.app/1``.

Writes ``{"schema", "generated", "branches": {"branch2": {...}}}``. The app (``app/app.js``,
``mergeDocs``) and the Expo build (``mobile/scripts/build-web.js``) merge
``app/data/branch2.json`` with Branch 1's ``app_data.json``, so neither branch overwrites the other.

The branch2 block:
    title, dataset, model, decision      what was run
    metrics                              overall, on test patients only (sensitivity, fa_per_day, delay)
    targets                              success criteria of the report (§7)
    subjects                             per SeizeIT2 test patient, every one (honest-results rule)
    alarms                               test alarms: subject, run, t_s, confidence, kind
    prior_effect                         false alarms/day at the target sensitivity, per prior mode
    lookalike                            alarms per hour of each look-alike activity
    feature_importance                   top features of the baseline
    patients                             per Branch 1 patient id (filled when the detector runs on
                                         the same patients' wrist data; empty for SeizeIT2 alone)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .config import OPENNEURO_DOI, Config

SCHEMA = "epicare.app/1"


def _num(x, nd=3):
    if x is None:
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if not np.isfinite(x) else round(x, nd)


def _clean(o: dict) -> dict:
    return {k: (_num(v) if isinstance(v, (float, np.floating)) else int(v) if isinstance(v, (np.integer,)) else v)
            for k, v in o.items()}


def branch2_block(res: dict, cfg: Config, synthetic: bool = False, prior_table: pd.DataFrame | None = None,
                  lookalike: pd.DataFrame | None = None, importances: dict | None = None,
                  patients: list | None = None) -> dict:
    o = res["overall"]
    al = res["alarms"]
    return {
        "title": "Convulsive seizure detection",
        "dataset": {"name": "Synthetic SeizeIT2-format data (code check only)" if synthetic
                    else f"SeizeIT2 (OpenNeuro, doi:{OPENNEURO_DOI})", "synthetic": bool(synthetic),
                    "sensor": "chest/neck accelerometer (not wrist)" if not synthetic else "synthetic"},
        "model": {"kind": cfg.model.kind, "use_physiology": cfg.model.use_physiology,
                  "window_s": cfg.pre.window_s, "step_s": cfg.pre.step_s, "fs": cfg.pre.fs},
        "decision": [{"fold": d["fold"], "threshold": d["threshold"], "min_positive_s": d["min_positive_s"],
                      "n_test": len(d["test"])} for d in res["decisions"]],
        "prior_shift_cap": cfg.decision.prior_shift_cap,
        "metrics": _clean({"sensitivity": o["sensitivity"], "fa_per_day": o["fa_per_day"],
                           "delay_median_s": o["delay_median_s"], "delay_p90_s": o["delay_p90_s"],
                           "n_seizures": o["n_seizures"], "n_detected": o["n_detected"],
                           "n_false_alarms": o["n_false_alarms"], "hours": o["hours"]}),
        "targets": {"sensitivity": cfg.eval.target_sensitivity, "fa_per_day": cfg.decision.target_fa_per_day,
                    "delay_s": cfg.eval.target_delay_s},
        "subjects": [_clean(r) for r in res["per_subject"].to_dict("records")],
        "alarms": [{"subject": r.subject, "run": r.run, "t_s": _num(r.time, 1), "confidence": _num(r.confidence),
                    "prior_shift_applied": _num(r.shift), "true_seizure": r.kind == "true", "kind": r.kind}
                   for r in al.itertuples()] if len(al) else [],
        "prior_effect": [_clean(r) for r in prior_table.to_dict("records")] if prior_table is not None else None,
        "lookalike": [_clean(r) for r in lookalike.to_dict("records")] if lookalike is not None and len(lookalike) else None,
        "feature_importance": {k: _num(v, 4) for k, v in list((importances or {}).items())[:10]},
        "patients": patients or [],
    }


def export_app_data(block: dict, out_path: str | Path = "../app/data/branch2.json") -> Path:
    """Write the Branch 2 file read by the app. Other branches' blocks in it are kept."""
    out_path = Path(out_path)
    doc = {}
    if out_path.exists():
        try:
            doc = json.loads(out_path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            doc = {}
    doc.update({"schema": SCHEMA, "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    doc.setdefault("branches", {})["branch2"] = block
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return out_path
