# Experimental contract (v0.1)

## Claim classes and admissible evidence

| Claim | Current admissible evidence | Not justified |
| --- | --- | --- |
| Deterministic replay input | Timestamped traces, fixed generators, SHA-256 | Real-time delivery jitter is zero |
| Frame output correctness | Full-resolution exact-pixel invariant, tests | Real renderer equivalence |
| Image-space artifacts | Paired synthetic stimuli and pixel MSE | Human perceptual invisibility |
| Reduced sample demand | Explicit counted reference-model sample sites | Vulkan fragment invocations / actual GPU cost |
| Gaze-latency response | Timestamp-based delayed selection | Measured end-to-end headset latency |
| Throughput/power | NONE in v0.1 | FPS gains, energy savings, device performance |
| Human-independence | Trace replay is headless | Benchmark reproduces human results |

## Stimulus and policy controls

Keep the full-resolution reference constant for each (scene, trace, frame); compare all policies on identical underlying pixels and gaze timestamps. Use the true gaze sample for error weighting even when policy gaze is fixed or delayed. Report frequency, resolution, FOV, coordinates, reference/rate zones, and sample count. The software model shares a single source pixel across rate-sized blocks. It does **not** reproduce actual hardware interpolation, tiling rules, early-Z, texture sampling, rasterization or shader divergence.

## What makes the next experiment paper-grade

- Real HMD per-eye optical calibration, lens mapping, pixels-per-degree and monocular/binocular gaze semantics.
- Privacy-cleared eye-tracking datasets with fixation, pursuit, saccades, blinks and missing samples; subjects held out across analysis splits.
- Realistic dynamic scenes with known high-quality reference images; multi-scene/multi-condition reproducible workloads.
- Synchronized capture and replay timebase: acquisition, prediction, app, GPU submit, presentation, HMD display. Do not treat commanded delay as measured latency.
- **GPU timestamps** around meaningful render passes and frame-time P50/P95/P99 (present latency separately). CPU time must not be substituted.
- Supported shading-rate capability checks; actual invocation counters where available; explicit separate CPU, GPU, and VIO work.
- Controlled resolution, refresh rate, temperature, power profile, warmup, run order, repetitions and confidence intervals. Compare across devices only with stated differences.
- Spatial and temporal quality: PSNR/SSIM and gaze-weighted diagnostics, plus validated perceptual metrics/observer experiments where claims require perception.
- Paired within-trace algorithm comparisons, uncertainty intervals, factorial sensitivity to gaze noise and delay, ablations, and preregistered primary outcomes when feasible.
- Live/replay agreement quantified with confidence intervals; correlations alone are insufficient (also assess bias, limits of agreement and rank stability).

## Integrity and scope

Official ILLIXR starter tasks prohibit agentic AI completing them and feeding ILLIXR codebase into an LLM. This independent repository contains **no copied ILLIXR source** and no automated solution of those tasks. Get appropriate permission/clarity before implementing an ILLIXR-specific adapter. No researcher approval, human-subjects ethics clearance or headset availability is implied by this repository.

## Initial acceptance tests

Unit suite and CI require deterministic trace construction, rejection of invalid coordinates/timestamps, correct zero-order-hold delay, ray-angle sanity, full reference exact pixel match, and bounded sample fraction. The run creates a machine-readable ledger distinguishing PASS / NOT_RUN / NOT_IMPLEMENTED / OUT_OF_SCOPE. No synthetic result is promoted to empirical XR findings.
