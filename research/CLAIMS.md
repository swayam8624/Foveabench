# Candidate novelty and scientific-claim registry

**Reviewed against repository at:** `ba1d50b` (2026-10-10). “Novelty” below means a **candidate direction**, not a confirmed world-first. Before claiming priority, conduct a formal dated systematic literature and patent/code audit, then demonstrate independent experimental improvement. A testbench is not automatically a new algorithm.

## Prior art and what is NOT our contribution

| Item | Already existed | Implication |
|---|---|---|
| ILLIXR | Modular XR runtime and instrumentation | We cannot claim the first modular XR testbed or that it is already integrated |
| XRBench | Reproducible XR system/ML workloads and multiobjective evaluation | We cannot claim XR workload benchmarking or score combination is new |
| FovVideoVDP | Gaze-/eccentricity-dependent image/video perceptual difference prediction and human validation | Basic gaze-weighting and evaluating subjective correlation are not inventions |
| GazeBaseVR and ETRA prediction research | Recorded VR eye trajectories and prior forecasting baselines | Synthetic gaze replay and hold-vs-velocity prediction alone are not new |
| Classic RL/bandits/CMA-ES/Bayesian optimization | Adaptive configuration search and constrained feedback learning | Calling PPO/CMA-ES for foveation does not by itself supply novelty |
| Cinebench-style viewers and frame replay | Visual benchmarking and post-render display | A visual GUI is a product feature, not a scientific finding |

References and original-study protocols: [`../docs/PAPER_REPLICATION_AND_VALIDITY.md`](../docs/PAPER_REPLICATION_AND_VALIDITY.md), [`../benchmark_spec/papers/reproduction_registry.json`](../benchmark_spec/papers/reproduction_registry.json). Do not assume these cover all related work.

## Novelty candidate register — ideas with falsification protocols

| ID | Candidate contribution | Status 2026-10-10 | What would demonstrate science, not just engineering? | What would falsify or demote it? |
|---|---|---|---|---|
| **N-001** | **Replay-validity envelope:** empirically map when unattended gaze-contingent XR evaluations preserve live-human algorithm rankings | **PROPOSED, not validated** | Same algorithms and stimuli in causally matched offline and live headset sessions; estimate ranking reversals with subject/device uncertainty and boundary conditions | Live/replay rankings are already stable, no measurable boundary, or existing prior art establishes same result |
| **N-002** | **Reliability qualification:** calibrated model predicts if an offline algorithm ranking is trustworthy given observable deployment conditions | **PROPOSED** | Prospective, unseen participant/device calibration and selective prediction; reliability intervals and abstention/coverage curves outperform baselines | Learned confidence is uncalibrated, underperforms simple thresholds, or depends on future/offline unavailable observables |
| **N-003** | **Failure-seeking valid workload synthesis:** discover physically plausible conditions that induce latency/perceptual failures or ranking reversals | **PROPOSED** | Constrain perturbations using measured distributions and show discovered failures transfer to real recordings/devices | Generator exploits simulator artifacts, breaks sensor physics, or repeatedly selects unrealistic saccades |
| **N-004** | **Adaptive experiment budgeting:** choose which additional trials/headsets/participants are required to establish a quality-constrained ranking at minimum cost | **PROPOSED** | Sequential design with measured sampling/resource cost, calibrated decision risk, and fewer real runs at equal confidence versus random/fixed allocations | Coverage/risk requirements fail or savings disappear once overhead is included |
| **N-005** | **Temporal human-perceptual failure model** for gaze error events, dropout bursts and foveated frames | **PROPOSED** | Matched subjective ratings plus calibrated display/optics, held-out stimulus/subject test, improvement over established VDP baselines, event-level ablations | No improvement over FovVideoVDP, or gains vanish under cross-display/scene testing |
| **N-006** | **Quality-constrained adaptive foveation controller** optimizing true measured motion-to-photon/quality/energy under gaze uncertainty | **PROPOSED** | Compare constrained search/bandits/RL with strong static and heuristic baselines; measured GPU/energy plus human quality gates, unseen hardware | Synthetic reward exploit, decision overhead erases gains, missing safety gates, or no advantage versus heuristic |
| **N-007** | **Benchmark reproducibility/measurement protocol** explicitly separating gaze time, rendering, hardware and human evidence | **IMPLEMENTED ENGINEERING; potential methods paper if new measurement finding emerges** | Independent labs run compatible workloads, find known errors or ranking changes prevented by protocol; external adoption | Existing standards cover method and no new scientifically consequential finding is demonstrated |
| **N-008** | **System-level XR foveation benchmarking corpus** with synchronized binocular gaze, scenes, timing and device state | **PROPOSED DATASET/BENCHMARK** | Publicly distributable licensed/consented multi-headset captures, unique tasks and independently reproduced baseline | Mere aggregation of pre-existing datasets or inaccessible/proprietary data |

## Implementation/features register — explicitly NOT novelty claims

| ID | Existing achievement | Reason it is an engineering feature |
|---|---|---|
| **I-001** | Procedural fixation/pursuit/jump traces, causal latency/noise/dropout replay | Standard stress generation; does not model human eye physiology |
| **I-002** | Vulkan compute with shader compilation, recorded dispatch timestamps and readback | True implementation, but it executes all pixels and never exercises hardware fragment VRS |
| **I-003** | Fixed/hold/velocity rendering and weighted MSE | Baselines and elementary numeric diagnostics; not calibrated perceptual research |
| **I-004** | Identity-disjoint synthetic train/validation/test and paired analysis | Necessary experimental hygiene; not a new estimator |
| **I-005** | Supervised 9→24→1 tanh/sigmoid blend of two causal predictors, Adam and best-validation checkpoint | A real trained network but ordinary architecture/objective; not RL, and overall did not win |
| **I-006** | Matched neural-to-Vulkan pipeline on software GPU | Valuable end-to-end functional testing; not evidence of performance savings |
| **I-007** | Offline cinematic viewer made from actual native image captures | Demonstration quality and testability, not live XR |
| **I-008** | Paper reproduction target registry and Spearman/participant bootstrap utility | Reproduction *infrastructure*, not completed published-paper replication |
| **I-009** | SHA-256/manifest code inventory and evidence recorder | Research integrity infrastructure, not empirical novelty |

## Claim-readiness gates

**Claim status allowed:** `proposed`, `engineering-implemented`, `synthetic-demonstrated`, `empirically-demonstrated`, `independently-reproduced`, `rejected`. Every claim upgrade must be accompanied by a dated protocol version, original raw file checksums, exact code commit, dataset license/consent, appropriate statistical unit, independent baseline, effect size and limitations.

**No accepted human-replay novelty claim exists as of this record.** If a paper is submitted, report FoveaBench as apparatus unless N-001/2/3/etc. are genuinely tested; do not invent novel algorithms retroactively. See [`RESEARCH_QUESTIONS.md`](RESEARCH_QUESTIONS.md) and [`TRACEABILITY.md`](TRACEABILITY.md).
