# Phase 1 verified sources and design mapping (2026-10-10)

The references are **inputs to engineering methodology**, not reproduction
claims. All numeric sweeps are provisional, chosen to expose failure modes;
none are falsely represented as mandated values from these publications.

| Reference | Source | Implication for Phase 1 |
|---|---|---|
| ILLIXR Consortium | https://illixr.org/ | Existing XR runtime/testbed and reference benchmarking; FoveaBench is independent and must add validated comparative rules |
| Dunn et al., Minimal reporting guideline for research involving eye tracking, Behavior Research Methods (2024) | https://pmc.ncbi.nlm.nih.gov/articles/PMC11225961/ | Strict metadata for model, firmware, calibration, sampling, latency, data loss, processing and uncertainty |
| Lohr et al., GazeBaseVR, Scientific Data (2023) | https://www.nature.com/articles/s41597-023-02075-5 | Strong candidate licensed/consented empirical dataset for later integration; 250Hz, 5,020 recordings, 407 participants |
| Khronos OpenXR `XrEyeGazeSampleTimeEXT` | https://registry.khronos.org/OpenXR/specs/1.1/man/html/XrEyeGazeSampleTimeEXT.html | Sample time need not equal requested/rendering time; keep event-time and delivery-time semantics separate |
| Khronos Vulkan calibrated timestamps | https://docs.vulkan.org/features/latest/features/proposals/VK_EXT_calibrated_timestamps.html | Different timestamp domains need explicit calibration; future GPU measurements must not conflate time sources |
| MLCommons Inference rules | https://github.com/mlcommons/inference_policies/blob/master/inference_rules.adoc | Separate load generation/quality gating, immutable configs, evidence, reproducibility and audit |
| MLPerf LoadGen | https://github.com/mlcommons/inference/blob/master/loadgen/README.md | Scheduling/data/metrics separation and reusable benchmark harness design |
| MLPerf power methodology | https://github.com/mlcommons/inference_policies/blob/master/power_measurement.adoc | Power and performance from same actual workload run, not cherry-picked across runs |

## Evidence gaps / papers not yet reproduced

- Did **not** collect new human observations or verify participant consent.
- Did **not** run ILLIXR native Vulkan integration or an XR headset.
- Did **not** benchmark XRBench, FovVideoVDP or other tools in this branch.
- Did **not** fit a learned eye-movement generator to real people.
- Did **not** measure GPU time, GPU power or actual photons-to-eye latency.

This engineering phase creates infrastructure and a falsifiable baseline. The
scientific novelty question remains open until comparison with existing systems
and cross-condition empirical evidence is complete.
