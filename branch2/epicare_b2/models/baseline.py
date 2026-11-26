"""Baseline detector (report §5.3): random forest (or XGBoost) on the hand-made features.

Light, explainable, and the fair reference for the CNN. Negatives are subsampled
(``neg_per_pos``) because convulsive windows are rare; windows of non-convulsive seizures are
left out of training (neither clearly positive nor clearly negative).
"""
from __future__ import annotations

import numpy as np

from ..config import ModelConfig
from ..features import PHYS_FEATURES, feature_names


def training_sample(y: np.ndarray, neg_per_pos: int, rng: np.random.Generator,
                    hard_neg: np.ndarray | None = None) -> np.ndarray:
    """Indices: all positives, all hard negatives, and ``neg_per_pos`` random negatives per positive."""
    pos = np.flatnonzero(y == 1)
    neg = np.flatnonzero(y == 0)
    n_neg = min(len(neg), max(neg_per_pos * max(len(pos), 1), 1000))
    keep = [pos, rng.choice(neg, n_neg, replace=False) if n_neg else neg[:0]]
    if hard_neg is not None:
        keep.append(np.flatnonzero(hard_neg & (y == 0)))
    return np.unique(np.concatenate(keep))


class FeatureDetector:
    """fit(X, y) / predict_proba(X) -> P(convulsive). X columns = feature_names(True)."""

    def __init__(self, cfg: ModelConfig | None = None):
        self.cfg = cfg or ModelConfig()
        self.names = feature_names(True)
        self.cols = [i for i, n in enumerate(self.names) if self.cfg.use_physiology or n not in PHYS_FEATURES]
        self.model = None

    def _make(self, pos_frac: float):
        c = self.cfg
        if c.kind == "xgb":
            from xgboost import XGBClassifier  # optional dependency
            return XGBClassifier(n_estimators=c.n_estimators, max_depth=c.max_depth or 6, learning_rate=0.05,
                                 subsample=0.8, colsample_bytree=0.8, eval_metric="logloss",
                                 scale_pos_weight=(1 - pos_frac) / max(pos_frac, 1e-6), random_state=c.seed,
                                 n_jobs=-1)
        from sklearn.ensemble import RandomForestClassifier
        return RandomForestClassifier(n_estimators=c.n_estimators, max_depth=c.max_depth,
                                      min_samples_leaf=c.min_samples_leaf, class_weight="balanced_subsample",
                                      n_jobs=-1, random_state=c.seed)

    def fit(self, X: np.ndarray, y: np.ndarray, hard_neg: np.ndarray | None = None) -> "FeatureDetector":
        rng = np.random.default_rng(self.cfg.seed)
        keep = y != 2
        X, y = X[keep], (y[keep] == 1).astype(int)
        hn = hard_neg[keep] if hard_neg is not None else None
        idx = training_sample(y, self.cfg.neg_per_pos, rng, hn)
        Xs, ys = X[idx][:, self.cols], y[idx]
        if ys.min() == ys.max():
            raise ValueError("training data holds a single class (no convulsive windows?)")
        self.model = self._make(ys.mean())
        self.model.fit(Xs, ys)
        # the sample is rebalanced: keep the true positive rate to correct the probabilities
        self.train_pos_frac = float(ys.mean())
        self.true_pos_frac = float(y.mean())
        return self

    def predict_proba(self, X: np.ndarray, recalibrate: bool = False) -> np.ndarray:
        p = self.model.predict_proba(X[:, self.cols])[:, 1]
        if recalibrate:  # undo the subsampling (prior correction); off by default, thresholds are tuned
            a = self.true_pos_frac / self.train_pos_frac
            b = (1 - self.true_pos_frac) / (1 - self.train_pos_frac)
            p = p * a / (p * a + (1 - p) * b)
        return p

    def importances(self) -> dict:
        imp = getattr(self.model, "feature_importances_", None)
        if imp is None:
            return {}
        names = [self.names[i] for i in self.cols]
        return dict(sorted(zip(names, map(float, imp)), key=lambda kv: -kv[1]))
