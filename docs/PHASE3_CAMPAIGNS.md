# Phase 3 — FB-CAMPAIGN-01

**Scientific scope:** automated, subject-disjoint train/validation/test evaluation
of already-produced gaze predictions. It does NOT train a reinforcement-learning
agent, measure human subjective quality, or rank physical GPUs.

Run on Ubuntu, macOS, or CI (Python 3.10+):

    python3 -m foveabench.phase3 datasets
    python3 -m foveabench.phase3 run --generate-phase1 --output results/campaign-001 --seed 20261010
    cat results/campaign-001/report.md

Or analyze your completed Phase 1 evidence:

    python3 -m foveabench.phase3 run --phase1-frames results/phase1/frames.csv --output results/campaign-002

Evidence: per_subject.csv, summary.csv, selected_policies.csv,
test_uncertainty.csv, splits.csv, manifest.json, report.md, STATUS.md.

Subject-level split prevents leakage across repeated recordings. The optimizer
chooses the lowest training-set mean angular loss for each known simulator
condition, then locks its choices before examining validation/test outcomes.
Missing predictions incur a disclosed 90-degree engineering penalty. A paired
subject-level bootstrap estimates variation; synthetic subjects do not justify
inference about real people. A known simulator condition is NOT necessarily
observable at inference time, so the selection lookup is not a live controller.

For native Vulkan and concurrent execution, install the Phase 2 toolchain, then:

    bash scripts/run_three_tracks.sh

Phase 1 and Phase 2 start concurrently. Phase 3 starts only when Phase 1 data
are complete. Phase 2 results are not silently pooled into causally aligned
gaze/render events. Real rasterized VRS, participant gaze and human perceptual
validation still require separate experiments.

The full dataset inventory is at benchmark_spec/datasets/registry.json.
**Catalogued means discoverable, NOT downloaded or licensed for redistribution.**
Data use requires checking publisher licenses and source-coordinate semantics;
the interchange is specified in benchmark_spec/datasets/FORMAT.md.

## Future RL

The current full-information model selector is NOT RL. A true adaptive
controller requires observable state at decision time, valid actions, reward
feedback (GPU time, image quality, power, frame deadline), runtime constraints,
and separation of training, validation and sealed test scenarios. A black-box
algorithm without tunable knobs or a learning interface cannot be universally
improved by reinforcement learning.
