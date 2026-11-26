"""Central configuration for EpiCare Branch 2 (convulsive seizure detection).

Every number fixed by the report (EpiCare Report.pdf, Section 5) is collected here so it can be
changed in one place. Paths are relative to the ``branch2/`` folder by default.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

BRANCH2_ROOT = Path(__file__).resolve().parents[1]

# --------------------------------------------------------------------------------------
# Dataset: SeizeIT2 (OpenNeuro ds005873, BIDS 1.8.0, CC0), 125 patients, 886 focal seizures.
# Layout:  sub-XXX/ses-01/{eeg,ecg,emg,mov}/sub-XXX_ses-01_task-szMonitoring_run-NN_<mod>.edf
# Events:  only in eeg/, ..._events.tsv with columns
#          onset duration eventType lateralization localization vigilance confidence channels
#          dateTime recordingDuration
# mov:     25 Hz, 12 channels (accelerometer + gyroscope of two sensor modules: back of the neck
#          on the EEG module, left chest on the ECG/EMG module). NOT on the wrist (report §5.6).
# ecg:     256 Hz, 1 channel.
# --------------------------------------------------------------------------------------
OPENNEURO_ID = "ds005873"
OPENNEURO_DOI = "10.18112/openneuro.ds005873.v1.1.0"
SEIZEIT2_TASK = "szMonitoring"
# Paper split (Bhagubai et al. 2025): train sub-001..096, validation sub-097..125
SEIZEIT2_TRAIN = [f"sub-{i:03d}" for i in range(1, 97)]
SEIZEIT2_VAL = [f"sub-{i:03d}" for i in range(97, 126)]

# eventType values that are not seizures
NON_SEIZURE_EVENTS = ("bckg", "impd")
# eventType values counted as *convulsive* (strong rhythmic movement). A code matches if it
# starts with one of these prefixes or contains one of the keywords (case-insensitive).
# sz_foc_f2b = focal to bilateral tonic-clonic (55 in SeizeIT2).
CONVULSIVE_PREFIXES = ("sz_foc_f2b", "sz_gen_m")
CONVULSIVE_KEYWORDS = ("tonicclonic", "tonic-clonic", "_clonic")
# never convulsive, even if a keyword matches (myoclonic = brief jerks, not a convulsion)
NOT_CONVULSIVE_KEYWORDS = ("myoclonic", "myio")


@dataclass
class PreprocessConfig:
    fs: int = 32                       # common rate for all sources (report §3 step 6, §5.2)
    window_s: float = 10.0             # 10-second windows
    step_s: float = 5.0                # 50 % overlap
    highpass_hz: float = 0.5           # removes gravity (report §5.2)
    lowpass_hz: float = 12.0           # anti-aliasing / noise, below fs/2
    min_overlap_s: float = 2.0         # a window is positive if it overlaps a convulsive seizure by >= 2 s
    # which mov sensor to use when the EDF holds two: matched against channel labels, first wins
    sensor_preference: tuple = ("ecg", "emg", "chest", "")   # "" = any sensor
    calibrate_gravity: bool = True     # SeizeIT2 reads ~0.5 g at rest: rescale so rest = 1 g
    ecg_min_rr_s: float = 0.3          # 200 bpm upper bound for R-peak detection
    hr_baseline_s: float = 300.0       # heart-rate change = HR - median HR of the previous 5 min


@dataclass
class ModelConfig:
    kind: str = "rf"                   # "rf" (random forest) | "xgb" (needs xgboost) | "cnn" | "cnn_phys"
    n_estimators: int = 300
    max_depth: int | None = 12
    min_samples_leaf: int = 5
    neg_per_pos: int = 50              # negatives kept per positive window when training
    use_physiology: bool = True        # heart rate (and EDA when present) features
    # CNN
    cnn_epochs: int = 15
    cnn_batch: int = 128
    cnn_lr: float = 1e-3
    cnn_channels: tuple = (16, 32, 64)
    device: str = "cpu"
    seed: int = 0


@dataclass
class DecisionConfig:
    threshold: float = 0.5             # on P(seizure | x), after the prior shift; tuned on validation
    min_positive_s: float = 20.0       # declared after ~15-20 s of consecutive positive windows (§5.4)
    refractory_s: float = 300.0        # one alarm per episode: no new alarm within 5 min
    max_alarms_per_hour: int = 3       # alert-policy rule (§6.2)
    stillness_s: float = 30.0          # post-ictal stillness check after the alarm
    stillness_rms_g: float = 0.02      # below this movement RMS the wearer is "still"
    prior_shift_cap: float = 1.0       # |log(r / r_bar)| <= 1 (§5.5), same as Branch 1
    # tuning grid (validation set only)
    threshold_grid: tuple = (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
    min_positive_grid: tuple = (10.0, 15.0, 20.0, 25.0, 30.0)
    target_fa_per_day: float = 1.0     # success criterion: < 1 false alarm per day of wear


@dataclass
class EvalConfig:
    split: str = "paper"               # "paper" (SeizeIT2 train/val) | "gkfold" (grouped by patient)
    n_folds: int = 5
    inner_folds: int = 3               # out-of-fold predictions on train patients to tune the decision
    pre_margin_s: float = 30.0         # an alarm up to 30 s before onset still counts as a detection
    post_margin_s: float = 60.0        # ... or up to 60 s after the seizure ends
    target_sensitivity: float = 0.9    # success criterion: >= 90 % of convulsive seizures detected
    target_delay_s: float = 30.0       # success criterion: < 30 s before the countdown


@dataclass
class Config:
    data_raw: Path = BRANCH2_ROOT / "data" / "raw" / OPENNEURO_ID
    data_processed: Path = BRANCH2_ROOT / "data" / "processed"
    models_dir: Path = BRANCH2_ROOT / "models"
    results_dir: Path = BRANCH2_ROOT / "results"
    pre: PreprocessConfig = field(default_factory=PreprocessConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    decision: DecisionConfig = field(default_factory=DecisionConfig)
    eval: EvalConfig = field(default_factory=EvalConfig)

    def to_dict(self) -> dict:
        d = asdict(self)
        for k, v in d.items():
            if isinstance(v, Path):
                d[k] = str(v)
        return d
