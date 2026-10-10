# FoveaBench scientific roadmap: from a visible visual benchmark to human-grounded credibility

## Status and exact scientific distinction

Current FoveaBench:

- **Functional native Vulkan compute**, software CPU device under UTM (Mesa llvmpipe).
- **Synthetic procedural gaze** with causal hold and velocity predictors.
- An actual supervised neural blend (9-input tanh model), trained and tested on
  disjoint *synthetic agent labels*. It is **not trained on human gaze recordings**.
- Numeric gaze errors and uncalibrated gaze-weighted image MSE. No
  psychophysically calibrated perceptual preference scores.
- A browser viewer of **actual offscreen Vulkan captured image frames**.
  Playback is after rendering, not a live benchmark score.

None of those establish hardware fragment VRS, native M2 Pro GPU performance,
end-to-end headset latency, perceptual validity, ILLIXR integration, or replay
ranking equivalence with a real participant wearing an XR headset.

## Reproducible literature baselines (ordered)

The machine-readable target registry is
`benchmark_spec/papers/reproduction_registry.json`, and the inspection command is
`python -m foveabench.paper_validation registry`. All entries are labelled
`not_reproduced`, `not_ingested`, or `research_candidate_unverified`. Do not
represent listed external paper numbers as reproduced measurements.

### 1. Real VR gaze and tail-error: Melnyk, Friedman & Komogortsev (ETRA 2026)

Paper https://doi.org/10.1145/3797246.3803043 ; supplementary source and
code claimed at https://hdl.handle.net/10877/23835 .

Main tasks: get source, run the original preprocessing and event segmentation
on the original **GazeBaseVR** RAN stimuli; reproduce the 40 ms prediction
horizon for 250 Hz recordings and 44 ms horizon for the Quest Pro cohort.
Match subject-wise five-fold cross validation, LSTM/CTEF/ClPr architectures,
P50/P95 (deg), large/small saccades and post-saccadic critical evaluation
periods, avoiding leakage across individuals. Reference table examples:
GazeBaseVR CTEF fixation P50=0.174°, P95=0.59°; large saccade P50=2.7°,
P95=8.67°. Quest Pro CTEF fixation P50=0.46°, P95=1.55°. These values are
from **published experimental gaze measurements**, not human opinion ratings.
Comparing FoveaBench with this paper requires matching protocol, device
precision, coordinates, prediction horizon and subject splits; our 90° virtual
camera UV errors are NOT directly comparable.

### 2. Perceptual/human-alignment: Mantiuk et al. FovVideoVDP (SIGGRAPH 2021)

Paper https://doi.org/10.1145/3450626.3459831 ; official metric
https://github.com/gfxdisp/FovVideoVDP and results
https://www.cl.cam.ac.uk/research/rainbow/projects/fovvideovdp/html_reports/benchmark/ .

This is our clearest route to comparing numerical predictions against actual
human visual judgements (MOS/JOD, preference correlations), not simply gaze
location measurements. Before running: obtain matched stimuli/reference pairs,
the original human data and rights for research reuse; pin software version;
match display luminance/EOTF/field of view/pixels per degree, fixation and
viewing distance. Reproduce the paper's actual test partition, nonlinear
regression fitting, PLCC/SROCC and preference interpretation. Calibration
MUST be done on non-test data. If published trial-level human ratings aren't
available, **do not claim reproduction or human validation**. Published
SROCC values and human preferences are not interchangeable with our synthetic
weighted-MSE scale.

### 3. XR system score alignment: Kwon et al. XRBench (MLSys 2023)

Paper https://proceedings.mlsys.org/paper_files/paper/2023/hash/07b7c2f8a6978e376f9656d69619bfbb-Abstract-mlsys2023.html
and reproducible MAESTRO code https://github.com/XRBench/XRBench-MLSys2023 .
Run authors' Figure 5/6 scripts under pinned dependencies; then replicate
Figure 7 variability. Crosscheck deadline miss rates, frame drops, energy,
model accuracy and multi-model concurrency. **XRBench is a computational
benchmark; its published outcomes are not subjective human quality scores**.

### 4. GazeBaseVR empirical recording ingestion

Dataset https://figshare.com/articles/dataset/GazeBaseVR_Data_Repository/21308391
(CC BY 4.0; ~2.3 GB, 5,020 recordings, 407 participants, 250 Hz). Start with
the original provenance schema and one task. Keep left/right unit directions,
validity, nanosecond timestamps, calibration errors, participant IDs and sample
time separate; NEVER silently interpolate missing ground truth or mix session
IDs across train/test. Match the published dataset statistics after ingestion.

### 5. Human psychophysics candidate: foveated metamers

https://github.com/billbrod/foveated-metamers includes behavioral experiment
code. Pin the exact reviewed paper, original stimulus/participant files, and
license/consent **before** treating it as a reproduction target. This
candidate is currently unverified for complete matched public rating access.

## Human agreement evaluation protocol

