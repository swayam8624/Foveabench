# Published paper replication and human-grounded validation ledger

**Scientific claim status: NONE of the registered external experiments has been reproduced.** Entries specify candidate protocols and are not proof of access, publication correctness or license permission. The primary machine registry is [`../benchmark_spec/papers/reproduction_registry.json`](../benchmark_spec/papers/reproduction_registry.json); detailed preliminary bibliography is in [`../docs/PAPER_REPLICATION_AND_VALIDITY.md`](../docs/PAPER_REPLICATION_AND_VALIDITY.md).

| ID | Published study or public resource | Target original result (not ours) | What exactly must be matched | Status / blocker |
|---|---|---|---|---|
| **P-001** | ETRA 2026 Melnyk et al. gaze forecasting, DOI `10.1145/3797246.3803043` | GazeBaseVR CTEF fixation P50 **0.174°**, P95 **0.59°**; large-saccade P50 **2.7°**, P95 **8.67°** *as recorded in existing repo paper register* | 40 ms horizon, subject-wise 5-fold, RAN gaze task, appropriate sensor sampling, exactly authors' event segmentation/model code and angular geometry | **NOT REPRODUCED**; official code/supplement and source data not run; publication numbers are **external** |
| **P-002** | SIGGRAPH 2021 FovVideoVDP, DOI `10.1145/3450626.3459831` | Human subjective quality ranking and agreement with gaze-aware metric | Exact original stimuli and ratings, luminance/EOTF, viewing geometry, calibration fitting on development only, published scoring and confidence methodology | **NOT REPRODUCED**; no actual human score table ingested |
| **P-003** | MLSys 2023 XRBench, published GitHub `XRBench/XRBench-MLSys2023` | Frame deadlines/accuracy/energy and published figures | Official workload, model versions, baseline hardware simulator/MAESTRO setup and figure script | **NOT REPRODUCED**; do not call these human opinions |
| **P-004** | GazeBaseVR public recordings (dataset, not necessarily paper reproduction) | Published dataset counts: **5,020 recordings**, **407 people**, **250 Hz** | Licensed download, file census, binocular field meanings, calibration and consent, subject-separated split | **NOT INGESTED**; same as registry only |
| **P-005** | Foveated metamers behavioral experiments | Human discrimination/psychophysical thresholds | Pin reviewed paper, rights-cleared original stimuli and response records, monitor/HMD settings, baseline stimuli | **CANDIDATE UNVERIFIED**; publication identity and matched rating access pending |

The separate public dataset registry lists 22 sources; its two local entries are **procedural**, and the remaining 20 external sources are **not downloaded**. By usage: gaze+head recordings for prediction/replay, calibrated perception scores for image-quality agreement, 3D scenes for realistic rendering, and XR workloads for real system performance. Data category ≠ any proof of transfer to a different category (e.g., TUM VI has head/IMU data, not eye gaze).

## Minimum acceptance dossier for each paper

- Stable paper DOI/version and source code revision; identical task definition, units, horizon, event taxonomy and split policy.
- Download license/permissions, checksummed original files, pseudonymized participant ID/consent compliance, original preprocessing plus code commit.
- Independent reproduction command, pinned environment/hardware, stderr/stdout capture, raw results and references to specific original figure/table row.
- Reproduction deviation `(ours - published)` under **matching units/definitions**, with uncertainty and explanation. Do not impose an arbitrary ± tolerance before studying original paper variance.
- Exactly distinguish: `registered`, `downloaded`, `ingested`, `reproduced-author-setup`, `independently-reimplemented`, `tested-on-FoveaBench`, `human-live-validated`.

## Human-score correlation is a separate study

Current `foveabench.paper_validation compare-human` computes stimulus-mean Spearman rank correlation and pairwise ordering, plus a participant-level bootstrap, **only when the operator provides a ratings table and source metadata**. For an actual replication, audit data rights, display luminance/FOV/px-per-degree/EOTF, quality-scale orientation and participant grouping, then run official metric settings and independently calculate agreement. A real human-score file is required; test fixture ratings do **not** count.

No participant was recruited by the repository; no ethics/IRB decision is assumed. Before capturing new human data, obtain appropriate university/institutional human-subject oversight and signed consent/permissions as needed. Do not expose individual gaze traces or identifying session metadata through public logs, CI uploads, browser previews or generated reports.

## Most valuable validation ladder

1. **Dataset fidelity:** GazeBaseVR input importer, field/channel audit, exact counts and real participant-disjoint evaluation.
2. **Original-paper reproduction:** run original prediction/perception methods under their own registered conditions, and confirm/explain their reported figures.
3. **Cross-metric comparison:** use matched reference/render stimuli with calibrated VDP and available *actual* human rating records; compare all baselines, not just our MSE.
4. **Headset/system:** physical GPU foveation counters and actual end-to-end timestamps, real scenes, paired algorithm ordering across hardware.
5. **Human/live replay:** same scene/head/eye/clock setup with a preregistered comparison of live and replay algorithm rankings and failure boundaries.
6. **Novel confidence estimator:** only after RQ1 produces real rank-disagreement labels, fit a model and evaluate calibration on sealed new devices/participants.

Nothing in the current repository establishes Steps 1–6 as completed. For technical limitations refer to [`RESULTS.md`](RESULTS.md) and [`CLAIMS.md`](CLAIMS.md).
