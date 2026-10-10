# Source code, execution-path, interface and test inventory

**Snapshot baseline:** repository `main` commit `ba1d50b` (2026-10-10). This manual map covers every tracked implementation, test, automation, specification and doc family found during the audit. It describes actual code — no proposed module is mislabeled as implemented. For every individual function, line number, file hash and added file, generate the **automatic, SHA-256-indexed map** with `python scripts/research_archive.py inventory --repo . --output results/code-inventory-<unique-id>`. Line numbers vary after edits; use function names as the stable referent.

## Production source architecture

| Code ID | Source path | Existing symbols / behavior | Evidence and limits |
|---|---|---|---|
| **C-001** | `foveabench/__main__.py` | `Gaze`, `assert_gaze`, `gaze_trace`, `gaze_at_delay`, `angular_map`, `reference_scene`, `render_reference_model`, `quality_metrics`, `psnr`, `write_ppm`, `write_csv`, `summarize`, `write_svg`, `run`, `main` | Original reference/pinhole image-space model, synthetic sampling, emitted CSV/SVG/PPM; **not native Vulkan** |
| **C-002** | `foveabench/phase1.py` | `Sample`, `Observation`, `verify_samples`, `load_csv`, `validate_manifest`, `synthetic_traces`, `direction`, `angular_error`, `group_samples`, `observations`, `predict`, `load_config`, `generate_rows`, `aggregate`, `package_run`, `main` | Strict recorded data/generator schema, injected delay+jitter+noise+dropout, causal hold/velocity, numeric angular results; study `FB-GAZE-01` |
| **C-003** | `benchmark_spec/profiles/fb-gaze-01.json` | 90 Hz, 90°×90° virtual FOV, 240 frames, 4 sessions each fixation/pursuit/jump, 10 named conditions, 2 predictors, 5° miss threshold, quality gate | Versioned procedural profile, *not HMD optical calibration* |
| **C-004** | `native/vulkan_compute/main.cpp` | `Settings`, `Gaze`, `Push`, `parse`, `read_trace`, shader/data helpers, `Metric`, `VulkanContext`, `main` | C++17 native Vulkan dispatch, resource setup, descriptor/push constants, fences, timestamp queries, compute readback, reference comparison, manifests, sparse or every-N capture; **not rasterizer VRS** |
| **C-005** | `shaders/foveation.comp` | GLSL 450 `main` reads source pixels and shares a sample per spatial rate block by gaze and coarse tile distance | All image pixels still dispatch compute invocations; sample fraction is theoretical proxy |
| **C-006** | `native/vulkan_compute/CMakeLists.txt` | Vulkan SDK/glslang discovery, GLSL→SPIR-V compilation and `fb_vk_compute` target | Compiled on AMD64/ARM64 CI and local UTM ARM64; no `glslc` dependency necessary |
| **C-007** | `foveabench/phase2.py` | `valid_uv`, `make_trace`, `export_phase1`, `analyze`, `run_native`, `cli` | Canonical CSV trace translation, native CMake invocation, summary + manifest, `--capture-every` native capture option; no direct ILLIXR plugin |
| **C-008** | `foveabench/phase3.py` | `read_data`, `splits_for`, `summary`, `uncertainty`, `run`, `cli` | Synthetic identity-exclusive train/validation/test, training-only offline policy choice and paired synthetic-session uncertainty, not RL |
| **C-009** | `foveabench/learn.py` | `load_pairs`, `split_subjects`, `net`, `angles`, `metrics`, `train`, `main` | 9-feature causal input; NumPy 9→24→1 tanh/sigmoid gate; Adam backprop; best-validation checkpoint, model.npz/history/test outputs; supervised, not human-trained |
| **C-010** | `foveabench/learn_bridge.py` | `prepare`, `render`, `analyze` | Checks held-out matched times+ground truth, exports hold/velocity/learned Phase 2 traces, nine Vulkan jobs, paired weighted MSE + frame regression report; existing test identities reused for exploratory analysis |
| **C-011** | `foveabench/learn_transfer.py` | `checkpoint`, `inspection`, `evaluate`, `main` | Loads frozen checkpoint with shape/schema/hash checks, blend-weight diagnostics, rejects previously seen synthetic IDs, prints transfer summaries; source still procedural |
| **C-012** | `foveabench/showcase.py` | `ppm_to_png`, `png_chunk`, `demo_trace`, `_read_metrics`, `generate_viewer`, `run`, `main` | Native capture→PNG conversion, standalone HTML playback/slider/scene/policy controls, gaze crosshairs and visual chart; browser plays already recorded frames, no live render thread |
| **C-013** | `foveabench/paper_validation.py` | `read_register`, `midranks`, `spearman`, `preference_agreement`, `compare`, `main` | Verifies user-declared provenance fields, aggregates supplied *human* ratings by stimulus, Spearman and non-tied preference agreement, participant-cluster bootstrap. **No real ratings supplied to this study yet** |
| **C-014** | `foveabench/__init__.py` | Package identity and version | Import/package boundary only |
| **C-015** | `pyproject.toml` | Editable Python package requires NumPy and `tqdm`; `foveabench` CLI entry | Dependency declaration, not an independent model version lock |
| **C-016** | `scripts/research_archive.py` | `inventory`, `archive`, `verify`, source definitions and SHA-256 hashing | New audit tool; produces reproducible local code index and experiment evidence fingerprints, explicitly not validation certificate |

