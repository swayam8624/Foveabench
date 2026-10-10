# FB-LEARN-TRANSFER: frozen-checkpoint diagnostics and unseen synthetic identities

First inspect the learned gate on the existing saved test predictions:

    python -m foveabench.learn_transfer inspect --ml-output results/ml-utm-20261010T153731Z

Then generate NEW synthetic subjects. Copy the checked-in benchmark profile
and set `synthetic_sessions_per_kind` to 8 (rather than the original 4).
Use a **new seed**. IDs 04–07 in each motion class will be unseen by
the initial learned model. The tool excludes all 00–03 IDs using
the original saved `splits.csv`, even when the new seed changes their traces.

    python - <<'PY'
    import json
    from pathlib import Path
    src=Path('benchmark_spec/profiles/fb-gaze-01.json')
    p=json.loads(src.read_text())
    p['synthetic_sessions_per_kind']=8
    Path('benchmark_spec/profiles/fb-gaze-transfer-8.json').write_text(json.dumps(p,indent=2)+'\n')
    PY
    python -m foveabench.phase1 run --config benchmark_spec/profiles/fb-gaze-transfer-8.json \
      --seed 20261112 --output results/fresh-phase1-001
    python -m foveabench.learn_transfer evaluate \
      --ml-output results/ml-utm-20261010T153731Z \
      --phase1-frames results/fresh-phase1-001/frames.csv \
      --output results/transfer-new-identities-001

The evaluation freezes the checkpoint, rejects reuse of the exact training
file hash, excludes previously used synthetic subject IDs, prints verbose
progress bars and exports per-movement hold/velocity/learned comparisons.
Outputs: comparison.csv, test_predictions.csv, manifest.json, report.md.

Important: training and fresh-seed evaluation use the SAME procedural
trajectory families and simulator. These are not independent real human
recordings, even though seed and synthetic identities differ. Do not tune
the model to this evaluation and then describe it as an untouched holdout.
Real gaze dataset use, trusted physical GPU timing and ILLIXR integration
remain outside this module.