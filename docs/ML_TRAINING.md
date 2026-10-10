# FB-LEARN-01: real supervised gaze prediction training

FB-LEARN-01 trains a 9-input tanh/sigmoid neural network with NumPy/Adam and tqdm.
It learns how much to blend the *causally generated* hold/velocity predictor outputs.
The ground-truth gaze is used only as a training label and in held-out evaluation.
Subject-disjoint, synthetic-motion-stratified train/validation/test partitions
prevent repeated subject identities crossing dataset boundaries.

From Ubuntu in the repository root, with .venv active:

    python -m pip install -e .
    python -m foveabench.learn train \
      --phase1-frames results/three-tracks-utm-20261010T152017Z/phase1/frames.csv \
      --output results/ml-study-001 \
      --epochs 80 --batch-size 512 --seed 20261010
    cat results/ml-study-001/report.md

Outputs: model.npz (actual trained weights), history.csv (each epoch),
splits.csv, test_metrics.csv (baselines vs learned), test_predictions.csv,
manifest.json and STATUS.md. If the output directory already exists,
training refuses to overwrite evidence.

Scientific limits: current Phase 1 traces are synthetic only. The model is
a supervised blending controller, NOT reinforcement learning, human perceptual
modeling or real GPU optimization. It cannot be asserted to improve real
participants or actual XR applications without real data and validation.