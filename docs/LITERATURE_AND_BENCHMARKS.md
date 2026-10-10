# Literature and benchmark provenance — initial design audit (2026-10-10)

This is a research-practice matrix, not a claim to have reproduced these publications. Every item below is linked so experiments can be matched to evidence.

## XR/foveated rendering

1. **Wang, Shi & Liu, _Foveated rendering: a state-of-the-art survey_ (Computational Visual Media, 2023)**. https://doi.org/10.1007/s41095-022-0306-4 — organizes perceptual models, rendering approaches and integration. **Implication:** separate model/renderer/perception claims and use true angular eccentricity, not arbitrary screen-space rings.
2. **Singh et al., _Power, Performance, and Image Quality Tradeoffs in Foveated Rendering_ (IEEE VR 2023)**. https://ieeevr.org/2023/program/papers/ — compares full, fixed, tracked approaches including eye-tracker cost and power, not FPS alone. **Implication:** our eventual real-GPU matrix must track end-to-end cost, energy and image quality; v0.1's sample proxy is insufficient.
3. **Liu et al., _FovealNet_ (IEEE TVCG 2025)**. https://doi.org/10.1109/TVCG.2025.3549577 — explicitly discusses gaze-tracking error tails, region sizes and performance/perceptual tradeoffs. **Implication:** evaluate gaze error distribution tails, tracking errors and latency/region interactions instead of only mean errors.
4. **Jiménez Navarro et al., _Dynamic Visual Dominance in Stereoscopic Foveation_ (SIGGRAPH 2026)**. https://dynamicvisualdominance.mpi-inf.mpg.de/ — stereoscopic visual dominance matters. **Implication:** monocular synthetic initial model must not be generalized to binocular human perception; include per-eye analysis before perceptual claims.
5. **GazeBaseVR dataset (2023)**. https://pmc.ncbi.nlm.nih.gov/articles/PMC10060927/ — longitudinal binocular gaze with signal quality methods and latency concerns. **Implication:** consider carefully for authorized trace validation, including provenance, sampling rate, uncertainty, and missing values; do not silently import user records.
6. **2026 ETRA gaze prediction/error-tail study**. https://doi.org/10.1145/3797246.3803043 — evaluates gaze forecast errors across oculomotor event types and P50/P95. **Implication:** stratify by saccades, pursuit, fixation and report tail errors rather than averages alone.
7. **Vulkan fragment-shading-rate spec**. https://docs.vulkan.org/refpages/latest/refpages/source/VK_KHR_fragment_shading_rate.html — actual supported shading modes/combiners define hardware behavior. **Implication:** v0.1 block sharing is an intentionally crude analytic proxy; later validate against device properties and GPU timestamps.
8. **Vulkan fragment-density-map sample**. https://docs.vulkan.org/samples/latest/samples/extensions/fragment_density_map/README.html — a distinct feature path with feature queries. **Implication:** do not casually conflate FDM, VRS and image-space downsampling.

## Actual benchmark suite requirements inferred from the above literature

**Workloads:** recorded+synthetic, fixations/pursuit/saccades, noise/dropouts, multiple scenes, motion, contrast & spatial-frequency ramps, binocular gaze, calibrated FOV; **baselines:** full, fixed, tracked, delayed, VRS, alternative foveal radius; **outcomes:** paired quality/error versus correctly instrumented GPU time, frame pacing and energy, actual tracking overhead; **reproducibility:** versions, driver/device, exact input hashes, config, run order, warmup, repetitions, uncertainty and ablations.

No single study in the above proves a universal standard 'benchmark for all foveated rendering'. Our eventual contribution will need to define, justify and validate its own workload suite.

## FPGA/Xilinx (separate, currently OUT OF SCOPE)

If “FPGA bench / Xilinx” was intentional, a genuine AMD/Xilinx FPGA evaluation is a **different** project requiring an HDL/HLS design, Vivado-compatible host, a named target part, timing constraints, synthesis/implementation and possibly physical board instrumentation. CPU image-model sample proxies are not FPGA metrics.

- **AMD/Xilinx FPL26 optimization contest actual benchmark suite**: https://xilinx.github.io/fpl26_optimization_contest/benchmarks.html — names 19 design checkpoints and a target xcvu3p device with explicit clock-domain timing methodology. Relevant metrics include LUT, FF, DSP, BRAM use, Fmax and timing validity.
- **Vivado UG892, 2026.1**: https://docs.amd.com/r/en-US/ug892-vivado-design-flows-overview/Running-Reports-DRC-Power-Utilization-Analysis — use `report_utilization`, `report_power`, design analysis and DRC checks.
- **Vivado UG906, 2026.1**: https://docs.amd.com/r/en-US/ug906-vivado-design-analysis/Report-Power — power is an estimate requiring workload activity and design implementation, not an instantaneous code statistic.

FPGA research methodology additionally needs: part/speed grade, RTL/HLS revision, constraint clock and WNS/hold checks, routed timing, frequency, throughput, data width, interface bandwidth, BRAM/LUT/FF/DSP, watts with stated method, J/op, algorithm correctness, resource-efficiency Pareto plots, repeat builds/seeds, version/pblock constraints and test vectors. **Nothing from this FPGA column is measured by FoveaBench v0.1.**
