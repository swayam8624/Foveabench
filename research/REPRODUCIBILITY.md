# Reproduction, snapshots and chain of evidence

## Environment known for user's actual UTM experiment

- Host context: Apple M2 Pro Mac with UTM Apple virtualization; Ubuntu 24.04.5 LTS guest, `aarch64`, eight virtual CPUs, 11 GiB guest RAM, 4 GiB swap; `vulkaninfo --summary` at run time: Vulkan instance 1.3.275; reported device `llvmpipe (LLVM 20.1.2, 128 bits)` as **PHYSICAL_DEVICE_TYPE_CPU**, Mesa driver 25.2.8.
- Build: Python 3.12.3, GNU C++ 13.3, Clang 18.1.3, CMake 3.28.3, Vulkan development headers, `glslangValidator`. User's ILLIXR source exists separately at `~/research/illixr` and installation under `~/research/illixr-install`, **not linked into FoveaBench**.
- Important: no Apple Metal GPU device was available through this Vulkan VM. All device dispatch times reported here are software driver times, **not Mac native GPU metrics**.

## Key commands (within the already existing VM)

```bash
cd ~/research/Foveabench
source .venv/bin/activate
git status --short
git rev-parse HEAD
python -m pip install -e .
python -m unittest discover -s tests -v
cmake -S native/vulkan_compute -B build/fb-vulkan -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build/fb-vulkan --parallel 2
bash scripts/run_three_tracks.sh "results/three-track-record-$(date -u +%Y%m%dT%H%M%SZ)"
python -m foveabench.paper_validation registry
bash scripts/run_visual_all.sh
```

`results/` and `build/` are excluded by `.gitignore`. Each runner requires a **new result folder**. `scripts/run_visual_all.sh` can select previously saved learned gaze traces; read the report/manifest to verify exactly which gaze source was used. Browser replay is recorded native output, not live XR.

## Actual supervised model and frozen transfer

```bash
python -u -m foveabench.learn train \
 --phase1-frames results/three-tracks-utm-20261010T152017Z/phase1/frames.csv \
 --output "results/train-repro-$(date -u +%Y%m%dT%H%M%SZ)" \
 --epochs 80 --batch-size 512 --hidden 24 --lr 0.003 \
 --patience 20 --seed 20261010

python -m foveabench.learn_transfer inspect \
 --ml-output results/ml-utm-20261010T153731Z
```

For transfer, generate a **new profile** with eight synthetic sessions per motion, seed it differently, and run `foveabench.learn_transfer evaluate` with the frozen `model.npz` and saved `splits.csv`. See `docs/ML_TRANSFER_VALIDATION.md`. This still only assesses same-generator synthetic transfer.

## Every new experiment: automatically inventory and fingerprint

```bash
# Records each tracked code, test and spec file, SHA-256 and functions/line numbers.
python scripts/research_archive.py inventory --repo . \
 --output "results/code-inventory-$(date -u +%Y%m%dT%H%M%SZ)"

# Example: fingerprint original user run files. No raw content is copied/uploaded.
python scripts/research_archive.py archive --repo . \
 --run-dir results/learned-render-20261010T154459Z \
 --output "results/evidence-hash-$(date -u +%Y%m%dT%H%M%SZ)" \
 --description "User ARM64 UTM software-Vulkan learned/hold/velocity diagnostic"

# Locate the last generated fingerprint; verify original raw results are unchanged.
FINGERPRINT=$(ls -dt results/evidence-hash-*/ | head -n1)
python scripts/research_archive.py verify --manifest "${FINGERPRINT}/evidence_manifest.json"
```

**Archive limitation:** the manifest contains absolute original path, checksums and metadata; it does NOT copy raw evidence. For durable backup also copy/harden the complete run directory and hashes. Git worktree dirty status and commit are captured, but do not guarantee all tools/firmware are reproducible unless dependencies are pinned. CI artifact URLs expire; copy artifacts into an access-controlled research storage location.

## Folder layout, trace contracts and interpretation

- `results/three-tracks-*/phase1` holds synthetic gaze pair records and predictors; `phase2` holds software native render output; `phase3` analyzes gaze prediction results only.
- `results/ml-*/model.npz` stores neural weights; `splits.csv` and `history.csv` make train, validation and test choices auditable; `test_predictions.csv` is already held-out *but subsequently used for exploratory analysis*.
- `results/learned-render-*/traces` and `/render/` hold nine matched policies and paired quality deltas; reusing those results for model selection would invalidate a later independent claim.
- `results/transfer-*/evaluation/` holds new synthetic IDs, excluded prior IDs, frozen checkpoint fingerprint and transfer metrics.
- `results/visual-*/viewer/index.html` plus `/assets` holds HTML and PNG capture; playback changes no native shader runtime parameters.
- `benchmark_spec/datasets/registry.json`: **catalogued is not downloaded**. No provided license/consent covers unapproved redistribution.

## Interpretation and integrity checklist

Data SHA + model/checkpoint SHA + git commit + device type + input profile + algorithm settings + result SHA + no input leakage + paired measurement + statistical unit. For method qualification see `research/CLAIMS.md`, for original numbers see `research/RESULTS.md`. An invalid or incomplete condition should be reported `NOT_RUN`, not silently filled.
