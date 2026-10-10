# Phase 1 execution and audit — FoveaBench FB-GAZE-01

## One-command study

From cloned repository root under Ubuntu 24.04 ARM64 (UTM), macOS, or native
Linux with Python 3.10+:

```bash
python3 -m foveabench.phase1 run \
  --config benchmark_spec/profiles/fb-gaze-01.json \
  --output results/phase1-first-study --seed 20261010
```

This study uses Python standard library only; the existing v0.1 software image
reference still requires NumPy. If the repository is cloned for the first time:

```bash
git clone https://github.com/swayam8624/Foveabench.git
cd Foveabench
python3 -m foveabench.phase1 run --output results/phase1-first-study
```

Results are never overwritten. Choose a new directory for a subsequent run.
For the full existing model see the root README.

### Profile

12 synthetic traces = 3 synthetic classes (fixation/pursuit/jump) × 4 seeded
variants, 240 frames each, at 90 Hz. There are 10 controlled conditions:
clean, 20/60 ms delay, jitter, 0.5/2 deg noise, 10/30% dropout and two combined
conditions. Two causal algorithms (hold and bounded velocity) are compared on
exactly the same delivered observations. Total **57,600 frame–model–condition
evaluations**. These frames are *not* independent human subjects.

### Output

- `frames.csv`: every prediction and true withheld normalized gaze; timestamps,
  per-frame angular error and geometric velocity classification.
- `per_trace.csv`: mean/P95 per continuous trace and availability.
- `summary.csv`: availability, P50/P95/P99, error/miss metrics, quality gate.
- `paired.csv`: paired trace-level mean difference between baselines.
- `profile.json`: exact declared scenario configuration.
- `dataset_metadata.json`: source, license/provenance and measurement caveats.
- `manifest.json`: engine/config/dataset hashes, machine/version and checks.
- `STATUS.md`: objective audit ledger with unsupported/not-run evidence.
- `report.md`: readable auto-generated comparison table.

### Interpretation

The `5°` threshold defines a *geometric* region-miss test; it is NOT proof a
person could perceive the difference. The quality gate uses provisional
availability ≥95% and region-miss rate ≤5%. Results may be marked `FAIL` by
this gate without causing a crash; this is useful and **not a software
unit-test failure**. A negative paired difference (`velocity - hold`) means
velocity has lower mean angular error for that specified trace condition.

The synthetic jump event is an instantaneous workload discontinuity, **not** a
physiologically accurate model of the saccade trajectory. These artificial
fault distributions are not claimed to fit human eye-tracker statistics.

### Linux VM

The UTM ARM64 VM is appropriate for running this entirely headless analysis.
No headset or Vulkan ICD is required. Later GPU results must be measured on
supported physical GPU hardware, not inferred from VM timings.

### Traceability / correctness

Run: `python3 -m unittest discover -s tests -p test_phase1.py -v`.
Validation checks include monotonic timestamps, finite coordinates,
strict dataset provenance, no future sample access, out-of-order delivery,
paired conditions, and full artifact generation. Neither tests nor CI can
certify the suitability of a participant study or device rendering fidelity.
