# FoveaBench — Research Record of Truth

**Record epoch:** 2026-10-10 UTC. **Repository:** [`swayam8624/Foveabench`](https://github.com/swayam8624/Foveabench). **Audited implementation head:** `ba1d50bdb9de35e123e348804edae66776dd7bfc` (before this documentation update). This is a longitudinal lab notebook, not a claim that FoveaBench is a validated XR performance standard.

## Scope and navigation

| Permanent record | What it answers | Source-of-truth convention |
|---|---|---|
| [`CLAIMS.md`](CLAIMS.md) | Every candidate novelty, prior-art distinction, testable claim, and its falsification test | **Claims are hypotheses unless evidence says otherwise** |
| [`CODE_AND_TEST_MAP.md`](CODE_AND_TEST_MAP.md) | Every tracked subsystem, core function family, C++/GLSL shader, test, workflow, and execution path | Actual code paths, not conceptual wishlists |
| [`RESULTS.md`](RESULTS.md) | Numbers from local UTM, arm64/amd64 GitHub CI and prior reference runs | Explicit source, subset, status, limitations |
| [`DEVELOPMENT_LOG.md`](DEVELOPMENT_LOG.md) | Chronological dated development, merges, defects and resolutions | Git commit identities and distinguish local/CI |
| [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) | How to reproduce, hash and inspect work without overwriting past evidence | Commands, environment and immutable artifacts |
| [`RESEARCH_QUESTIONS.md`](RESEARCH_QUESTIONS.md) | Novelty hypotheses, measurement equations, statistical design and failure gates | Mechanisms, controls, falsifiability |
| [`PAPER_AND_HUMAN_VALIDATION.md`](PAPER_AND_HUMAN_VALIDATION.md) | Registered papers, datasets, human comparisons and exact missing prerequisites | **Targets are NOT reproductions** |
| [`ROADMAP.md`](ROADMAP.md) | Work packages, dependencies, acceptance gates, hardware/IRB blockers | Proposed future work, not completed results |
| [`TRACEABILITY.md`](TRACEABILITY.md) | Claim → function → artifact → CI/UTM evidence links | Separates code verification from scientific validation |
| [`RESEARCH_POLICY.md`](RESEARCH_POLICY.md) | Recordkeeping rules, no-overclaim policy, participant safety and publication rules | Mandatory for future development |
| `scripts/research_archive.py` | Automatic tracked code/symbol inventory; SHA-256 manifests for local runs | Does not upload data or certify hardware/human validity |

The existing `docs/` collection is retained as historical implementation documentation. In particular, historical `docs/STATUS.md` contains statements such as “UTM not verified” that were accurate **at that earlier checkpoint**, but are no longer the current status. For current state, read this record alongside [`RESULTS.md`](RESULTS.md) and contemporaneous user terminal logs.

## Current status in one table

| Capability | Current qualification |
|---|---|
| Deterministic synthetic gaze generation and sensor perturbations | **Executed**; synthetic-only, not biological |
| Causal hold/velocity predictor comparisons | **Executed** across prescribed conditions |
| Native Vulkan and SPIR-V execution on Apple UTM ARM64 | **User terminal verified**; **software llvmpipe**, not M2 Pro native GPU |
| User's Phase 1–3 campaign | **User terminal verified** on 2026-10-10; 57,600 prediction outcomes, concurrent Vulkan functional test, held-out synthetic model selection |
| Trainable neural gaze gate | **Executed** with real supervised gradient updates/Adam; frozen checkpoint saved; worse than hold overall |
| Native learned-model image comparisons | **User terminal verified**; 16,848 compute dispatches, no VRS acceleration claims |
| Extra-seed synthetic transfer | **User terminal verified**; 28,474 eligible pairs from 12 new synthetic IDs; no human transfer proof |
| Actual recorded-frame visual playback | **AMD64 and ARM64 CI verified**; user-UTM viewer execution pending new log |
| Real human gaze dataset integration | **Not run**; dataset URLs are catalog entries, not installed data |
| Independent published paper reproduction | **Not run**; registration and evaluators are not published-score replication |
| Physical rasterizer/hardware VRS/GPU speedup | **Not implemented or measured** |
| Actual ILLIXR plugin or eye-tracked headset | **Not implemented**; previous ILLIXR installation does not imply integration |
| RL policy controller | **Not implemented**; offline policy selection and supervised blending are not RL |
| Human-rating correlation / IRB participant study | **Not performed**; analysis API does not create genuine ratings |

## Audit conventions

Each finding is referenced by `F-###` in [`RESULTS.md`](RESULTS.md); each novelty hypothesis by `N-###` in [`CLAIMS.md`](CLAIMS.md); each software capability by `C-###` in [`CODE_AND_TEST_MAP.md`](CODE_AND_TEST_MAP.md); and each milestone by `D-###` in [`DEVELOPMENT_LOG.md`](DEVELOPMENT_LOG.md). All documents point to these durable identifiers.

**Three levels of evidence:** (1) source inspected / test contract; (2) program executed in CI or user VM; (3) independently reproduced real-world scientific conclusion. A Level 1 or 2 achievement must never be relabeled Level 3. GitHub Actions URLs prove workflow execution only; they do not create equivalence with UTM or actual headset hardware.

**Raw evidence:** output under `results/` is `.gitignore`d and remains on the originating computer or in Actions artifacts. Our transcribed results are *not* a substitute for preserved raw files. Use `scripts/research_archive.py archive` to create integrity hashes, and separately back up raw files with access controls. Do not push private participant recordings.
