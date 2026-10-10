# Research conduct and documentation policy

Every code, experiment, scientific inference and failed attempt should be recorded with **date, author/operator, commit, command, inputs, seeds, device, output directory, hashes, result and limitation**. Don't silently rewrite history: append corrections with original claim ID and a reason.

### Experimental source hierarchy

1. **Raw reproducible evidence:** immutable CSV/images/manifest, code commit, pinned config and log/CI artifact hash. Keep on storage under experiment ID; do not add large raw participant data to Git.
2. **Verified execution:** CI or recorded local command with exit status and device identification. CI ARM64 **is not** the user's actual UTM VM. Local UTM console logs are stronger evidence for that environment.
3. **Reported derivative:** summary from raw data with declared units/metrics and grouping. Tables transcribed from a conversation are useful provisional historical records, not replacement raw evidence.
4. **Published external result:** outside benchmark reference value. Store bibliographic link and exact protocol; **never** relabel it “reproduced” until matched execution and independent analysis exist.
5. **Proposed claim:** design/hypothesis with falsification path; no success score.

### Required research log fields

- `[run_id, UTC timestamp, branch+SHA, git dirty state, host+OS+architecture, Vulkan physical-device type and driver, device calibration, workload profile+SHA, input dataset ID+SHA+license+consent, participant grouping policy, software dependencies, exact invocation, random seeds, warmup/repetition, failure/timeouts, outputs+SHA, metric definitions, uncertainty method, result status, significance limits, decision, next step]`.
- For trained models add features (future information audit), train/validation/test ID lists, optimizer, hyperparameters, stopping rule, checkpoint hash, inference time, adversarial/domain-shift data, and retraining versus frozen-checkpoint distinction.
- For human comparison additionally require human-rating source, IRB/ethics policy where applicable, demographics/privacy controls, viewing distance, luminance/EOTF, HMD pixels/degree and consent permissions. Never imply an exemption has been granted.

### Claims forbidden without appropriate evidence

Do not say: GPU speedup from software llvmpipe; hardware VRS when only a compute shader did sample sharing; energy savings without instrument; participant validity from synthetic agent IDs; live/presentation latency from `vkCmdWriteTimestamp`; human perception from weighted MSE; established novelty from combining known libraries; reinforcement learning from supervised Adam/lookup table; published paper reproduced just because title/score is in the registry; full ILLIXR integration from a separate checkout.

### Experimental safeguards

- Refuse overwrite of evidence directories; fingerprint files with SHA-256 and verify before external dissemination.
- Do not upload private subject data, restricted stimuli or tokens to public GitHub.
- Current software must remain independent of official ILLIXR starter tasks that prohibit agentic AI completion; obtain permission/clarity before agentic modifications there.
- Preserve split partition keys by *real participant* and session/device when human data become available; avoid frame-level leakage.
- Public PRs need code correctness CI, documentation update, and status/limitations. Unexpected CI failure is a finding/incident, not something to hide.
- Proposed experiment scripts and summaries must identify result classes (`software-vulkan-functional`, `synthetic`, `real-gaze-offline`, `native-hardware`, `live-human`) instead of promoting the class.

### Documentation done criteria for all subsequent PRs

Update: (i) code map if changed API; (ii) `RESULTS.md` for actual new measurements, or clearly 'NOT RUN'; (iii) development log including setbacks; (iv) `CLAIMS.md` if proposing/upgrading scientific novelty; (v) public-facing README/status links. Commit generated source inventory separately as a checksum record if publishing a release. Validate archive integrity locally and never commit an unreviewed generated participant-data dump.
