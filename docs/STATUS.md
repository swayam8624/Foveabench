# Research execution ledger

Date: 2026-10-10. Evidence from GitHub Actions https://github.com/swayam8624/Foveabench/actions/runs/38041402849: 5 numerical tests passed, 360 synthetic model frames across 30 conditions, complete CSV/SVG/artifact upload. A follow-up revision adds a short-run saccade-switch regression test. UTM execution remains unverified.

| Item | Status | Evidence / next gate |
| --- | --- | --- |
| Repository baseline | INSPECTED | Original main contained only LICENSE |
| Deterministic synthetic trace model | IMPLEMENTED, CI VALIDATED | Unit suite and CI |
| Angular foveal regions | IMPLEMENTED, VALIDATION PENDING | Projection test; no HMD calibration |
| Full/fixed/tracked/delayed policies | IMPLEMENTED, VALIDATION PENDING | Synthetic suite |
| Stimulus scenes and sample-sharing model | IMPLEMENTED, VALIDATION PENDING | Full pixel invariant and previews |
| CSV, SVG, manifests, SHA256, failure ledger | IMPLEMENTED, VALIDATION PENDING | Smoke run |
| CI on Ubuntu | PASSED ON GITHUB UBUNTU RUNNER | GitHub Actions |
| Ubuntu 24.04 ARM64 UTM run | NOT_RUN | Follow docs/UTM_UBUNTU.md |
| Actual Vulkan fragment shading rate | NOT_IMPLEMENTED | Feature probing and real GPU testbed |
| ILLIXR adapter | NOT_IMPLEMENTED | Must respect official starter-task AI restrictions |
| Recorded human-gaze benchmarking | NOT_RUN | Provenance/privacy/consent + dataset |
| Live-versus-replay comparison | NOT_RUN | Device-specific capture synchronization |
| Psychophysically validated quality | NOT_RUN | Perceptual study/calibration |
| FPGA/Xilinx Vivado benchmarks | OUT_OF_SCOPE | Hardware project separate; see literature notes |

**Research publication status:** no empirical research claim or preprint is justified by this scaffold. Do not characterize first synthetic outputs as validated efficiency improvements.

Next: execute smoke under CI and locally, audit artifacts, run ARM64 Ubuntu on UTM, then independently build a real Vulkan backend that records GPU timestamps and checks VRS feature support. Work with Brendan on defining the most defensible live/replay validation study.

## October 10, 2026 — Phase 1 new autonomous study

- **FB-GAZE-01 implementation:** independent no-GPU gaze replay/prediction experiment added at `foveabench/phase1.py`.
- **Trial locally:** 12 procedural gaze streams, 10 injected conditions, two causal baselines, 57,600 predictions and a complete result archive; 8/8 Phase 1 integrity tests passed.
- **GitHub Ubuntu CI:** initial phase study passed with full artifact upload. This does not verify execution inside the user's ARM64 UTM guest.
- **Recorded dataset ingestion:** strict profile and license/consent metadata contract available; no third-party dataset downloaded or run yet.
- **GPU / ILLIXR / human validity:** still NOT_IMPLEMENTED or NOT_TESTED. Do not promote simulated angular-error scores to human perceptual ratings.
- **Next gate:** real empirical trace converter and native Vulkan time-instrumented renderer, plus reproduction on ARM64 UTM.

## October 10, 2026 — Native Phase 2 development checkpoint

- **FB-RENDER-01 Vulkan compute backend:** IMPLEMENTED and verified under Mesa software Vulkan on both hosted Ubuntu 24.04 AMD64 and ARM64. GLSL→SPIR-V, Vulkan queue/dispatch, host buffer readback, synthetic scene and gaze policy comparisons are actual native operations.
- **Per-frame Vulkan device timestamps:** QUERY PATH EXECUTED (where queue timestamp capabilities exist); values are software-driver device times on CI, **not GPU performance claims**.
- **Concurrent execution:** PASSED. `scripts/run_dual_tracks.sh` ran the independent 57,600-prediction Phase 1 suite simultaneously with the native Phase 2 benchmark, each in its own result directory.
- **Phase 1 → Phase 2 interchange:** IMPLEMENTED with strict timestamps, coordinate validation and explicit missing-prediction fallback.
- **True hardware spatial VRS:** NOT IMPLEMENTED, only feature discovery. Real GPU measurements remain NOT_RUN.
- **ILLIXR runtime plugin:** NOT IMPLEMENTED (external trace interchange designed; no starter-task source or solutions used).
- **User's local UTM VM execution:** NOT YET VERIFIED.
- **XR live-versus-replay and participant validation:** NOT PERFORMED.

## October 10, 2026 — Phase 3 execution

- **FB-CAMPAIGN-01**: IMPLEMENTED and validated on hosted Ubuntu; train/validation/test split by identity, with full-information offline predictor selection using *train* labels only and paired identity-level bootstraps on heldout comparisons.
- **57,600 synthetic prediction outcomes**, 12 **synthetic identities** and 10 conditions analyzed in hosted CI. These 12 IDs are *not 12 participants*.
- **ARM64 three-track execution**: PASSED. Phase 1/2 launched concurrently; Phase 3 consumed Phase 1 evidence after it completed. Workflow: https://github.com/swayam8624/Foveabench/actions/runs/38049717202
- **17 dataset catalog entries**: 2 generated procedural sources, 15 external sources **not downloaded** or gated. Registry does not assert redistribution rights.
- **Actual RL optimization**, empirical gaze measurements, real GPU VRS, live ILLIXR integration, headset power, perceptual subjects: NOT IMPLEMENTED/NOT VALIDATED.