## Execution paths and output contracts

1. **Reference smoke:** `python -m foveabench --help` → `C-001` → static procedural trace and two image patterns → PPM/CSV/SVG/manifests. Distinct from GPU code.
2. **Causal study:** `python -m foveabench.phase1 run --output DIR --seed N` → `C-002` loads profile `C-003` → observation generator respects delivery times and missing samples → hold+velocity prediction for each frame/condition → `DIR/frames.csv`, `summary.csv`, `report.md`, `manifest.json` and per-trace artifacts.
3. **Native rendering:** `python -m foveabench.phase2 run --trace TRACE --output DIR` → `C-007` validates CSV and builds CMake → `C-004` opens Vulkan and dispatches `C-005` → `DIR/frames.csv`, `summary.csv`, `manifest.json`, `frames/*.ppm`, `report.md`.
4. **Concurrent campaign:** `scripts/run_three_tracks.sh DIR` starts `C-002` and `C-007` concurrently; Phase 3 `C-008` reads the completed phase1 frame table. They are *not* time-synchronized per-frame.
5. **Train neural:** `python -m foveabench.learn train --phase1-frames INPUT --output DIR` → `C-009` pairs predictions, trains using supervised ground truth labels, serializes `model.npz`, `history.csv`, `splits.csv`, `test_metrics.csv`, `test_predictions.csv`.
6. **Learned-to-Vulkan:** `python -m foveabench.learn_bridge prepare` → nine CSVs paired by gaze timestamp; then `.render` → nine native executions and `comparison.csv`, `paired_frame_errors.csv`, `report.md`. No accuracy guarantee if the model is overfit.
7. **Frozen transfer:** `python -m foveabench.learn_transfer evaluate --ml-output ... --phase1-frames ... --output DIR` → `C-011` loads trained model **without any gradient updates**, excludes existing IDs and writes a new comparison. Identifiers are synthetic, not biological participants.
8. **Visual capture:** `bash scripts/run_visual_all.sh` uses the saved learned pursuit trace when present, else procedural demo → native `C-004` with `--capture-every 1` → `C-012` converts actual PPM frames to PNG → offline `viewer/index.html`, JS playback controls and SHA manifest.
9. **Paper/human utility:** `python -m foveabench.paper_validation registry` prints proposed studies; `compare-human` requires supplied and provenance-checked human ratings; no automatic source download or fabricated measurements.
10. **Archive/document:** `python scripts/research_archive.py inventory|archive|verify` records code symbols or hashes local outputs; neither changes benchmark behavior nor uploads private data.

## Configurations, specifications and source registries (all tracked)

- `benchmark_spec/datasets/FORMAT.md`: coordinate/time/participant/consent contract for recorded gaze.
- `benchmark_spec/datasets/registry.json`: 22 **catalog** entries: 2 procedurally available + 20 external not downloaded/registration-gated; classification by input utility only.
- `benchmark_spec/papers/reproduction_registry.json`: five paper/dataset reproduction targets, all recorded as pending/unverified.
- `benchmark_spec/profiles/fb-gaze-01.json`: default reproducible trial matrix and declared quality gates.
- `LICENSE`: repository's existing license; **not** evidence that external datasets are redistributable.
- `.gitignore`: excludes results, venv, build and transient/large files from tracked code.

