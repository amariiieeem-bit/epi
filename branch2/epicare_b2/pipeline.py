"""High-level Branch 2 functions: load, cross-validate by patient, simulate the Branch 1 link.

Honest-results rules (report §7): split by patient, never by window; the decision (threshold,
positive duration) is tuned on out-of-fold predictions of the *training* patients only; every
patient is reported, including failures.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import SEIZEIT2_TRAIN, SEIZEIT2_VAL, Config
from .evaluation import RunPred, evaluate_runs, tune_decision
from .features import PHYS_FEATURES, feature_names
from .preprocessing import load_subject
from .signals import make_windows


# ------------------------------------------------------------------ loading
def load_subjects(processed: str | Path, subjects: list[str] | None = None) -> dict[str, dict]:
    processed = Path(processed)
    out = {}
    for f in sorted(processed.iterdir()) if processed.exists() else []:
        if (f / "windows.npz").exists() and (subjects is None or f.name in subjects):
            out[f.name] = load_subject(f)
    if not out:
        raise FileNotFoundError(f"no processed subject in {processed} (run: python -m epicare_b2 preprocess)")
    return out


def raw_windows(sub: dict, cfg: Config) -> np.ndarray:
    """(n, 4, w) raw windows of a subject, rebuilt from the saved 32 Hz signals (--keep-signal)."""
    W = []
    for r in sub["runs"].itertuples():
        f = Path(sub["folder"]) / f"signal_{r.run}.npy"
        if not f.exists():
            raise FileNotFoundError(f"{f} missing: preprocess with --keep-signal to train the CNN")
        w, _ = make_windows(np.load(f).astype(np.float32), cfg.pre)
        W.append(w)
    W = np.concatenate(W)
    assert len(W) == len(sub["y"]), "signal and windows out of step: preprocess again"
    return W


def run_preds(sub: dict, p: np.ndarray, cfg: Config, with_signal: bool = False) -> list[RunPred]:
    """Split one subject's window predictions into runs for the decision and evaluation."""
    out = []
    ev = sub["events"]
    for r in sub["runs"].itertuples():
        m = sub["run"] == r.run_index
        e = ev[ev["run"] == r.run] if len(ev) else ev
        mag = None
        if with_signal:
            f = Path(sub["folder"]) / f"signal_{r.run}.npy"
            mag = np.load(f)[:, 3].astype(np.float32) if f.exists() else None
        out.append(RunPred(sub["subject"], r.run, sub["t_start"][m], p[m], e.reset_index(drop=True),
                           float(r.duration_s), mag, cfg.pre.fs))
    return out