`python -m foveabench.paper_validation compare-human --csv human_scores.csv
--provenance provenance.json --output results/human-comparison-001`
performs a *diagnostic* analysis for properly sourced per-participant human
quality scores and predicted scores matched on identical stimulus IDs. The
ratings CSV uses:

```csv
participant_id,stimulus_id,human_score,predicted_score
```

Both scores must be oriented **higher = better**. The metric should be
participant-independent for a fixed stimulus; model and display-specific
reproducibility metadata are required from the operator. Do not use arbitrary
synthetic numbers as human ratings. Minimum: 5 distinct people, 6 stimuli.
The tool reports stimulus-level Spearman rank correlation, agreement on
non-tied stimulus pairs and 95% *participant-cluster* bootstrap intervals.
This **does not automatically certify paper replication**. It cannot verify
consent, optical calibration, authentic published ratings, licensing, or
reproduce nonlinear original-paper regression. Prefer n much larger than these
minimal integrity floors for any scientific claim.

Example required provenance JSON (fill only with VERIFIED information):

```json
{
  "paper_id": "SIGGRAPH-2021-FOVVIDEOVDP",
  "source_url": "https://publisher.example/verified-data-source",
  "license": "confirmed license or permission",
  "human_rating_source": "original study published human ratings (not synthetic)",
  "display_calibration": "documented device, FOV, luminance, viewing distance, px/deg and stimulus geometry",
  "quality_higher_is_better": true,
  "provenance_verified_by_operator": true
}
```

This manifest is **not** proof of verification just because it says `true`.
New human data collection requires relevant ethics review and informed consent.

## Engineering program (acceptance gates)

| Stage | Build next | Empirical acceptance | Blockers |
|---|---|---|---|
| A. Interactive visual benchmark | Real captured native frames; local playback controls; provenance; non-overwrite | Browser plays recorded Vulkan output matching CSV/manifest; full reference pixel match = 0 | None under UTM CPU-Vulkan; **no hardware score** |
| B. Real gaze source | GazeBaseVR audited adapter; recorded subject IDs and acquisition time | Data completeness/coordinates/calibration checks; subject-exclusive splits and real gaze prediction P50/P95; license evidence | Dataset ingestion/download and human-data usage terms |
| C. Paper baselines | Run official ETRA 2026 code and verified XRBench scripts in isolated environments | Reproduce compatible table/figure and uncertainty; any deviation explained, including device differences | Matched code, datasets, measured horizons |
| D. Quality/human validation | FovVideoVDP with exactly specified optical display config; obtain original human JOD/MOS | Reproduce original rank correlation and confidence interval without tuning on test; transfer to our stimuli only if validated | Matched human rating availability, device calibration |
| E. Real graphics benchmark | Rasterized Vulkan VRS attachments, per-eye scene geometry, 3D motion; high-res material workload | Actual fragment invocation savings and hardware counters alongside measurable quality; cross-driver repeatability | Physical VRS-capable GPU; cannot get Apple M2 Metal features through software Vulkan |
| F. ILLIXR streaming and live/replay | Independently authorized official runtime adapter; time synchronization | Same gaze/head/scene history preserved, known event delays; paired offline vs live residuals and algorithm-ranking agreement | ILLIXR starter-task AI restriction, supervisor approval, real headset |
| G. RL and adaptive optimizer | Constrained action/reward interface, contextual bandit, later PPO only if temporal returns matter | Beat tuned fixed/hold/velocity and rule-based policies on *sealed* new people/scenes/devices; no quality-gate regression; include decision overhead and training cost | Meaningful reward calibration from B–F |
| H. Open benchmark/paper | Versioned benchmark, deterministic runners, independent reproduction package | External group independently reproduces representative claims | Robust artifacts and honest limitations |

**Paper north star:** determine the conditions under which an unattended replay
benchmark preserves live human-experience rankings, not merely optimize
against a synthetic sensor simulator. Measure both agreements and failures;
negative findings are publishable when the design is sufficiently rigorous.

## Immediate next 3 milestones

1. **Now** run visual showcase on existing UTM and inspect frame-accurate
   truth/used gaze + full/fixed/tracked/lagged spatial artifacts. Fix code bugs
   under one committed source tree; no need to reinstall ILLIXR.
2. **Next** import public GazeBaseVR *task subset* with trace-level QC and
   metadata. Keep participant-disjoint results; repeat predictor evaluation
   and begin ETRA 2026 source reproduction with exact horizons. No SOTA claims
   until real data and paper baselines are matched.
3. **Then** launch human-judgment alignment from FovVideoVDP public study if
   stimulus/rating rights allow it, alongside actual GPU/ILLIXR runs after
   access and approvals. Only after this build reward-driven optimization.

## Scientific caveat about current synthetic transfer checks

Old synthetic IDs 00–03 and new IDs 04–07 are generated by exactly the same
three hand-coded families; identity-disjointness is necessary but absolutely
not sufficient to establish human generalization. Also, the trained model
receives **past causal hold/velocity outputs**, not direct eye camera images.
It cannot discover a better predictor beyond the convex combination of those
existing outputs. To improve robustly, train a real time-series predictor on
raw measured eye histories and evaluate under actual latency budgets.
