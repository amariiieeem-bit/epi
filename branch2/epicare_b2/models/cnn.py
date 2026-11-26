"""Main detector (report §5.3): a small 1D CNN on the raw window, optionally fused with physiology.

Input: (batch, 4, 320) = x, y, z, dynamic magnitude, 10 s at 32 Hz. About 20 k parameters,
small enough for a watch. ``cnn_phys`` adds a branch for heart-rate change (and EDA change),
NaN replaced by 0 with a "measured" flag so the model still runs without them.
Exports to ONNX (then TensorFlow Lite or ONNX Runtime Mobile on the device).
PyTorch is imported lazily: the rest of Branch 2 runs without it.
"""
from __future__ import annotations

import numpy as np

from ..config import ModelConfig


def _torch():
    try:
        import torch
        return torch
    except ImportError as e:  # pragma: no cover
        raise ImportError("the CNN needs PyTorch: pip install torch") from e


def build_net(cfg: ModelConfig, n_phys: int = 0):
    torch = _torch()
    nn = torch.nn

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            layers, c_in = [], 4
            for c in cfg.cnn_channels:
                layers += [nn.Conv1d(c_in, c, 7, padding=3), nn.BatchNorm1d(c), nn.ReLU(), nn.MaxPool1d(2)]
                c_in = c
            self.conv = nn.Sequential(*layers, nn.AdaptiveAvgPool1d(1), nn.Flatten())
            self.phys = nn.Sequential(nn.Linear(2 * n_phys, 8), nn.ReLU()) if n_phys else None
            self.head = nn.Sequential(nn.Dropout(0.2), nn.Linear(c_in + (8 if n_phys else 0), 32), nn.ReLU(),
                                      nn.Linear(32, 1))

        def forward(self, x, phys=None):
            h = self.conv(x)
            if self.phys is not None:
                h = torch.cat([h, self.phys(phys)], dim=1)
            return self.head(h).squeeze(1)

    return Net()


def _phys_input(P: np.ndarray | None) -> np.ndarray | None:
    if P is None:
        return None
    m = np.isfinite(P)
    return np.concatenate([np.where(m, P, 0.0) / 20.0, m.astype(np.float32)], axis=1).astype(np.float32)


class CNNDetector:
    def __init__(self, cfg: ModelConfig | None = None, use_phys: bool | None = None):
        self.cfg = cfg or ModelConfig()
        self.use_phys = (self.cfg.kind == "cnn_phys") if use_phys is None else use_phys
        self.net = None
        self.scale = 1.0

    def fit(self, W: np.ndarray, y: np.ndarray, P: np.ndarray | None = None, verbose: bool = True):
        """W: (n, 4, w) windows; y: 0/1/2 labels (2 dropped); P: (n, k) physiology or None."""
        torch = _torch()
        c = self.cfg
        torch.manual_seed(c.seed)
        rng = np.random.default_rng(c.seed)
        from .baseline import training_sample
        keep = np.flatnonzero(y != 2)
        idx = keep[training_sample((y[keep] == 1).astype(int), c.neg_per_pos, rng)]
        Wt = W[idx].astype(np.float32)
        self.scale = float(np.std(Wt) + 1e-6)
        yt = (y[idx] == 1).astype(np.float32)
        Pt = _phys_input(P[idx]) if (self.use_phys and P is not None) else None
        self.n_phys = 0 if Pt is None else Pt.shape[1] // 2
        self.net = build_net(c, self.n_phys).to(c.device)
        opt = torch.optim.Adam(self.net.parameters(), lr=c.cnn_lr, weight_decay=1e-4)
        pw = torch.tensor((1 - yt.mean()) / max(yt.mean(), 1e-6), device=c.device)
        lossf = torch.nn.BCEWithLogitsLoss(pos_weight=pw)
        n = len(yt)
        for ep in range(c.cnn_epochs):
            self.net.train()
            perm = rng.permutation(n)
            tot = 0.0
            for b in range(0, n, c.cnn_batch):
                j = perm[b:b + c.cnn_batch]
                xb = torch.from_numpy(self._augment(Wt[j], rng) / self.scale).to(c.device)
                pb = torch.from_numpy(Pt[j]).to(c.device) if Pt is not None else None
                loss = lossf(self.net(xb, pb), torch.from_numpy(yt[j]).to(c.device))
                opt.zero_grad(); loss.backward(); opt.step()
                tot += float(loss) * len(j)
            if verbose:
                print(f"  cnn epoch {ep + 1}/{c.cnn_epochs}  loss {tot / n:.4f}")
        return self

    @staticmethod
    def _augment(x: np.ndarray, rng) -> np.ndarray:
        """Random rotation of the 3 axes (the sensor can sit any way round) + amplitude jitter."""
        x = x.copy()
        q, _ = np.linalg.qr(rng.normal(size=(3, 3)))
        x[:, :3] = np.einsum("ij,njt->nit", q, x[:, :3])
        return (x * rng.uniform(0.8, 1.2, (len(x), 1, 1))).astype(np.float32)

    def predict_proba(self, W: np.ndarray, P: np.ndarray | None = None, batch: int = 2048) -> np.ndarray:
        torch = _torch()
        self.net.eval()
        out = []
        Pp = _phys_input(P) if (self.n_phys and P is not None) else None
        with torch.no_grad():
            for b in range(0, len(W), batch):
                xb = torch.from_numpy(W[b:b + batch].astype(np.float32) / self.scale).to(self.cfg.device)
                pb = torch.from_numpy(Pp[b:b + batch]).to(self.cfg.device) if Pp is not None else None
                out.append(torch.sigmoid(self.net(xb, pb)).cpu().numpy())
        return np.concatenate(out) if out else np.zeros(0)

    def n_parameters(self) -> int:
        return sum(p.numel() for p in self.net.parameters())

    def export_onnx(self, path, window: int = 320) -> str:
        """Export for on-device inference (§5.6 on-device check). Input is divided by ``scale`` first."""
        torch = _torch()
        self.net.eval()
        x = torch.zeros(1, 4, window)
        args = (x, torch.zeros(1, 2 * self.n_phys)) if self.n_phys else (x,)
        names = ["acc", "phys"] if self.n_phys else ["acc"]
        torch.onnx.export(self.net, args, str(path), input_names=names, output_names=["logit"],
                          dynamic_axes={n: {0: "batch"} for n in names + ["logit"]})
        return str(path)