# ------------------------------------------------------------------ detector wrapper
class Detector:
    """Same interface for the feature model and the CNN: fit(list of subjects), predict(subject)."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.kind = cfg.model.kind
        names = feature_names(True)
        self.phys_cols = [names.index(n) for n in PHYS_FEATURES]

    def fit(self, subs: list[dict], extra_negatives: list[dict] | None = None, verbose: bool = False):
        extra = extra_negatives or []
        y = np.concatenate([s["y"] for s in subs] + [np.zeros(len(e["y"]), np.int8) for e in extra])
        hard = np.concatenate([np.zeros(len(s["y"]), bool) for s in subs] + [np.ones(len(e["y"]), bool) for e in extra])
        if self.kind in ("rf", "xgb"):
            from .models.baseline import FeatureDetector
            X = np.concatenate([s["feats"] for s in subs] + [e["feats"] for e in extra])
            self.model = FeatureDetector(self.cfg.model).fit(X, y, hard)
        else:
            from .models.cnn import CNNDetector
            W = np.concatenate([raw_windows(s, self.cfg) for s in subs] + [e["windows"] for e in extra])
            P = np.concatenate([s["feats"][:, self.phys_cols] for s in subs + extra])
            self.model = CNNDetector(self.cfg.model).fit(W, y, P, verbose=verbose)
        return self

    def predict(self, sub: dict) -> np.ndarray:
        if self.kind in ("rf", "xgb"):
            return self.model.predict_proba(sub["feats"])
        W = sub["windows"] if "windows" in sub else raw_windows(sub, self.cfg)
        return self.model.predict_proba(W, sub["feats"][:, self.phys_cols])


# ------------------------------------------------------------------ cross-validation
def subject_folds(subjects: list[str], cfg: Config) -> list[tuple[list, list]]:
    if cfg.eval.split == "paper":
        tr = [s for s in subjects if s in SEIZEIT2_TRAIN]
        te = [s for s in subjects if s in SEIZEIT2_VAL]
        if tr and te:
            return [(tr, te)]
    k = min(cfg.eval.n_folds, len(subjects))
    rng = np.random.default_rng(cfg.model.seed)
    order = list(rng.permutation(subjects))
    return [([s for s in order if s not in order[i::k]], order[i::k]) for i in range(k)]


def _has_pos(subs):
    return any((s["y"] == 1).any() for s in subs)


def _oof_preds(subs: list[dict], cfg: Config, extra=None) -> list[RunPred]:
    """Out-of-fold predictions on training subjects (inner grouped folds), to tune the decision."""
    names = [s["subject"] for s in subs]
    k = min(cfg.eval.inner_folds, len(names))
    out = []
    for i in range(k):
        val = names[i::k]
        tr = [s for s in subs if s["subject"] not in val]
        if not _has_pos(tr):
            continue
        det = Detector(cfg).fit(tr, extra)
        for s in subs:
            if s["subject"] in val:
                out += run_preds(s, det.predict(s), cfg)
    return out


def cross_validate(S: dict[str, dict], cfg: Config | None = None, extra_negatives: list[dict] | None = None,
                   verbose: bool = True) -> dict:
    """Patient-grouped evaluation. Returns test predictions per run, chosen decisions, metrics."""
    cfg = cfg or Config()
    folds = subject_folds(list(S), cfg)
    test_preds, decisions, per_fold = [], [], []
    w, st = cfg.pre.window_s, cfg.pre.step_s
    for fi, (tr, te) in enumerate(folds):
        trs = [S[s] for s in tr]
        if not _has_pos(trs):
            print(f"fold {fi}: no convulsive seizure in training patients, skipped")
            continue
        oof = _oof_preds(trs, cfg, extra_negatives)
        dec = tune_decision(oof, cfg.decision, cfg.eval, window_s=w, step_s=st)[0] if oof else \
            {"threshold": cfg.decision.threshold, "min_positive_s": cfg.decision.min_positive_s}
        det = Detector(cfg).fit(trs, extra_negatives, verbose=verbose)
        fold_preds = []
        for s in te:
            fold_preds += run_preds(S[s], det.predict(S[s]), cfg, with_signal=True)
        r = evaluate_runs(fold_preds, cfg.decision, cfg.eval, dec["threshold"], dec["min_positive_s"],
                          window_s=w, step_s=st)
        for p in fold_preds:
            p.decision = dec  # type: ignore[attr-defined]
        test_preds += fold_preds
        decisions.append({"fold": fi, **dec, "train": tr, "test": te})
        per_fold.append({"fold": fi, **r["overall"]})
        if verbose:
            o = r["overall"]
            print(f"fold {fi}: thr {dec['threshold']:.2f}, {dec['min_positive_s']:.0f} s | "
                  f"sens {o['sensitivity']:.2f} ({o['n_detected']}/{o['n_seizures']}), "
                  f"FA/day {o['fa_per_day']:.2f}, delay {o['delay_median_s']:.0f} s")
    res = evaluate_with_decisions(test_preds, cfg)
    res.update({"preds": test_preds, "decisions": decisions, "folds": pd.DataFrame(per_fold)})
    if decisions:
        res["detector"] = det  # last fold's model (look-alike test, feature importances)
    return res


def evaluate_with_decisions(preds: list[RunPred], cfg: Config, use_prior: bool = False) -> dict:
    """Evaluate test runs, each with the decision of its own fold."""
    parts = {}
    for p in preds:
        d = getattr(p, "decision", {"threshold": cfg.decision.threshold, "min_positive_s": cfg.decision.min_positive_s})
        parts.setdefault((d["threshold"], d["min_positive_s"]), []).append(p)
    al, sz, hr = [], [], []
    for (thr, mp), ps in parts.items():
        r = evaluate_runs(ps, cfg.decision, cfg.eval, thr, mp, use_prior=use_prior,
                          window_s=cfg.pre.window_s, step_s=cfg.pre.step_s)
        al.append(r["alarms"]); sz.append(r["seizures"]); hr.append(r["hours"])
    from .evaluation import per_subject, summarize
    A = pd.concat(al, ignore_index=True) if al else pd.DataFrame(columns=["time", "kind", "subject"])
    Z = pd.concat(sz, ignore_index=True) if sz else pd.DataFrame(columns=["detected", "delay_s", "subject"])
    H = pd.concat(hr, ignore_index=True) if hr else pd.DataFrame(columns=["subject", "hours"])
    return {"alarms": A, "seizures": Z, "hours": H, "overall": summarize(A, Z, H), "per_subject": per_subject(A, Z, H)}


# ------------------------------------------------------------------ Branch 1 link (report §7 simulation)
def branch1_shift_distributions(app_json: str | Path | None, cap: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """Prior shifts Branch 1 produced in hours before a seizure vs other hours (out-of-sample).

    Read from Branch 1's app export (``app/data/app_data.json``: per-patient timeline p1 and
    seizures). Falls back to a mildly informative forecast if the file is missing."""
    pre, norm = [], []
    if app_json and Path(app_json).exists():
        doc = json.loads(Path(app_json).read_text(encoding="utf-8"))
        for p in (doc.get("branches", {}).get("branch1") or {}).get("patients", []):
            tl = p.get("timeline") or {}
            p1 = np.array([np.nan if v is None else v for v in tl.get("p1", [])], float)
            if not len(p1) or not tl.get("start"):
                continue
            t0 = pd.Timestamp(tl["start"])
            hours = t0 + pd.to_timedelta(np.arange(len(p1)), unit="h")
            sz = pd.to_datetime(tl.get("seizures", [])).sort_values()
            # same labels as Branch 1: events (>= 4 h apart), the hour after a seizure left out
            ev = [s for i, s in enumerate(sz) if i == 0 or s - sz[i - 1] >= pd.Timedelta(hours=4)]
            y = np.zeros(len(p1), bool)
            post = np.zeros(len(p1), bool)
            for s in ev:
                y[(hours <= s) & (hours + pd.Timedelta(hours=1) > s)] = True
            for s in sz:
                post |= (hours > s) & (hours <= s + pd.Timedelta(hours=1))
            r_bar = np.nanmean(p1)
            sh = np.clip(np.log(np.maximum(p1, 1e-9) / max(r_bar, 1e-9)), -cap, cap)
            ok = np.isfinite(sh) & ~post
            pre += list(sh[ok & y]); norm += list(sh[ok & ~y])
    if len(pre) < 3 or len(norm) < 10:
        rng = np.random.default_rng(0)
        pre = np.clip(rng.normal(0.4, 0.4, 500), -cap, cap)
        norm = np.clip(rng.normal(-0.05, 0.4, 5000), -cap, cap)
    return np.asarray(pre, float), np.asarray(norm, float)


def simulate_prior(preds: list[RunPred], mode: str, pre_shift=None, norm_shift=None, cap: float = 1.0,
                   seed: int = 0) -> list[RunPred]:
    """Attach a prior shift to every test window (one value per hour of recording).

    mode: "none" (0), "branch1" (draws from Branch 1's measured behaviour: hours holding a
    seizure from ``pre_shift``, others from ``norm_shift``), "perfect" (+cap in seizure hours,
    -cap elsewhere), "useless" (draws from the pooled distribution, unrelated to seizures)."""
    rng = np.random.default_rng(seed)
    pooled = None if pre_shift is None else np.concatenate([pre_shift, norm_shift])
    out = []
    for r in preds:
        hour = (r.t_start // 3600).astype(int)
        nh = int(hour.max()) + 1 if len(hour) else 0
        sz_h = np.zeros(nh, bool)
        for e in r.events.itertuples():
            if e.convulsive:
                sz_h[int(e.onset // 3600): int(e.offset // 3600) + 1] = True
        if mode == "none":
            h = np.zeros(nh)
        elif mode == "perfect":
            h = np.where(sz_h, cap, -cap)
        elif mode == "branch1":
            h = np.where(sz_h, rng.choice(pre_shift, nh), rng.choice(norm_shift, nh))
        elif mode == "useless":
            h = rng.choice(pooled, nh)
        else:
            raise ValueError(mode)
        q = RunPred(r.subject, r.run, r.t_start, r.p, r.events, r.duration_s, r.mag, r.fs, h[hour] if nh else None)
        if hasattr(r, "decision"):
            q.decision = r.decision  # type: ignore[attr-defined]
        out.append(q)
    return out


def prior_effect(preds: list[RunPred], cfg: Config, app_json=None, thresholds=None) -> pd.DataFrame:
    """Sensitivity and false alarms per day, with and without the prior, over a threshold sweep.

    Read at fixed sensitivity: the success criterion is fewer false alarms with the prior."""
    pre, norm = branch1_shift_distributions(app_json, cfg.decision.prior_shift_cap)
    thresholds = thresholds or list(np.round(np.arange(0.2, 0.96, 0.05), 2))
    rows = []
    for mode in ("none", "useless", "branch1", "perfect"):
        sim = simulate_prior(preds, mode, pre, norm, cfg.decision.prior_shift_cap, seed=cfg.model.seed)
        for thr in thresholds:
            o = evaluate_runs(sim, cfg.decision, cfg.eval, threshold=thr, use_prior=True,
                              window_s=cfg.pre.window_s, step_s=cfg.pre.step_s)["overall"]
            rows.append({"prior": mode, "threshold": thr, **o})
    return pd.DataFrame(rows)


def fa_at_sensitivity(curve: pd.DataFrame, target: float = 0.9) -> pd.DataFrame:
    """Lowest false alarms per day reaching the target sensitivity, per prior mode."""
    out = []
    for mode, g in curve.groupby("prior", sort=False):
        ok = g[g.sensitivity >= target]
        best = ok.sort_values("fa_per_day").iloc[0] if len(ok) else g.sort_values("sensitivity").iloc[-1]
        out.append({"prior": mode, "sensitivity": best.sensitivity, "fa_per_day": best.fa_per_day,
                    "threshold": best.threshold, "reached_target": bool(len(ok))})
    return pd.DataFrame(out)


# ------------------------------------------------------------------ final model (all patients)
def fit_final(S: dict[str, dict], cfg: Config, extra_negatives: list[dict] | None = None) -> dict:
    """Detector trained on every subject; decision tuned on their out-of-fold predictions.

    This is the model that runs on new data (the wrist recordings of Branch 1's patients, the
    watch). Its performance is the cross-validated one, never measured on its own training data."""
    subs = list(S.values())
    oof = _oof_preds(subs, cfg, extra_negatives)
    dec = tune_decision(oof, cfg.decision, cfg.eval, window_s=cfg.pre.window_s, step_s=cfg.pre.step_s)[0] if oof \
        else {"threshold": cfg.decision.threshold, "min_positive_s": cfg.decision.min_positive_s}
    det = Detector(cfg).fit(subs, extra_negatives)
    return {"detector": det, "decision": dec, "subjects": list(S), "kind": cfg.model.kind}


def save_model(final: dict, path: str | Path) -> Path:
    import pickle
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(final, f)
    return path


def load_model(path: str | Path) -> dict:
    """Only load model files you created yourself (pickle runs code on load)."""
    import pickle
    with open(path, "rb") as f:
        return pickle.load(f)
