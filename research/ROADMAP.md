# Development and research program: distinct from completed work

**Product goal:** reusable, safe, fully documented unattended XR testbench with optional Cinebench-style live visualization, dataset ingestion, calibrated perception, real system timing and future *separately tested* adaptive optimization. **Science goal:** establish predictive validity, characterize offline/live ranking failures and, if evidence warrants, create an algorithm to qualify uncertain benchmark conclusions. The two goals must never be confused.

## Work packages with dependency gates

| WP | Scope | Prerequisites | Verifiable gate | Current classification |
|---|---|---|---|---|
| **WP-00** | Lab notebook/claims/results/code map and SHA archive | Current code/UTM outputs | Docs, code indexing and SHA tamper tests in CI | **Implemented by this PR**, raw UTM hashing must be done on VM |
| **WP-01** | Offline native visual showcase refinement | Phase 2 renderer and static UI | Actual captured PNG/HTML replay, no synthetic UI image substitution | **Implemented**, CI verified, user viewer UI feedback pending |
| **WP-02** | Empirical gaze data adaptation | GazeBaseVR license, original channel semantics | Real gaze importer with unit/time/eye/participant audit; genuine disjoint people | **NOT STARTED** |
| **WP-03** | Reproduce ETRA gaze forecasting | WP-02; original authors' code and protocol | Reproduced compatible fixation/saccade table with error accounting | **NOT STARTED** |
| **WP-04** | Human perceptual validation | FovVideoVDP setup; licensed ratings/stimuli | Correlations and rank disagreement on withheld people/stimuli with uncertainty | **NOT STARTED** |
| **WP-05** | Actual raster 3D/Vulkan VRS workload | Physical device supporting VRS, representative scene data, graphics engineer access | `VK_KHR_fragment_shading_rate` actual graphics pipeline, invocation counters, real GPU present/energy instrumentation | **NOT STARTED**; UTM llvmpipe insufficient |
| **WP-06** | Real-time Cinebench-like desktop runner | WP-05 or justified real-time CPU graphic fallback | Live frame-rate/hardware load visible *during* rendering; verify wall-clock vs GPU timers | **NOT IMPLEMENTED**: current viewer is postcapture replay |
| **WP-07** | Authorized ILLIXR adapter, synchronized eye/head/display events | Clarify official starter-task AI restrictions; supervisor and integration permission | Per-frame timestamp provenance, consent, no unlicensed code use | **NOT IMPLEMENTED** |
| **WP-08** | Live-vs-replay controlled study | WP-02, WP-04/05/07, approved human protocol as applicable | Predeclared ranking-reversal analysis and bias/limits of agreement, participant clusters | **NOT PERFORMED** |
| **WP-09** | Reliability-envelope estimator / experiment selection | WP-08 real labels and credible baselines | Calibrated risk vs coverage and prospective unseen-device/subject evaluation | **HYPOTHESIS ONLY** (`N-001`, `N-002`, `N-004`) |
| **WP-10** | Learning-based foveation optimization | Real task constraints/costs, WP-04/05+ real validated data | Compare static/heuristic, search, bandit and optionally RL; include decision overhead and no quality-gate regression | **HYPOTHESIS ONLY** (`N-006`) |
| **WP-11** | Independent reproduction/release/publication | Suitable WP-02..09 claims and reproducibility dossier | Outside lab repeat, committed data licenses, methods code and honest limitations | **NOT READY** |

## Recommended operational order

- **Now:** ship research records and run `research_archive.py archive` on your original UTM evidence. Preserve the script/version, device manifest, zip and 256-bit hashes. Verify one dry-run clone can recreate the visual viewer and model summary.
- **Next:** obtain one small, permitted sample of GazeBaseVR or similar public VR gaze; compare parser outputs to original schema and test strict subject ID isolation. No model-training loop against test yet.
- **In parallel:** make the render path genuinely graphics hardware-capable on a suitable VRS GPU while maintaining CPU/software CI fallback; collect scenes with explicit licensing.
- **After data:** reproduce ETRA 2026 gaze accuracy and FovVideoVDP published metrics separately, preserve negative mismatches and data constraints. Only then set up a real offline/live agreement study with the supervisor.
- **Only after observed failures:** formulate N-001/N-002 statistical reliability estimator, validate real-world calibration; investigate RL if a sequential reward/latency/power environment actually exists.

## Research publication decision tree

If we only implement code and capture pretty frames → **engineering/benchmark artifact**, possibly systems tooling venue if broadly useful but no claim of new scientific finding.

If we find an independently reproducible failure pattern of replay preserving rankings and characterize its conditions → **empirical measurement/methods paper**.

If a calibrated method predicts those failures prospectively better than existing reliability/calibration baselines → **additional algorithmic scientific contribution**.

If published human quality/timing papers are not independently reproduced, still release useful engineering work with honest scope; never fabricate results.

## Gate acceptance evidence template

`WP-ID | owner | date UTC | branch/commit | raw run dir hash | dataset license + split | scene/device/timestamp settings | baseline outputs | statistical unit | effect/CI | evidence level | PASS/FAIL/NOT_RUN | scientific limitations | next reviewer action`.
