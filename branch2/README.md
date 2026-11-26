# EpiCare: Branch 2, convulsive seizure detection

Answers "is a convulsive seizure happening right now?" from the accelerometer, within about
20 seconds, and keeps false alarms low with heart rate and the Branch 1 prior, as specified in
`EpiCare Report.pdf` §5. Dataset: *SeizeIT2* (OpenNeuro
[ds005873](https://openneuro.org/datasets/ds005873), CC0), plus our own recordings of everyday
look-alike movements.

```
branch2/
├── epicare_b2/                 the package
│   ├── config.py               every setting from the report in one place
│   ├── edf.py                  EDF reader / writer (numpy only, no pyedflib)
│   ├── io_seizeit2.py          BIDS runs, events.tsv, accelerometer picked from EDF labels, inspector
│   ├── signals.py              32 Hz, magnitude, high-pass, 10 s windows 50 % overlap, labels, ECG -> HR
│   ├── features.py             hand-made features (rhythm, 2-8 Hz power, regularity, energy...) + HR
│   ├── preprocessing.py        runs -> data/processed/<subject>/windows.npz
│   ├── models/
│   │   ├── baseline.py         random forest (or XGBoost) on the features
│   │   └── cnn.py              small 1D CNN on the raw window, optional physiology branch, ONNX export
│   ├── decision.py             consecutive positive windows, refractory, alarms/hour cap, Branch 1 prior
│   ├── evaluation.py           sensitivity per seizure, false alarms / 24 h, delay, decision tuning
│   ├── pipeline.py             patient-grouped CV, simulation of the Branch 1 link (report §7)
│   ├── lookalike.py            our look-alike recordings (CSV) -> false-alarm test or hard negatives
│   ├── msg_wrist.py            fusion: detector on Branch 1's wrist archives with Branch 1's prior
│   ├── download.py             SeizeIT2 from OpenNeuro's public S3 bucket (resumable, no account)
│   ├── app_export.py           results -> JSON for the app (branches.branch2)
│   ├── synthetic.py            fake SeizeIT2-layout dataset + look-alike CSVs, to test without download
│   └── __main__.py             command line
├── tests/test_branch2.py       10 quick tests:  python tests/test_branch2.py
└── data/ models/ results/      created on use, ignored by git
```

## Quick start

```bash
pip install -r requirements.txt
python tests/test_branch2.py                       # 10 tests, ~10 s

# whole chain on synthetic data (no download)
python -m epicare_b2 synth                         # data/synthetic + data/lookalike_synth
python -m epicare_b2 preprocess data/synthetic --out data/processed_synth --keep-signal
python -m epicare_b2 evaluate --processed data/processed_synth --lookalike data/lookalike_synth
python -m epicare_b2 export-app --processed data/processed_synth --lookalike data/lookalike_synth --synthetic
```

Real data:

```bash
python -m epicare_b2 download --convulsive-only    # 38 subjects with a convulsive seizure, 19 GB
python -m epicare_b2 download                      # all 125 subjects: mov + ecg + events, 53 GB (of 126 GB)
python -m epicare_b2 inspect data/raw/ds005873     # FIRST: channel labels, units, seizure types
python -m epicare_b2 preprocess data/raw/ds005873 --keep-signal
python -m epicare_b2 evaluate --model rf           # baseline (milestone M2)
python -m epicare_b2 evaluate --model cnn_phys     # main model (M4, needs torch)
```

## What the dataset looks like (from the OpenNeuro mirror and the SeizeIT2 paper)

* `sub-001` … `sub-125`, one session `ses-01`, several runs each:
  `sub-001/ses-01/{eeg,ecg,emg,mov}/sub-001_ses-01_task-szMonitoring_run-01_<mod>.edf`.
* Events only in `eeg/…_events.tsv`: `onset duration eventType lateralization localization
  vigilance confidence channels dateTime recordingDuration`. `bckg` and `impd` (impedance check)
  are not seizures. Convulsive here = `sz_foc_f2b` (focal to bilateral tonic-clonic, 55 in the
  paper) and generalised motor tonic-clonic / clonic codes (`config.CONVULSIVE_*`).
* `mov`: 25 Hz, 12 channels (accelerometer + gyroscope of two modules: back of the neck and
  left chest). **Not the wrist.** Channel labels and units are read from the EDF header; the
  chest module is preferred (`sensor_preference`), units are converted to g from the header or,
  if missing, from the ~1 g resting magnitude. Run `inspect` once on the real data to confirm.
* `ecg`: 256 Hz, 1 channel → heart rate per window and its change from the previous 5 minutes.
  No EDA in SeizeIT2: the EDA feature stays NaN (the random forest handles missing values).
* Paper split: train `sub-001`–`096`, validation `sub-097`–`125` (`--split paper`, default).

## Design choices

* **Same input for every source.** SeizeIT2 (25 Hz chest), Empatica E4 (32 Hz wrist), a
  phone or a watch all go through `process_signal`: resampled to 32 Hz, magnitude of the raw
  axes, then a 0.5–12 Hz band-pass that removes gravity.
* **No look-ahead.** Features only use the current and past windows, so the delay measured is
  the delay the patient would get. The stillness after an alarm is checked separately
  (`still` column) for alerts that can wait.
* **Decision over time.** `min_positive_s` of consecutive positive windows (20 s = 3 windows),
  one alarm per episode (5 min refractory), at most 3 alarms per hour. Threshold and duration
  are tuned on out-of-fold predictions of the training patients, never on the test patients.
* **Counting.** An alarm in `[onset − 30 s, offset + 60 s]` of a convulsive seizure is a
  detection; an alarm during a non-convulsive seizure counts as neither a detection nor a false
  alarm; every other alarm is false. False alarms are per 24 h of recording.
* **Branch 1 prior.** `logit p' = logit p + clip(log(r / r̄), −1, 1)`; the cap is re-applied inside
  the detector, so no forecast can push it further. SeizeIT2 and My Seizure Gauge share no
  patients, so the link is tested by simulation (`pipeline.prior_effect`): each test hour gets
  a shift drawn from Branch 1's real out-of-sample behaviour (read from
  `../app/data/app_data.json`), and the run is repeated with no prior, a useless and a
  perfect forecast. The result is read as false alarms per day at 90 % sensitivity.

## Look-alike recordings (to collect)

One CSV per recording in `data/lookalike/`, named `<activity>__<anything>.csv`, columns
`t, x, y, z` (seconds; g or m/s², detected) and optionally `hr`. Activities from the report:
brushing teeth, clapping, running, shaking a bottle, bus or car, shivering, playing an
instrument, tremor. Use them either as the false-alarm test (`--lookalike`) or as training
hard negatives (`--lookalike … --hard-negatives`), never both.

## Fusion with Branch 1

SeizeIT2 and My Seizure Gauge share no patients. To show both branches for the *same* patient,
`fuse` trains the final detector on all SeizeIT2 subjects (decision tuned out-of-fold), then
runs it on the Empatica E4 wrist accelerometer (32 Hz) + HR + EDA of Branch 1's archives, with
Branch 1's out-of-sample hourly risk as the prior (`msg_wrist.py`). Per Branch 1 patient it
reports false alarms per day of real wrist wear with and without the prior, and the alarms
near a recorded seizure (MSG seizures have no type, so no sensitivity there). This is also the
wrist placement check of §5.6.

```bash
python -m epicare_b2 fuse --archives ../branch1/data/raw/Mayo_*.zip     # -> ../app/data/branch2.json
cd ../mobile && npm start                                              # the app shows it (Détection tab)
```

## App

`export-app` writes the `branches.branch2` block of the shared schema `epicare.app/1`.
`export-app` writes to `results/branch2_app.json` by default; `fuse` writes
`../app/data/branch2.json` with the per-patient wrist results. With `--out ../app/data/branch2.json`, the
app and `mobile/` (`npm start`) merge it with Branch 1's file automatically.
