# FoveaBench research roadmap (2026-10-10)

## Scientific north star

Produce *valid decisions* about gaze-contingent XR algorithms from unattended,
repeatable experiments. Do NOT claim routine replay is equivalent to live XR
until that predictive validity has been experimentally established. One open
question is whether offline/replay ranking reversals occur under latency,
tracking error, workload change and platform change.

## Five parallel research / engineering phases

| Phase | Calendar target | Engineering track | Research track | Acceptance gate |
|---|---|---|---|---|
| 1. Evidence/specification | October 10–17 | Formal scenario profile, strict input/metadata validation, event-time replay, sensor fault injection, paired baseline study, versioned artifacts, Linux CI | Survey existing ILLIXR/XRBench/FovVideoVDP/MLPerf practices, state hypotheses and measurement limits | Autonomous FB-GAZE-01 suite executes with auditable causal trace/score outputs and complete failure ledger |
| 2. Actual rendering | October 17–November 7 | C++ Vulkan instrumented renderer, shader-rate feature detection, native resource/queue timestamp synchronization, controlled scenes, image dump; ILLIXR adapter if permitted | Benchmark equivalence against image reference, baseline comparability, engine/rate constraints | Hardware-reported GPU results *only* where supported. VM yields functional but not native-GPU results |
| 3. Workload campaigns | November 7–28 | Real gaze dataset ingestion, power/quality modules, formal quality gates, performance/quality Pareto plots, statistically controlled matrix, distributed scheduler | Scene/patient/participant/device coverage; held-out workload robustness; prior state-of-art comparisons | Reproducible baselines under representative empirical traces; quantitative uncertainty and ablations |
| 4. Predictive validity | November 28–January 15 | Live/replay synchronization, hardware/eye-tracker capture pipeline, perceptual study instrument, privacy and fault profiles | Ethics/IRB approval if required, participants/lab logistics, ranking agreement, limits of agreement, perceptual fidelity | Demonstrate validity *domain* of offline rankings or characterize failures; disclose boundaries |
| 5. Open benchmark + paper | January 15–March 2027 | Stable adapter API, hosted reports, packaging, competitor-reproduced releases | Preprint, independent reproduction, thesis and conference manuscript, review response | Code/data/experiment release and scientifically justified paper submission |

Targets depend on physical GPU/headset access and approvals for new human data.
Human participants are NOT involved in Phase 1 routine execution. No IRB
exemption is assumed for later collection.

## Research claims registry

- **C1: (Established)** Deterministic *inputs* can be generated and replayed offline.
- **C2: (Phase 1, limited)** Holding gaze versus bounded linear extrapolation has
  different sensitivity to injected delay, jitter, noise and missing samples in
  specified synthetic scenarios. This does NOT show behavior with real people.
- **C3: (Not established)** FoveaBench automated scores generalize to real scenes,
  headsets, participants or perceptual quality.
- **C4: (Not established)** Replay preserves live algorithm rankings.
- **C5: (Not established)** FoveaBench measures actual Vulkan GPU and headset timings.
- **C6: (Not established)** Benchmark covers realistic industry XR workloads.

## Why Phase 1 includes real dataset contracts but not copied datasets

Published datasets have terms, metadata and original eye-geometry conventions.
The first iteration intentionally refuses arbitrary CSVs without a declared,
consent-appropriate provenance record and an explicit coordinate/timebase
conversion. It neither silently averages binocular eyes nor labels a synthetic
trajectory as a human trace. Integration with GazeBaseVR will need an audited
converter plus the dataset's own documentation and permission terms.

## Scientific methodology principles

1. Same sensor observation stream for every competing predictor within a paired
   (trace, scenario) comparison.
2. Ground truth target gaze is never given to a predictor; only observations
   delivered before the target time may be consumed.
3. Measurement of real gaze *acquisition*, *delivery* and *presentation* times
   is separate from an artificial latency slider.
4. Keep missing predictions distinct from incorrectly predicted directions.
5. Report P50/P95/P99 angular error, quality-gate misses and availability;
   condition on both algorithm and scenario. A single score would hide failures.
6. Preserve per-trace and per-subject aggregation; do not treat adjacent frames
   from the same person as independent samples. Do not interpret synthetic-agent
   variability as a population confidence interval.
7. No GPU or psychophysical assertions without actual corresponding measurements.
8. Quality gate thresholds are provisional and must be reviewed, justified and
   preregistered before any standardized submissions.

## Risks / blockers

- Native hardware GPU and eye-tracked XR headset may be unavailable initially.
- The official ILLIXR starter exercises restrict agentic AI. Keep independent
  FoveaBench development separate and seek clarity for integration with ILLIXR.
- Dataset licenses, calibration and binocular conversion may preclude automatic
  download and one-size-fits-all import.
- FovVideoVDP, LPIPS and similar metrics have environment/model limitations;
  their outputs are not universal perceptual truth.
- Public synthetic workloads may be learned/overfit. Later include held-out
  independent scenes and real participant validation.
- CPU timer reproducibility and GPU measurement comparability differ; never
  report software reference wall time as actual GPU performance.

## Next integration package for Brendan

A compact technical note should ask about available hardware, official ILLIXR
adapter boundaries, live gaze timestamp capture, public/consented datasets,
IRB process and whether a rank-validity or perceptual-validity study best matches
his lab priorities. No email or faculty approval is implied here.
