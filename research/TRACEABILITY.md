# Traceability matrix: question → implementation → raw evidence → decision

A passing pipeline does **not** prove a novelty hypothesis. Evidence names below indicate the narrow level actually supported.

| Claim/findings IDs | Question or observation | Implementation path | Primary artifact / CI evidence | Demonstrated? | Required next evidence |
|---|---|---|---|---|---|
| N-001 | Offline replay preserves live human policy ordering within some measurable envelope | `phase1.py`, `phase2.py`, `phase3.py`; future approved live adapter | F-001 to F-004 only synthetic/headless | **NO**: zero live comparison | Same real participants, headset/display timing, paired offline and live rankings |
| N-002 | Benchmark can predict probability its own ranking is wrong | `phase3.py` train-only selector is groundwork; no `q(c)` predictor | F-004 | **NO** | Real disagreement labels; calibration on unseen headset/subject splits |
| N-003 | Valid workload search finds ranking reversals | Synthetic perturbations in `phase1.py` only; no adversarial optimizer | F-001, F-004 | **NO** | Physically calibrated constraints, search baseline, external transfer |
| N-004 | Active experiment selection cuts validated benchmarking cost | No implementation | None | **NO** | Sequential allocation vs fixed randomized experiments |
| N-005 | Temporal perceptual metric improves on existing metrics | `paper_validation.py` evaluator only | F-017: no human data | **NO** | Reproduce FovVideoVDP & obtain real subjective ratings |
| N-006 | Neural/bandit/RL optimization improves actual XR under hard constraints | `learn.py` supervised prediction only; `learn_bridge.py` for posthoc rendering | F-008, F-009, F-010, F-012 | **NO**: current neural network loses overall | New real gaze, measured GPU/quality cost, safe train/deploy controls |
| N-007 | Scientific reproducibility protocol prevents faulty XR inference | `phase1.py`, `phase2.py`, `research_archive.py`, `RESEARCH_POLICY.md` | F-002/F-014 functionality and hash tests | **Engineering demonstrated**, no methods novelty proved | Independent lab reproduction on multiple real GPU/headsets |
| N-008 | Unique public synchronized multimodal XR benchmark corpus | Catalogues only | `datasets/registry.json`, F-001 | **NO** | Rights-cleared collected synchronised data, provenance and baselines |
| I-001 | Causal synthetic trace prediction works | `foveabench/phase1.py` | F-001, GitHub CI | **YES, synthetic only** | Real gaze recordings |
| I-002 | Native compute works on UTM ARM64 llvmpipe | `native/vulkan_compute/main.cpp`, `shaders/foveation.comp` | F-002, F-003 | **YES, CPU software Vulkan** | Actual VRS on physical GPU |
| I-003 | Different prediction inputs alter synthetic render MSE | `learn_bridge.py`, `phase2.py` | F-005, F-010 | **YES, numeric proxy** | Independent human-based quality agreement |
| I-004 | Model select/train splits exclude specified synthetic IDs | `phase3.py`, `learn.py`, `learn_transfer.py` | F-004, F-007/F-012; relevant tests | **YES, per synthetic identity** | Participant-disjoint real-world test |
| I-005 | Trained NumPy supervised model produced actual checkpoint | `learn.py`, `model.npz`, `history.csv` | F-008/F-009 and CI run `38064010661` | **YES, did not beat hold overall** | New objective/architecture and real-data validation |
| I-006 | Learned model drives native output (offline) | `learn_bridge.py`, `phase2.py` | F-010, UTM `learned-render-20261010T154459Z` | **YES, 16,848 dispatches** | Visual physical GPU and real scenes |
| I-007 | Native captured Vulkan images replay in browser | `showcase.py`, capture-every in `main.cpp` | F-014, CI run `38066563920` | **YES on CI**; local UTM showcase pending | User UTM visual demonstration and live path |
| I-008 | External paper replication infrastructure exists | `paper_validation.py`, paper registry | F-017 | **Contract/tests only** | Official independent table/figure reproduction |
| I-009 | Code/evidence hashes generated | `scripts/research_archive.py` | `tests/test_research_archive.py` | **Unit-tested** | Archive and verify real raw local experiment |

## Required source chain before scientific publication

Published number → original data license/consent and immutable SHA → exact input preprocessing + methodology → immutable reference output → matching metric and sample/group definition → our independent execution and output SHA → error bar/unit analysis → reviewer-verifiable reproduction summary. Missing a link means evidence incomplete.

**No scientific link should point to a future/guessed local `results` file**: the UTM paths named in `RESULTS.md` were explicitly printed by the user, but the local files are not contained in Git. Contributors must verify and archive them separately before including as redistributed datasets.
