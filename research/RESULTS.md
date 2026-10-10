# Measured, executed and reported results — experiment ledger

**Cutoff:** 2026-10-10. **Evidence grades:** `G1 = raw artifacts/CI logs verified`, `G2 = user terminal output in the present project conversation`, `G3 = secondary prior assistant summary without raw transcript in this repository`; confidence does **not** mean scientific population-level validity. Source data logged on user UTM are not copied into public Git because `results/` is intentionally ignored. Some old CI runs/Artifacts may expire; preserve original work when possible.

All quantities below are **synthetic test outcomes or software Vulkan functional measurements**; there are no real participants, physical GPU VRS measurements, powered headset tests, perceptual human outcomes or genuine paper-reproduction findings yet. “Frames”, “model outcomes”, “policy evaluations” and “dispatches” have different denominators.

## Stable result registry

| Finding | Date UTC | Workload/source | Observed result | Evidence and epistemic limit |
|---|---|---|---|---|
| **F-001** | Oct 10 | Phase 1 generated 12 synthetic traces × 10 conditions × 2 predictors × 240 frames | **57,600 frame×model evaluations** | `FB-GAZE-01`, GitHub Actions Phase 1 and user three-phase transcript (G1 + G2). Twelve *pseudonymous agents*, **not people** |
| **F-002** | Oct 10 | Phase 2 16 frames × 2 scenes × 4 policies | **128 native Vulkan compute dispatches**, `llvmpipe`, CPU software device, device query timestamps available; exact full-reference pixel mismatch count **0** | UTM terminal run `results/utm-vulkan-20261010T151919Z`, user-reported (G2); no hardware raster/VRS claim |
| **F-003** | Oct 10 | Three-track launcher on actual user's UTM Ubuntu 24.04.5 ARM64 | Phase 1 PASS, Phase 2 PASS, Phase 3 PASS, exit **0**; evidence folder **11 MB** | User run `results/three-tracks-utm-20261010T152017Z` (G2). Phase 1 and 2 concurrent but not gaze/render synchronized |
| **F-004** | Oct 10 | Phase 3 offline training-only condition selector on 12 synthetic identities; 10 conditions | Selected velocity for several lag/dropout/jitter conditions; on heldout identities it increased average penalized angle by **+0.3199° to +0.4334°** in listed conditions versus hold | User report (G2). Intervals contained zero; only 3 synthetic held-out labels, cannot imply harm in humans |
| **F-005** | Oct 10 | User's linked 48-frame pursuit latency-60 rendering, two predictors × two scenes × four policies | **768 dispatches** (384 each). Chirp weighted MSE hold **6,783.1765**, velocity **6,359.7731** (−6.24%). Edges hold **3,537.2887**, velocity **3,331.1730** (−5.83%) | User `results/linked-gaze-render-20261010T152147Z` transcript (G2). Software VDP-*un*calibrated MSE, not hardware acceleration |
| **F-006** | Oct 10 | Broader fixation/pursuit/jump synthetic render with 60 ms sensor lag | Previous report: velocity on pursuit **+8.83% / +9.30%** image-error improvement, on jumps **−2.00% / −1.91%**, fixation ~0 | Prior turn report (G3); full raw `results` directory and stdout were not uploaded here, so treat as supporting, not standalone evidence |
| **F-007** | Oct 10 | NumPy supervised neural gate (9 input features, 24 hidden neurons), synthetic identity-disjoint 3-way split | **28,475 usable frame pairs**, **325 missing pairs excluded** in arm64 CI; train **14,239** / validation **7,115** / test **7,121** frames, synthetic identities **6/3/3** | [`CI run 38064010661`](https://github.com/swayam8624/Foveabench/actions/runs/38064010661) (G1) and UTM screenshots (G2). No real human data |
| **F-008** | Oct 10 | User neural training 80 epochs max with patience 20; best validation checkpoint epoch **29**; early stopped at epoch **49** | Heldout mean gaze error: hold **3.6158°**, velocity **5.6563°**, learned **3.6538°**. P95 hold **8.4987°**, learned **8.4804°**; miss>5° hold **9.77%**, learned **10.25%** | User `results/ml-utm-20261010T153731Z` screenshots (G2) and CI analog (G1). Learned was **~1.05% worse than hold overall** despite pursuit improvement |
| **F-009** | Oct 10 | 7,121 test-frame gaze subgroup metrics | Fixation hold **0.8610°**, learned **0.8885°**; pursuit **2.7726° vs 2.6857°**; jump **7.2090° vs 7.3820°** | User screenshot (G2). Neural model improves pursuit by ~3.14%, worsens others; test motion labels used for *analysis*, not as neural features |
| **F-010** | Oct 10 | Native Vulkan paired rendering with learned checkpoint, 3 motions × 3 predictors × 234 frames × 2 scenes × 4 policies | **16,848 compute dispatches**, 9 native runs all PASS, exit 0. Image-level per-scene results in table below | User `results/learned-render-20261010T154459Z` pasted terminal log (G2). Same *already examined* synthetic heldout identities: exploratory, not an independent final test |
| **F-011** | Oct 10 | Expanded Phase 1 synthetic profile, 8 sessions per motion; 10 conditions × 2 predictors × 240 frames | **115,200 scored frame×model outcomes**, **56,962 paired usable frames**, **638 unavailable pairs excluded** | User `results/transfer-utm-20261010T155306Z` screenshots (G2). Source still same procedural generator |
| **F-012** | Oct 10 | Frozen neural checkpoint, **12 new synthetic pseudonymous IDs**, 12 earlier IDs excluded | **28,474 eligible fresh-ID pairs**, hold mean **3.6708°**, velocity **5.6665°**, learned **3.6918°**; hold miss5 **9.42%**, learned **9.61%** | User transfer report (G2). Learned overall **~0.57% worse** than hold, though pursuit benefited |
| **F-013** | Oct 10 | Frozen neural per-motion synthetic transfer | Fixation: hold **0.7731°**, learned **0.7983°**; pursuit hold **2.7025°**, learned **2.6064°**; jumps hold **7.5380°**, learned **7.6719°** | Same UTM transferred model evidence (G2). Does not generalize to human population |
| **F-014** | Oct 10 | First native visual capture CI: 12 frames × 2 scenes × 4 policies | **96 native dispatches**; **96 captured genuine images**, arm64 and amd64 llvmpipe PASS | [`CI run 38066563920`](https://github.com/swayam8624/Foveabench/actions/runs/38066563920) (G1), image artifact `fb-visual-vulkan-ubuntu-24.04-arm` |
| **F-015** | Oct 10 | Full visual showcase through `scripts/run_visual_all.sh` | Default **72 frames × 2 scenes × 4 policies = 576 dispatches** *specified*, not yet user-UTM verified by submitted log | Code/workflow config only (G1 design), label **NOT RUN ON USER VM**. 96-frame CI smoke **does not** prove this exact 72-frame local run happened |
| **F-016** | Oct 10 | Native frame image/quality correctness under software Vulkan | Full policy pixel mismatch max = **0** in reported UTM run; sample fraction lower under foveation | User manifest in F-002. Sample fraction is calculated pixel-block proxy; all workgroups still dispatch, no actual fragment invocation savings |
| **F-017** | Oct 10 | Code/test suite and paper human-rating utility | Existing tests pass CI; human-rating correlation source and paper reproduction **NOT RUN** | Repo workflows and paper register (G1 functionality only). No published human data had been ingested |

### F-010 — Complete learned versus baseline *image* table

Signed change is **reduction in gaze-weighted MSE relative to hold**; **positive means lower MSE**. One test trace per motion (234 usable frames), two diagnostic scenes, `llvmpipe` (not GPU speed). Raw source: the user's Oct 10 terminal output `results/learned-render-20261010T154459Z/report.md`.

| Motion | Scene | Hold weighted MSE | Velocity weighted MSE | Learned weighted MSE | Velocity Δ | Learned Δ |
|---|---|---:|---:|---:|---:|---:|
| fixation | chirp | 5251.928 | 5275.061 | 5254.797 | −0.44% | −0.05% |
| fixation | edges | 3083.110 | 3102.829 | 3088.009 | −0.64% | −0.16% |
| pursuit | chirp | 6260.468 | 5663.948 | 6214.189 | **+9.53%** | +0.74% |
| pursuit | edges | 3664.393 | 3310.433 | 3638.325 | **+9.66%** | +0.71% |
| jump | chirp | 6170.065 | 6291.005 | 6170.065 | −1.96% | 0.00% |
| jump | edges | 3469.468 | 3539.579 | 3469.468 | −2.02% | 0.00% |

**F-010 conclusion:** the blend avoids much of velocity's instability during synthetic jumps, but does not capture most of its pursuit benefit. Since the model trains on UV MSE rather than actual image quality and uses a coarse hand-generated distribution, this is unsurprising; the difference is an engineering hypothesis, not proof of causal mechanism.

### F-012 — Frozen new-ID transfer detail

| Movement | Frame pairs | Hold mean angular | Velocity mean angular | Learned mean angular | Hold miss>5° | Learned miss>5° |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 28,474 | 3.6708° | 5.6665° | 3.6918° | 9.42% | 9.61% |
| fixation | 9,494 | 0.7731° | 3.3302° | 0.7983° | 2.26% | 2.42% |
| jump | 9,490 | 7.5380° | 10.3771° | 7.6719° | 12.15% | 13.36% |
| pursuit | 9,490 | 2.7025° | 3.2931° | 2.6064° | 13.84% | 13.06% |

**Critical interpretation:** disjoint *synthetic IDs* on the same trajectory generator and different seeds are a limited robustness check, **not** independent biological/real-world validation. This distinction remains even when all timestamps, hashes and splits are internally correct.

## Known errors, fixes and remaining bias

- Phase 2 initial CI had a CRLF trace-header parsing mismatch. Trim carriage return; successful ARM64 and AMD64 tests thereafter (`D-004`).
- Neural model inspection once raised `Missing learned prediction audit fields`: code expected `velocity_weight`, while training saved `blend_weight`. Fixed; a separate `ResourceWarning` for an unclosed `splits.csv` was also fixed (`D-010`). These failures are retained, not erased.
- Image error (`weighted_mse`) weights full-resolution reference differences by the *true* synthetic gaze. It is **not** a validated perceived quality score, and can prefer different policies than angular error.
- Phase 1 synthetic jump is a square-wave stress signal, not an experimentally verified saccade generator. Its very large P95 reflects this artificial design; don't interpret that as a headset/participant error distribution.
- Some released scripts include output overwrite guards, but archived evidence should still be checksummed and copied independently. Native C++ and Python timing brackets do not establish end-to-end presentation delay.
- UTM has **11 GiB RAM, 8 ARM64 vCPUs, 77 GiB disk free (at recorded diagnosis)**, Mesa `llvmpipe` LLVM 20.1.2 (128-bit); `vulkaninfo` reported CPU physical device. Kernel Ubuntu 24.04.5 / 7.0.0-31-generic at the time. This is the actual VM, not the host Mac Metal GPU.

## How to upgrade an entry to a published claim

1. Locate the original raw directory for `F-###` under the user's `~/research/Foveabench/results/` or the CI artifact link.
2. Run `python scripts/research_archive.py archive --run-dir ... --output results/fingerprints-ID --description ...` and `verify` it.
3. Record checksum, exact config/version, sample/group definitions, hardware provenance, results with units, and uncertainty. Evaluate the actual scientific conclusion on valid independent data.
4. Add the resulting date/commit and artifact link to this ledger **without overwriting** the earlier preliminary evidence.
