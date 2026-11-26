"""SeizeIT2 (OpenNeuro ds005873) reader: runs, events, motion and ECG signals.

Layout (BIDS):  <root>/sub-XXX/ses-01/{eeg,ecg,mov}/sub-XXX_ses-01_task-szMonitoring_run-NN_<mod>.edf
Events live in eeg/ only: ..._run-NN_events.tsv (onset and duration in seconds from the run start).
Channel names are read from the EDF headers, never hard-coded: the accelerometer axes are found by
matching labels (``ACC`` / ``acc`` + x, y, z), and the sensor module by ``sensor_preference``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .config import (CONVULSIVE_KEYWORDS, CONVULSIVE_PREFIXES, NON_SEIZURE_EVENTS, NOT_CONVULSIVE_KEYWORDS,
                     OPENNEURO_ID, SEIZEIT2_TASK)
from .edf import EdfSignal, read_edf, read_header

RUN_RE = re.compile(r"(sub-[^_]+)_(ses-[^_]+)_task-[^_]+_(run-[^_]+)_(\w+)\.(edf|tsv)$")


@dataclass
class Run:
    subject: str
    session: str
    run: str
    files: dict = field(default_factory=dict)      # modality -> path ("eeg", "ecg", "mov", "events")

    @property
    def key(self) -> str:
        return f"{self.subject}_{self.session}_{self.run}"


def find_runs(root: str | Path, subjects: list[str] | None = None) -> list[Run]:
    """All runs of the dataset, sorted by subject then run."""
    root = Path(root)
    runs: dict[str, Run] = {}
    for p in sorted(root.glob("sub-*/ses-*/*/*")):
        m = RUN_RE.search(p.name)
        if not m:
            continue
        sub, ses, run, mod, _ = m.groups()
        if subjects and sub not in subjects:
            continue
        r = runs.setdefault(f"{sub}_{ses}_{run}", Run(sub, ses, run))
        r.files[mod] = p
    return sorted(runs.values(), key=lambda r: (r.subject, r.session, r.run))


def is_convulsive(event_type: str) -> bool:
    e = str(event_type).lower()
    if any(k in e for k in NOT_CONVULSIVE_KEYWORDS):
        return False
    return e.startswith(CONVULSIVE_PREFIXES) or any(k in e for k in CONVULSIVE_KEYWORDS)


def read_events(path: str | Path | None) -> pd.DataFrame:
    """Seizure events of a run: onset, duration, offset (s from run start), type, convulsive flag."""
    cols = ["onset", "duration", "offset", "eventType", "convulsive", "vigilance"]
    if path is None or not Path(path).exists():
        return pd.DataFrame(columns=cols)
    ev = pd.read_csv(path, sep="\t", na_values=["n/a"])
    ev = ev[~ev["eventType"].astype(str).isin(NON_SEIZURE_EVENTS)].copy()
    ev["onset"] = ev["onset"].astype(float)
    ev["duration"] = ev["duration"].astype(float).fillna(0.0)
    ev["offset"] = ev["onset"] + ev["duration"]
    ev["convulsive"] = ev["eventType"].map(is_convulsive)
    if "vigilance" not in ev:
        ev["vigilance"] = np.nan
    return ev[cols].sort_values("onset").reset_index(drop=True)


def _axis(label: str) -> str | None:
    m = re.search(r"(?:^|[^a-z])([xyz])(?:$|[^a-z])", label.lower().replace("acc", " "))
    return m.group(1) if m else None


def pick_accelerometer(labels: list[str], preference=("",)) -> list[str] | None:
    """Labels of one accelerometer triplet (x, y, z), choosing the sensor by preference order."""
    acc = [lab for lab in labels if "acc" in lab.lower() and _axis(lab)]
    if not acc:
        return None
    for pref in preference:
        group = [lab for lab in acc if pref.lower() in lab.lower()]
        by_axis = {}
        for lab in group:
            by_axis.setdefault(_axis(lab), lab)
        if all(a in by_axis for a in "xyz"):
            return [by_axis["x"], by_axis["y"], by_axis["z"]]
    return None


def to_g(acc: np.ndarray, unit: str = "") -> np.ndarray:
    """Accelerometer -> units of g. Uses the EDF unit, else the median magnitude (~1 g at rest)."""
    u = unit.lower().replace(" ", "")
    if u in ("g",):
        return acc
    if u in ("m/s2", "m/s^2", "ms-2", "m/s²"):
        return acc / 9.80665
    if u in ("mg",):
        return acc / 1000.0
    med = np.nanmedian(np.linalg.norm(acc, axis=1)) if len(acc) else 1.0
    if 5 < med < 15:
        return acc / 9.80665
    if 500 < med < 1500:
        return acc / 1000.0
    if 40 < med < 90:        # Empatica E4 raw units (1/64 g)
        return acc / 64.0
    return acc


def gravity_scale(acc_g: np.ndarray) -> float:
    """Resting magnitude of the accelerometer (should be 1 g), from its stillest 20 % of samples."""
    if acc_g is None or len(acc_g) < 100:
        return 1.0
    m = np.linalg.norm(acc_g, axis=1)
    dyn = np.abs(np.diff(m))
    still = m[1:][dyn <= np.quantile(dyn, 0.2)]
    g = float(np.median(still)) if len(still) else float(np.median(m))
    return g if np.isfinite(g) and g > 0 else 1.0


def calibrate_gravity(acc_g: np.ndarray, tol: float = 0.1) -> tuple[np.ndarray, float]:
    """Rescale so that the resting magnitude is 1 g, if it is off by more than ``tol``.

    SeizeIT2's motion EDFs say "g" but read ~0.50 at rest on both sensor modules (checked on
    sub-015, all runs): the values are half the true acceleration. Without this, every movement
    would look half as strong as on a watch, and the model would not transfer to the wrist."""
    g = gravity_scale(acc_g)
    if abs(g - 1.0) > tol:
        return acc_g / g, g
    return acc_g, 1.0


@dataclass
class RunSignals:
    run: Run
    duration_s: float
    acc: np.ndarray | None         # (n, 3) in g
    acc_fs: float
    acc_labels: list
    gravity: float                 # resting magnitude before calibration (1.0 = none applied)
    ecg: np.ndarray | None
    ecg_fs: float
    events: pd.DataFrame


def load_run(run: Run, preference=("",), with_ecg: bool = True, calibrate: bool = True) -> RunSignals:
    acc, acc_fs, acc_labels, grav = None, 0.0, [], 1.0
    dur = 0.0
    if "mov" in run.files:
        h, _ = read_header(run.files["mov"])
        dur = h.duration_s
        trip = pick_accelerometer(h.labels, preference)
        if trip:
            _, sig = read_edf(run.files["mov"], channels=trip)
            sig = sorted(sig, key=lambda s: trip.index(s.label))
            n = min(len(s.data) for s in sig)
            acc = to_g(np.column_stack([s.data[:n] for s in sig]), sig[0].unit)
            if calibrate:
                acc, grav = calibrate_gravity(acc)
            acc_fs, acc_labels = sig[0].fs, trip
    ecg, ecg_fs = None, 0.0
    if with_ecg and "ecg" in run.files:
        h, sig = read_edf(run.files["ecg"])
        if sig:
            ecg, ecg_fs = sig[0].data, sig[0].fs
            dur = dur or h.duration_s
    return RunSignals(run, dur, acc, acc_fs, acc_labels, grav, ecg, ecg_fs, read_events(run.files.get("events")))


def inspect_dataset(root: str | Path, max_runs: int = 3) -> pd.DataFrame:
    """Print what the dataset holds (first runs' channel labels, seizure counts per type)."""
    runs = find_runs(root)
    print(f"{len(runs)} runs, {len({r.subject for r in runs})} subjects in {root}")
    for r in runs[:max_runs]:
        print(f"\n{r.key}: {sorted(r.files)}")
        for mod in ("mov", "ecg"):
            if mod in r.files:
                h, _ = read_header(r.files[mod])
                print(f"  {mod}: {h.duration_s / 3600:.2f} h, record {h.record_s} s")
                for lab, u, fs in zip(h.labels, h.units, h.fs):
                    print(f"    {lab!r:28} {u!r:8} {fs:g} Hz")
        if "mov" in r.files:
            h, _ = read_header(r.files["mov"])
            print("  accelerometer picked:", pick_accelerometer(h.labels, ("ecg", "emg", "chest", "")))
    ev = pd.concat([read_events(r.files.get("events")).assign(subject=r.subject) for r in runs],
                   ignore_index=True) if runs else pd.DataFrame()
    if len(ev):
        print("\nSeizure types:")
        print(ev.groupby(["eventType", "convulsive"]).size().sort_values(ascending=False).to_string())
        conv = ev[ev.convulsive]
        print(f"\nConvulsive: {len(conv)} seizures in {conv.subject.nunique()} subjects")
    return ev


def convulsive_subjects(root: str | Path) -> list[str]:
    """Subjects with at least one convulsive seizure (needs only the events files)."""
    subs = set()
    for p in Path(root).glob("sub-*/ses-*/eeg/*_events.tsv"):
        if read_events(p).convulsive.any():
            subs.add(p.name.split("_")[0])
    return sorted(subs)


__all__ = ["Run", "RunSignals", "find_runs", "read_events", "load_run", "pick_accelerometer",
           "is_convulsive", "inspect_dataset", "to_g", "calibrate_gravity", "convulsive_subjects", "EdfSignal", "SEIZEIT2_TASK"]
