# Phase 2 implementation: native Vulkan compute and ILLIXR interchange

## What runs now

**FB-RENDER-01/2.0** builds a native C++ Vulkan compute pipeline using **SPIR-V compiled from GLSL**. It runs on a physical Vulkan GPU or, where available, a Mesa Lavapipe software device inside Ubuntu UTM ARM64. It generates two diagnostic scenes, dispatches four policies (full/fixed/tracked/lag40), reads back actual Vulkan buffer outputs, and computes PSNR-adjacent quality diagnostics against deterministic reference RGB images.

The timing uses Vulkan timestamp queries (`vkCmdWriteTimestamp` at TOP_OF_PIPE/BOTTOM_OF_PIPE) around the compute dispatch. It checks the compute queue's `timestampValidBits`, the device property `timestampComputeAndGraphics`, and `timestampPeriod`. When unsupported, the timestamp CSV field is blank; timing is never fabricated. Each dispatch is completed with a fence before host inspection. **This measures a compute kernel, not GPU rasterized fragment shading or a complete XR frame.**

The Vulkan implementation discovers whether the device advertises `VK_KHR_fragment_shading_rate` and whether pipeline, primitive or attachment features exist. It **does not enable or use VRS** in this version. Actual foveated VRS requires a Vulkan graphics pipeline and, for spatial rate control, a hardware-supported shading-rate attachment (and the correct render pass or dynamic-rendering integration). Khronos documents those capabilities independently. A CPU software driver, including Lavapipe, is marked `software-vulkan-functional` and automatically excluded from hardware benchmark rankings.

### Build and run on Ubuntu 24.04 ARM64 under UTM

Install generic prerequisites (inside the Ubuntu guest, not on macOS):

```bash
sudo apt update
sudo apt install -y git build-essential clang cmake ninja-build libvulkan-dev vulkan-tools mesa-vulkan-drivers glslang-tools python3
uname -m
vulkaninfo --summary
cd ~/research/Foveabench
# If git repo already exists, inspect status before updating.
git status --short
git pull --ff-only origin main
python3 -m foveabench.phase2 make-trace --output results/trace-001.csv --frames 48
python3 -m foveabench.phase2 run --trace results/trace-001.csv --output results/vulkan-001 --frames 48
cat results/vulkan-001/report.md
cat results/vulkan-001/manifest.json
```

`CMakeLists.txt` invokes `glslangValidator` to compile `shaders/foveation.comp` into binary SPIR-V. Vulkan is used without any graphical window or headset; UTM graphics acceleration can remain off. For physical GPU-only runs:

```bash
python3 -m foveabench.phase2 run --trace results/trace-001.csv --output results/native-gpu-001 --frames 48 --require-hardware
```

This **fails** if the selected Vulkan device is CPU/software; it does not relabel Lavapipe as a GPU.

### Run Phases 1 and 2 concurrently

```bash
bash scripts/run_dual_tracks.sh
```

The script creates a timestamped results directory, builds the independent renderer, launches the complete 57,600-evaluation gaze-prediction study **at the same time** as the 256-dispatch rendering study, writes separate logs and artifacts, and produces a joint ledger. If either phase fails, the exit status is nonzero. The two runs do not depend on each other's output and use independent result directories.

### Feed real Phase 1 predictor output to Phase 2

After Phase 1 has produced `results/my-gaze-study/frames.csv`, create a renderer-ready input from a specific predictor/condition/trace (use IDs in the Phase 1 file):

```bash
python3 -m foveabench.phase2 export-phase1 \
  --input results/my-gaze-study/frames.csv \
  --condition latency-60 --predictor hold --trace-id synthetic-fixation-00 \
  --fallback center --output results/exported-trace-001.csv
python3 -m foveabench.phase2 run \
  --trace results/exported-trace-001.csv --output results/linked-001 --frames 120
```

`--fallback center` is explicit: if the predictor returned no value on a frame, a center-of-screen gaze is recorded. `--fallback hold` uses the last valid prediction, and fails if the initial sample is unavailable. The default `reject` fails on any missing prediction. The canonical trace preserves `timestamp_ns,truth_x,truth_y,used_x,used_y,valid` and rejects nonmonotonic timestamps/nonfinite or out-of-bounds normalized UVs. It currently requires valid gaze on each Vulkan input frame; no silent imputation.

### Provenance, instrumentation and limitations

Each result contains: `frames.csv` (per-frame per-policy timestamp-reported compute duration, image error, sample-count *proxy*, mismatching pixels), `summary.csv`, `manifest.json`, `STATUS.md`, `report.md`, a preserved `trace.csv` and PPM screenshots. The frame results are created by the actual native Vulkan program, **not** a Python timing loop. The analysis process records `trace_sha256` and a result class. Raw result files must be retained when rerunning the analysis.

The generated image is an image-space pixel-block sampling model. All output pixels run a compute thread, so `sample_fraction_proxy` is **not** a GPU invocation count and there is **no performance benefit implied** by a reduced proxy. GPU queries measure command execution, not host submit+queue wait, present, eye-tracking inference, or motion-to-photon latency. Benchmarks also need clock stabilization, warmup, device power data, multiple measured runs and cross-device repeatability before hardware rankings.

## ILLIXR relationship (separate from the official starter tasks)

ILLIXR's own runtime already has a modular plugin and Switchboard dataflow. The official starter-task page explicitly prohibits agentic AI completing starter tasks or feeding ILLIXR source to LLMs. We did **not** read/modify ILLIXR code or implement its starter tasks here. Integration is currently through an **external versioned trace interchange**. Once starter tasks are completed manually and supervisor consent/scope is clarified, implement an independent ILLIXR adapter using its public plugin interface to publish gaze samples, align frame clocks and consume render outputs. This will require testing against the running ILLIXR version and cannot be asserted complete based on the interchange alone.

Suggested independent adapter contract:

- `trace_source`: canonical timestamped gaze with acquisition/delivery validity and coordinate convention metadata.
- `renderer`: swappable ILLIXR/standalone Vulkan backend with feature and environment manifest.
- `capture`: synchronized frame id, app time, GPU time, content hash, motion prediction and presentation timestamps.
- `comparison`: the same trace/scenes/parameters across algorithms, with explicit adapters preserving timing semantics.

See https://illixr.org/starter_tasks and https://illixr.github.io/ILLIXR/latest/working_with/writing_your_plugin/ for official constraints and supported extension points.

## Remaining Phase 2 acceptance items (NOT COMPLETED)

1. True **rasterization** backend with hardware VRS attachment and per-eye render targets.
2. ILLIXR live plugin/runner with version-stable Switchboard topics, after starter-task rules are satisfied.
3. Physical-GPU hardware validation and repeatability (CI runners can expose Lavapipe only).
4. Resolved GPU timestamps vs full-frame present-to-display timing, synchronization with gaze/head pose.
5. Representative licensed XR scenes and tested quality metrics under real binocular gaze.

No study using participants has been run or approved by this code. Software Vulkan execution is a genuine Vulkan path, but not valid evidence of physical GPU efficiency.
