"""Command line:  python -m epicare_b2 <command> ...

  synth        synthetic SeizeIT2-format dataset + look-alike recordings (no download needed)
  download     download SeizeIT2 from OpenNeuro (motion, ECG, events only; resumable)
  inspect      list runs, channel labels, seizure types of a SeizeIT2 folder (run this first)
  preprocess   SeizeIT2 folder -> data/processed/<subject>/windows.npz
  evaluate     patient-grouped evaluation (+ prior simulation, + look-alike test)
  fuse         evaluate on SeizeIT2, train the final detector, run it on Branch 1's wrist archives
               with Branch 1's prior, and write ../app/data/branch2.json (what the app shows)
  export-app   evaluate, then write the JSON read by the app (default results/branch2_app.json;
               ../app/data/branch2.json to show it in the app)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import Config


def _evaluate(a, cfg):
    from .evaluation import lookalike_alarms
    from .pipeline import cross_validate, fa_at_sensitivity, load_subjects, prior_effect
    S = load_subjects(a.processed, a.ids)
    extra = None
    looks = None
    if a.lookalike:
        from .lookalike import load_lookalikes
        looks = load_lookalikes(a.lookalike, cfg)
    if looks and a.hard_negatives:
        extra, looks = looks, None      # never train and test on the same recordings
    res = cross_validate(S, cfg, extra_negatives=extra)
    curve = prior_effect(res["preds"], cfg, a.branch1_json)
    prior = fa_at_sensitivity(curve, cfg.eval.target_sensitivity)
    la = None
    if looks and "detector" in res:
        from .lookalike import lookalike_preds
        dec = res["decisions"][-1]
        la = lookalike_alarms(lookalike_preds(looks, res["detector"], cfg), cfg.decision, dec["threshold"],
                              dec["min_positive_s"], cfg.pre.window_s, cfg.pre.step_s)
    return S, res, curve, prior, la


def main(argv=None):
    ap = argparse.ArgumentParser(prog="epicare_b2")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("synth")
    s.add_argument("--out", default="data/synthetic")
    s.add_argument("--lookalike-out", default="data/lookalike_synth")

    s = sub.add_parser("download")
    s.add_argument("--out", default="data/raw/ds005873")
    s.add_argument("--ids", nargs="*", default=None, help="subjects (default: all)")
    s.add_argument("--convulsive-only", action="store_true",
                   help="only subjects with a convulsive seizure (events are fetched first)")
    s.add_argument("--modalities", nargs="+", default=["mov", "ecg", "events"])
    s.add_argument("--workers", type=int, default=4)
    s.add_argument("--dry-run", action="store_true", help="only print the number of files and GB")

    s = sub.add_parser("inspect")
    s.add_argument("root")
    s.add_argument("--runs", type=int, default=3)

    s = sub.add_parser("preprocess")
    s.add_argument("root")
    s.add_argument("--out", default="data/processed")
    s.add_argument("--ids", nargs="*", default=None, help="subjects, e.g. sub-001 sub-002")
    s.add_argument("--keep-signal", action="store_true", help="save the 32 Hz signal (needed for the CNN)")
    s.add_argument("--no-ecg", action="store_true")

    for name in ("evaluate", "export-app", "fuse"):
        s = sub.add_parser(name)
        s.add_argument("--processed", default="data/processed")
        s.add_argument("--ids", nargs="*", default=None)
        s.add_argument("--model", choices=["rf", "xgb", "cnn", "cnn_phys"], default="rf")
        s.add_argument("--no-physiology", action="store_true")
        s.add_argument("--split", choices=["paper", "gkfold"], default="paper")
        s.add_argument("--lookalike", default=None, help="folder of look-alike CSV recordings")
        s.add_argument("--hard-negatives", action="store_true",
                       help="train on the look-alike recordings instead of testing on them")
        s.add_argument("--branch1-json", default="../app/data/app_data.json",
                       help="Branch 1 app export, for the prior simulation")
        s.add_argument("--out", default={"evaluate": "results", "export-app": "results/branch2_app.json",
                                         "fuse": "../app/data/branch2.json"}[name])
        if name in ("export-app", "fuse"):
            s.add_argument("--synthetic", action="store_true")
        if name == "fuse":
            s.add_argument("--archives", nargs="+", required=True, help="Branch 1 archives Mayo_<id>.zip")
            s.add_argument("--period", choices=["timeline", "all"], default="timeline",
                           help="timeline: only hours with Branch 1's out-of-sample risk")
            s.add_argument("--max-sessions", type=int, default=None)
            s.add_argument("--model-out", default="models/detector.pkl")

    a = ap.parse_args(argv)
    cfg = Config()
    if a.cmd == "synth":
        from .synthetic import make_dataset, make_lookalikes
        print(make_dataset(a.out))
        print(make_lookalikes(a.lookalike_out))
    elif a.cmd == "download":
        from .download import download
        from .io_seizeit2 import convulsive_subjects
        ids = a.ids
        if a.convulsive_only:
            download(a.out, None, ("events",), workers=16)
            ids = convulsive_subjects(a.out)
            print(f"{len(ids)} subjects with a convulsive seizure: {' '.join(ids)}")
        download(a.out, ids, tuple(a.modalities), a.dry_run, a.workers)
    elif a.cmd == "inspect":
        from .io_seizeit2 import inspect_dataset
        inspect_dataset(a.root, a.runs)
    elif a.cmd == "preprocess":
        from .preprocessing import process_dataset
        process_dataset(a.root, cfg, a.ids, a.out, keep_signal=a.keep_signal, with_ecg=not a.no_ecg)
    elif a.cmd in ("evaluate", "export-app", "fuse"):
        cfg.model.kind = a.model
        cfg.model.use_physiology = not a.no_physiology
        cfg.eval.split = a.split
        S, res, curve, prior, la = _evaluate(a, cfg)
        print("\nOverall (test patients):", json.dumps({k: (round(v, 3) if isinstance(v, float) else v)
                                                       for k, v in res["overall"].items()}))
        print(res["per_subject"].to_string(index=False))
        print("\nPrior effect at the target sensitivity:\n" + prior.to_string(index=False))
        if la is not None:
            print("\nLook-alike activities:\n" + la.to_string(index=False))
        if a.cmd == "evaluate":
            out = Path(a.out)
            out.mkdir(parents=True, exist_ok=True)
            res["per_subject"].to_csv(out / f"subjects_{a.model}.csv", index=False)
            res["alarms"].to_csv(out / f"alarms_{a.model}.csv", index=False)
            res["seizures"].to_csv(out / f"seizures_{a.model}.csv", index=False)
            curve.to_csv(out / f"prior_curve_{a.model}.csv", index=False)
            if la is not None:
                la.to_csv(out / f"lookalike_{a.model}.csv", index=False)
            (out / "config.json").write_text(json.dumps(cfg.to_dict(), indent=1, default=str))
        else:
            from .app_export import branch2_block, export_app_data
            imp = res["detector"].model.importances() if "detector" in res and a.model in ("rf", "xgb") else {}
            patients = None
            if a.cmd == "fuse":
                from .msg_wrist import run_branch1_patients
                from .pipeline import fit_final, save_model
                print("\nFinal detector on all SeizeIT2 subjects ...")
                final = fit_final(S, cfg)
                print("decision:", final["decision"], "->", save_model(final, a.model_out))
                patients = run_branch1_patients(a.archives, final, cfg, a.branch1_json, a.period, a.max_sessions)
            block = branch2_block(res, cfg, a.synthetic, prior, la, imp, patients)
            print(export_app_data(block, a.out))


if __name__ == "__main__":
    main()