## Test catalog — every tracked test file

| Test file | Coverage purpose | Critical gap |
|---|---|---|
| `tests/test_core.py` | Reference scenes, synthetic switch, gaze latency, projection, sample proxy and full-res identity | No physical GPU or human gaze |
| `tests/test_phase1.py` | Causal delivery/no-lookahead, out-of-range timestamp and coordinate rejection, manifest rights checks, deterministic experiment | No empirical tracker data |
| `tests/test_phase2.py` | Phase1→Phase2 export and missing-prediction fallback, trace no-overwrite, percentile, reports not inventing timing | C++ hardware VRS not tested |
| `tests/test_phase3.py` | Split exclusivity, train-only optimization insensitive to modified held-out labels, duplicate and output guards | Synthetic identity count small |
| `tests/test_learn_bridge.py` | Matched exported renderer inputs, error on nonexistent scenario, provenance checks | Native execution tested separately in CI |
| `tests/test_learn_transfer.py` | Checkpoint/schema load and reject no unseen synthetic IDs | No real subject splits |
| `tests/test_paper_validation.py` | Human-score utility's math/provenance/false-claim guard on fabricated **test fixture** ratings | Fixtures do not count as real human rating evidence |
| `tests/test_showcase.py` | PNG CRC conversion, standalone image contract, native-input consistency | GUI browser experience and real desktop need user playback |
| `tests/test_research_archive.py` | New SHA archive roundtrip and tamper detection, code AST index, protection from recursive/empty archive | GitHub runner only unless executed under user VM |

## Workflow catalog — every CI file

| Workflow | What its result actually establishes |
|---|---|
| `.github/workflows/reference.yml` | Python reference model integrity only |
| `.github/workflows/phase1.yml` | Phase1 procedural study, contract tests, uploaded synthetic artifacts |
| `.github/workflows/phase2.yml` | Vulkan build/execution with Mesa software CPU-Vulkan on AMD64 and ARM64, concurrent studies |
| `.github/workflows/phase3.yml` | Synthetic held-out policy study and chained three-track suite |
| `.github/workflows/learn.yml` | Synthetic neural training, checkpoint validation, nine-run learned-to-Vulkan experiment and frozen synthetic transfer |
| `.github/workflows/visual.yml` | Native framebuffer capture and PNG/browser-viewer generation on both CI architectures |
| `.github/workflows/research-record.yml` | New record schema/code index/archiving utility tests; no real science implied |

## Shell scripts — all tracked scripts

- `scripts/diagnose_ubuntu.sh`: print Ubuntu/Vulkan/software/tool environment diagnostics.
- `scripts/run_dual_tracks.sh`: run gaze study and native rendering concurrently with isolated log/exit bookkeeping.
- `scripts/run_three_tracks.sh`: run Phase 1/2 simultaneously and Phase 3 after Phase 1; no frame synchronization.
- `scripts/run_visual_all.sh`: inspect model, paper register, native capture and browser playback, with one command.
- `scripts/research_archive.py`: audit code and fingerprint results; new.

## Existing research documents — preservation index

`README.md`, `docs/EXPERIMENTAL_CONTRACT.md`, `docs/LITERATURE_AND_BENCHMARKS.md`, `docs/ML_RENDER_COMPARISON.md`, `docs/ML_TRAINING.md`, `docs/ML_TRANSFER_VALIDATION.md`, `docs/PAPER_REPLICATION_AND_VALIDITY.md`, `docs/PHASE1_EXECUTION.md`, `docs/PHASE2_VULKAN.md`, `docs/PHASE3_CAMPAIGNS.md`, `docs/PHASES_AND_RESEARCH.md`, `docs/RESEARCH_SOURCES_PHASE1.md`, `docs/STATUS.md`, `docs/UTM_UBUNTU.md`, `docs/VISUAL_BENCHMARK.md` remain historical design/execution sources. Newly consolidated records in `research/` link to them without deleting or silently reconciling unsupported source claims.

## Not implemented in these source files

No actual Vulkan `VK_KHR_fragment_shading_rate` raster attachment or invocation-counter experiment; no immersive headset compositor; no per-eye calibration; no direct approved ILLIXR plugin; no real dataset importer run; no human survey or new participant study; no PPO/SAC/RL controller; no native energy/power collection; no actual 3D scene renderer. Proposed modules in roadmap **must not be counted as implemented source**.
