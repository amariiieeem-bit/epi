"""Fast unit tests (no download):  python tests/test_branch2.py   (or: python -m pytest tests -q)"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from epicare_b2.config import Config, DecisionConfig, EvalConfig, PreprocessConfig
from epicare_b2.decision import apply_prior, detect, prior_shift
from epicare_b2.edf import EdfSignal, read_edf, write_edf
from epicare_b2.evaluation import match_alarms
from epicare_b2.features import feature_names, window_feature_matrix
from epicare_b2.io_seizeit2 import is_convulsive, pick_accelerometer, read_events, to_g
from epicare_b2.signals import heart_rate_per_window, label_windows, make_windows, prepare_acc, r_peaks


def test_edf_roundtrip(tmp_path):
    x = np.sin(np.arange(250) / 5.0) * 3
    write_edf(tmp_path / "a.edf", [EdfSignal("ECGEMG SD ACC X", 25, "g", x), EdfSignal("ECG", 50, "mV", np.tile(x, 2))])
    h, sig = read_edf(tmp_path / "a.edf")
    assert h.n_records == 10 and [s.label for s in sig] == ["ECGEMG SD ACC X", "ECG"]
    assert sig[0].fs == 25 and np.allclose(sig[0].data, x, atol=1e-3)


def test_event_types_and_reader(tmp_path):
    assert is_convulsive("sz_foc_f2b") and is_convulsive("sz_gen_m_tonicClonic")
    assert not is_convulsive("sz_foc_ia_nm") and not is_convulsive("sz_foc_a_m_automatisms")
    p = tmp_path / "e.tsv"
    p.write_text("onset\tduration\teventType\tvigilance\n10\t8\timpd\tn/a\n500\t60\tsz_foc_f2b\tawake\n"
                 "100\t30\tsz_foc_ia_nm\tn/a\n")
    ev = read_events(p)
    assert list(ev.onset) == [100, 500] and list(ev.convulsive) == [False, True] and ev.offset.iloc[1] == 560


def test_pick_accelerometer_and_units():
    labs = ["EEG SD ACC X", "EEG SD ACC Y", "EEG SD ACC Z", "EEG SD GYR X", "ECGEMG SD ACC X",
            "ECGEMG SD ACC Y", "ECGEMG SD ACC Z"]
    assert pick_accelerometer(labs, ("ecg", "")) == ["ECGEMG SD ACC X", "ECGEMG SD ACC Y", "ECGEMG SD ACC Z"]
    assert pick_accelerometer(labs, ("nope", "")) == ["EEG SD ACC X", "EEG SD ACC Y", "EEG SD ACC Z"]
    from epicare_b2.io_seizeit2 import calibrate_gravity
    rng = np.random.default_rng(0)
    half = np.tile([0.0, 0.3, 0.4], (1000, 1)) + rng.normal(0, 0.01, (1000, 3))   # rest reads 0.5 g
    cal, g = calibrate_gravity(half)
    assert abs(g - 0.5) < 0.02 and abs(np.median(np.linalg.norm(cal, axis=1)) - 1) < 0.03
    assert calibrate_gravity(half * 2)[1] == 1.0                                 # already 1 g: untouched
    a = np.tile([0.0, 0.0, 9.81], (100, 1))
    assert np.allclose(to_g(a, ""), a / 9.80665) and np.allclose(to_g(a, "m/s2"), a / 9.80665)


def test_prepare_resample_window_label():
    cfg = PreprocessConfig()
    t = np.arange(25 * 120) / 25
    acc = np.column_stack([0.3 * np.sin(2 * np.pi * 3 * t), 0 * t, 1 + 0 * t])   # 3 Hz on top of gravity
    x = prepare_acc(acc, 25, cfg)
    assert x.shape == (32 * 120, 4) and abs(np.median(x[100:-100, 3])) < 0.05      # gravity removed
    win, t0 = make_windows(x, cfg)
    assert win.shape[1:] == (4, 320) and np.allclose(np.diff(t0), 5.0)
    ev = pd.DataFrame({"onset": [30.0, 80.0], "offset": [61.0, 90.0], "convulsive": [True, False]})
    y, sid = label_windows(t0, ev, cfg)
    assert y[t0 == 30].item() == 1 and y[t0 == 55].item() == 1   # 55-65: 6 s of overlap
    assert y[t0 == 60].item() == 0                                # 60-70: 1 s < min_overlap_s
    assert y[t0 == 85].item() == 2 and sid[t0 == 85].item() == 1


def test_features_see_rhythm():
    cfg = PreprocessConfig()
    t = np.arange(32 * 10) / 32
    rng = np.random.default_rng(0)
    rhythmic = 0.4 * np.sin(2 * np.pi * 4 * t)
    noise = rng.normal(0, 0.05, len(t))
    win = np.stack([np.stack([rhythmic] * 4), np.stack([noise] * 4)]).astype(np.float32)
    F = window_feature_matrix(win, 32, cfg.step_s)
    n = feature_names(True)
    assert F.shape == (2, len(n))
    assert abs(F[0, n.index("dom_freq_hz")] - 4) < 0.2
    assert F[0, n.index("acf_peak")] > 0.8 > F[1, n.index("acf_peak")]
    assert np.isnan(F[0, n.index("hr")])


def test_heart_rate_from_ecg():
    fs, bpm = 256, 75
    n = fs * 120
    x = np.zeros(n)
    x[(np.arange(0, 120, 60 / bpm) * fs).astype(int)] = 1.0
    x = np.convolve(x, np.exp(-(np.arange(-8, 9) / 2.5) ** 2), "same")
    pk = r_peaks(x + np.random.default_rng(0).normal(0, 0.02, n), fs)
    hr, _ = heart_rate_per_window(np.arange(0, 100, 5.0), pk, PreprocessConfig())
    assert np.nanmedian(np.abs(hr - bpm)) < 2


def test_decision_consecutive_refractory_prior():
    d = DecisionConfig(threshold=0.5, min_positive_s=20.0, refractory_s=300.0)
    t = np.arange(0, 1000, 5.0)
    p = np.full(len(t), 0.1)
    p[(t >= 100) & (t < 160)] = 0.9         # one long episode
    p[(t >= 400) & (t < 405)] = 0.9         # a single positive window: no alarm
    al = detect(t, p, d)
    assert len(al) == 1 and al.time.iloc[0] == 120.0   # 3 windows: 100, 105, 110 -> end 120
    # prior: +1 shift pushes 0.35 over 0.5, -1 never silences 0.99; the cap holds
    assert apply_prior(np.array([0.35]), 1.0)[0] > 0.5 and apply_prior(np.array([0.99]), -5.0)[0] > 0.97
    assert prior_shift([10.0], 1.0, 1.0)[0] == 1.0 and prior_shift([0.001], 1.0, 1.0)[0] == -1.0


def test_match_alarms():
    al = pd.DataFrame({"time": [125.0, 2000.0, 3000.0], "onset_est": 0, "confidence": 1, "shift": 0, "still": np.nan})
    ev = pd.DataFrame({"onset": [100.0, 2950.0], "offset": [160.0, 3010.0], "convulsive": [True, False],
                       "eventType": ["sz_foc_f2b", "sz_foc_ia_nm"]})
    a, sz = match_alarms(al, ev, EvalConfig())
    assert list(a.kind) == ["true", "false", "other_seizure"]
    assert sz.detected.iloc[0] and sz.delay_s.iloc[0] == 25.0


def test_branch1_prior_and_patient_block():
    from epicare_b2.msg_wrist import branch1_hourly_prior, patient_block
    b1 = {"timeline": {"start": "2020-03-01T00:00", "p1": [0.01, 0.02, None, 0.10]}}
    hours, shift, r_bar = branch1_hourly_prior(b1, "America/Chicago", 1.0)
    assert hours[0] == 1583042400 and np.allclose(np.diff(hours), 3600)       # local midnight = 06:00 UTC
    assert abs(r_bar - 0.13 / 3) < 1e-9 and abs(shift[3] - np.log(0.10 / r_bar)) < 1e-9
    assert shift[0] == -1.0 and shift[2] == 0.0      # capped; missing hour = average risk (no shift)
    al = pd.DataFrame({"prior": [False, False, True], "t": [hours[0] + 60, hours[3] + 30, hours[3] + 30],
                       "confidence": 0.8, "shift": [0.0, 0.0, 1.0], "still": np.nan, "near_seizure": [False, True, True]})
    blk = patient_block({"id": "1869", "alarms": al, "hours": 48.0, "seizures": np.array([hours[3]]),
                         "r_bar": r_bar, "period": (hours[0], hours[-1] + 3600), "tz": "America/Chicago"})
    assert blk["id"] == "1869" and blk["metrics"]["fa_per_day_no_prior"] == 0.5 and blk["metrics"]["fa_per_day"] == 0
    assert len(blk["detections"]) == 1 and blk["detections"][0]["time"] == "2020-03-01T03:00"


def test_end_to_end_synthetic(tmp_path):
    from epicare_b2.pipeline import cross_validate, load_subjects, prior_effect, fa_at_sensitivity
    from epicare_b2.preprocessing import process_dataset
    from epicare_b2.synthetic import SynthConfig, make_dataset
    sc = SynthConfig(subjects=("sub-001", "sub-002", "sub-003", "sub-097", "sub-098"), runs_per_subject=1,
                     run_h=0.5, convulsive_per_run=(1, 2))
    make_dataset(tmp_path / "raw", sc)
    cfg = Config()
    cfg.model.n_estimators = 50
    cfg.decision.threshold_grid = (0.4, 0.6)
    cfg.decision.min_positive_grid = (15.0, 20.0)
    process_dataset(tmp_path / "raw", cfg, out=tmp_path / "proc", verbose=False)
    S = load_subjects(tmp_path / "proc")
    res = cross_validate(S, cfg, verbose=False)
    o = res["overall"]
    assert o["n_seizures"] >= 2 and o["sensitivity"] >= 0.5 and np.isfinite(o["fa_per_day"])
    curve = prior_effect(res["preds"], cfg, None, thresholds=[0.5])
    assert set(fa_at_sensitivity(curve).prior) == {"none", "useless", "branch1", "perfect"}


if __name__ == "__main__":
    import inspect
    import warnings
    warnings.filterwarnings("ignore")
    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                if "tmp_path" in inspect.signature(fn).parameters:
                    with tempfile.TemporaryDirectory() as td:
                        fn(Path(td))
                else:
                    fn()
                print(f"PASS {name}")
            except Exception as e:  # noqa: BLE001
                failed += 1
                print(f"FAIL {name}: {e!r}")
    sys.exit(1 if failed else 0)
