# FB-LEARN-RENDER: Paired learned-model visualization through actual Vulkan compute

Train a supervised model with `python -m foveabench.learn train ...` first.
Then bridge the **held-out** synthetic predictions to nine native Vulkan
workloads (3 motion classes × 3 models), using matched timestamps and truth.

From Ubuntu with the FoveaBench virtual environment active:

    python -m foveabench.learn_bridge prepare \
      --ml-output results/ml-utm-20261010T153731Z \
      --output results/bridge-first \
      --condition latency-60
    python -m foveabench.learn_bridge render --prepared results/bridge-first
    cat results/bridge-first/report.md

Prepare validates the model and provenance, chooses the first held-out trace
for each of synthetic fixation, pursuit and jump, and produces identical
per-frame truth and timestamps for all three predictors. Missing predictions
were already excluded by supervised training; no implicit imputation occurs.
Max frames 0 means all eligible; CI can choose `--max-frames 24`.

`render` displays nine tqdm progress steps with explicit per-workload counts.
It builds/runs the Phase 2 native Vulkan backend, records native artifacts,
and compares the *tracked* foveation policy image quality across algorithms.
`report.md`, `comparison.csv`, `paired_frame_errors.csv`, and `manifest.json`
contain paired evidence and SHA256 input/model fingerprints.

These are EXPLORATORY, synthetic and numerically weighted-MSE results; the
trained model was already evaluated on this test partition. Treating it as
fresh sealed confirmation would contaminate future research. Do not use
these outcomes to iterate on the model and call the same participants a
preregistered independent test. Evaluate any revised model on genuinely
new participant/scene/device identities.

Software Vulkan (llvmpipe) is not physical GPU VRS. We do not interpret
timestamp changes in serial runs as improved hardware performance.