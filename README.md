# FoveaBench

**Version 0.1: reproducible gaze replay and a CPU image-space foveation reference model.** This is an independent research harness for the Virginia Tech / XR research direction. It is **not** an ILLIXR starter-task solution, a physical XR runtime, an FPGA testbench, or a measured Vulkan/GPU benchmark.

## Phase 2: FB-RENDER-01 — native Vulkan and concurrent execution (October 10, 2026)

A **real headless Vulkan compute workload** (C++17 / SPIR-V) now consumes a versioned gaze trace, renders four image-space foveation policies on two stress scenes, checks full-reference byte equality, and records **Vulkan device timestamps** where the compute queue supports them. It exports frames, numerical quality proxies, hardware/driver capability manifests, and uncertainty-relevant timing distributions. It probes `VK_KHR_fragment_shading_rate` support but **does not implement hardware VRS or integrate a live ILLIXR renderer yet**. Software Vulkan (e.g., Mesa Lavapipe) is explicitly excluded from hardware performance rankings.

Run in Ubuntu on UTM (or physical Linux; needs Vulkan/GLSL tools):

```bash
sudo apt update
sudo apt install -y cmake clang ninja-build libvulkan-dev mesa-vulkan-drivers vulkan-tools glslang-tools
python3 -m foveabench.phase2 make-trace --output results/vk-trace.csv --frames 32
python3 -m foveabench.phase2 run --trace results/vk-trace.csv --output results/vk-run --frames 32
cat results/vk-run/report.md

# Both Phase 1 and Phase 2 actually execute concurrently (separate evidence folders):
bash scripts/run_dual_tracks.sh
```

See [exact Phase 2 setup and scientific limitations](docs/PHASE2_VULKAN.md) and [verified CI workflows](https://github.com/swayam8624/Foveabench/actions). The CI workflow tests Vulkan software execution on **Ubuntu 24.04 AMD64 and ARM64**; this is not a validation of an actual UTM desktop environment.

## Phase 1: FB-GAZE-01 (October 2026)

**Autonomous gaze prediction and replay study:** 12 procedural trace streams × 10 sensor conditions × 2 causal predictors × 240 frames = **57,600 frame/predictor/condition evaluations**. No external data, head-mounted display, ILLIXR codebase or Vulkan device needed for this first *scientific scaffold*. The results are **synthetic and geometric only**: not actual GPU measurements, validated human perception or human participants.

```bash
# From the repository root, Python 3.10+ (no extra dependencies for Phase 1)
python3 -m foveabench.phase1 run --output results/phase1-first-study --seed 20261010
# Inspect results/phase1-first-study/{report.md,summary.csv,frames.csv,per_trace.csv,paired.csv,manifest.json,STATUS.md}
```

Real datasets can be passed only after normalization and with an explicit consent/license/eye-tracker metadata manifest: see [dataset contract](benchmark_spec/datasets/FORMAT.md). See [five-phase research roadmap](docs/PHASES_AND_RESEARCH.md), [full run instructions](docs/PHASE1_EXECUTION.md), and [reference sources](docs/RESEARCH_SOURCES_PHASE1.md). Each run reports geometric quality gates (explicit provisional thresholds), missing predictions, tail angular errors, paired outcomes, and provenance/limitations. This is distinct from the earlier pixel-block CPU demonstration below.

## Run immediately (Ubuntu 24.04 ARM64 in UTM, or macOS/Linux)

Requires Python 3.10+ with NumPy. In Ubuntu:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip
git clone https://github.com/swayam8624/Foveabench.git
cd Foveabench
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
python -m foveabench run --preset smoke --output results/first-run
```

After this, inspect `results/first-run/STATUS.md`, `manifest.json`, `summary.csv`, `frames.csv`, and `overview.svg`. To see RGB PPM frames open them in a compatible image viewer or convert to PNG using ImageMagick. The `--output` directory must not already exist; use a different path for your next run. To run the extended CPU reference exercise:

```bash
python -m foveabench run --preset study --output results/study-001
```

**These commands operate only on FoveaBench; they do not perform ILLIXR starter tasks.**

## What the experiment actually does

- Synthesizes **fixation**, **smooth pursuit-like** and **jump/saccade-like** gaze inputs at a fixed timestamp frequency (synthetic; not physiological recordings).
- Synthesizes **chirp** and **hard-edge** visual stimuli designed to stress reduced pixel sampling.
- Compares `full`, `fixed`, `gaze_0ms`, `gaze_40ms`, and `gaze_80ms`.
- Uses a rectilinear 90°×90° virtual camera and angular ray separation to determine 5° center / 15° middle / peripheral zones.
- Applies an 8×8-tile **sample-sharing approximation** of 1×1, 2×2, or 4×4 pixel shading, recording a *sample-count proxy*.
- Computes unweighted RGB MSE, PSNR, a clearly uncalibrated Gaussian gaze-weighted MSE/PSNR, and 5° foveal MSE with errors anchored to **true** gaze.
- Records per-frame and condition-aggregate CSV files, two example frames per condition, a simple SVG result plot, SHA-256 hashes for input trace files, a machine-readable manifest and a status ledger.

## First verified CI result

An initial Ubuntu-hosted GitHub Actions smoke run completed **360 modeled frames across 30 condition combinations**, and **5 numerical unit tests passed**. The artifacts are attached to https://github.com/swayam8624/Foveabench/actions/runs/38041402849 . This is not an ARM64-UTM validation and not a real GPU benchmark. Subsequent revisions include a short-trace saccade-switch regression test.

## Interpreting the output responsibly

The important first graph compares **modeled sample fraction** against **gaze-weighted MSE**. Neither quantity is a measured GPU speedup or a clinically/perceptually validated metric. The `cpu_model_ms` values are diagnostic local wall times subject to OS scheduling, VM overhead, software version, and thermal load; **never use them as evidence of GPU performance**. Foveated rendering also has geometry, bandwidth, tracking, interpolation, display, temporal artifact and latency costs that this model omits.

A perfect image has MSE=0. Its PSNR is mathematically +∞, represented as a blank CSV value / null JSON, not a finite fake number. A delayed gaze policy uses timestamp-based zero-order hold. Startup delay holds the first trace sample, and therefore the first frames may be artificially favorable.

## Research gates

**Gate 0: reference experiment** — this repository. **Gate 1:** measured software-vs-renderer image correspondence with a controlled GPU backend. **Gate 2:** Vulkan instrumentation with GPU timestamps, feature reporting, frame pacing and synchronized data. **Gate 3:** ILLIXR adapter implemented through an approved collaboration workflow, independently of the official starter tasks. **Gate 4:** consented/public human-gaze traces; live-versus-replay validation; non-synthetic scenes. **Gate 5:** cross-machine replication, power where supported, statistics, perceptual evaluation, paper.

See [experimental contract](docs/EXPERIMENTAL_CONTRACT.md), [literature/method choices](docs/LITERATURE_AND_BENCHMARKS.md), [Ubuntu instructions](docs/UTM_UBUNTU.md), and [project status](docs/STATUS.md).

## Licensing

Existing repository license applies. Any imported datasets must carry their own license, provenance and privacy information.
