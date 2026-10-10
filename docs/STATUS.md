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
