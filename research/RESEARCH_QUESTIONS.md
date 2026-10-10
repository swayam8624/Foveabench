# Research hypotheses, methods, equations and decision criteria

Each question must have preregistered experimental conditions, baselines and disjoint validation/evaluation. These are designs, not observed results.

## RQ1 — Are replay rankings predictive of live XR outcomes? (`N-001`)

For a pair of algorithms `A,B` under condition `c` define offline and live paired differences, `Δ_off = S_off(A,c) - S_off(B,c)` and `Δ_live = S_live(A,c)-S_live(B,c)`; align the direction of **better** before evaluation. A ranking reversal indicator is `R(A,B,c) = 1[sign(Δ_off) != sign(Δ_live)]` *only when neither difference is within a declared practical-equivalence margin*. Report indeterminate ties rather than forcing spurious wins. Across multiple candidate methods, use Kendall/Spearman ranking measures by matched experimental block, but also report absolute error, systematic bias, limits of agreement, tail errors, rank reversal rate and deadline misses. **Calibration and testing must not share participants.**

Experiment: 3+ distinct predictors/foveation implementations, >=2 workloads and >=2 real devices when feasible. Lock time alignment and predictors, randomize policy order, capture gaze acquisition/arrival/render submit/display timestamps separately, and record per-eye optics calibration. Use held-out participant and device grouping, session clustering and full hardware provenance. An independent outcome can be a *negative* result: offline scores do not robustly predict a live rank.

## RQ2 — Can an offline benchmark know when it is unreliable? (`N-002`)

Define `q(c) ≈ Pr[R=1 | x(c)]`, where `x(c)` contains only features observable at inference time: measured calibration quality, timestamp jitter/latency, gaze confidence, workload/frame budget, supported hardware capabilities. Model and calibrate using development folds, then evaluate on sealed participant/device folds. A confidence score must be evaluated with reliability plots, Brier score, log loss, selective-risk vs coverage, bootstrap at the participant/session level and appropriate cross-domain splits. Include trivial predictors (always trustworthy; unconditional training prevalence; simple worst-case bound); don't call `q` a probability unless calibrated.

## RQ3 — Can valid adversarial workload search expose failures efficiently? (`N-003`)

Optimization objective may seek *supported* rank reversals or quality-gate violations under bounded perturbations. Candidate factors: latency, burst dropout, offset/noise, real motion class and scene bandwidth. Reject perturbations inconsistent with measurement-based sensor physics or dataset timebases. Report held-out transfer success *outside* the simulator, search cost, false discoveries and repeated-seed stability. CMA-ES/Bayesian search/bandits are baseline optimizers, not novel algorithms by default.

## RQ4 — Does a new temporal perceptual measure predict actual people? (`N-005`)

Use licensed stimuli with per-participant MOS/JOD/pair preferences; reproduce authors' calibration/test split first. Compare fixed image-MSE, gaze-weighted MSE, PSNR/SSIM as appropriate, FovVideoVDP, and proposed temporal measures. No human-score tuning on held-out stimuli or observers. Report direction/orientation (higher better), within-display and cross-display correlations, non-tied preference agreement, correlations with confidence intervals *over participants*, and failure maps. Current `paper_validation.py` is an analysis skeleton, not this completed study.

## RQ5 — Does adaptive optimization improve quality-constrained rendering? (`N-006`)

Observed state `s_t`: causal gaze history, tracker confidence, queue/deadline/power state. Actions: foveal radius, shading rate, reconstruction quality, prediction horizon subject to supported device limits. Define constrained objective: minimize **actual measured** frame cost and power subject to quality, missed-frame and perceptual thresholds. Use a feasible-set/violation-first benchmark, not a single arbitrarily weighted score. Compare fixed best validation policy, conservative hold, velocity, hand-built switcher, Bayesian parameter search, contextual bandit and (only when justified) sequential RL. Include controller inference and training costs. Must be assessed with a frozen policy on new real scenes, participants and hardware.

## Current controlled limitation

The present neural blend was trained to reduce synthetic normalized-UV mean squared error. The model did **not** receive frame images or measured rendering quality gradients; rendering was a later diagnostic. Consequently, the neural gate can improve smooth pursuit while losing overall angular accuracy and fail to exploit all scene-specific image benefits. Simply adding more epochs without changing the data/objective is not a novel algorithm.
