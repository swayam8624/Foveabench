# Run FoveaBench inside UTM Ubuntu 24.04 ARM64

## Distinguish host and guest

Host: Apple-Silicon Mac (expected M2 Pro, 32 GB), UTM. Guest: Ubuntu 24.04 ARM64 with its own ext4 virtual disk. This Python CPU image-reference model does **not** require GPU passthrough, Vulkan or headset. For ILLIXR starter work, follow the **separate official rules** and do the starter tasks yourself. https://illixr.org/starter_tasks

## Guest commands

Open the Ubuntu terminal and enter:

```bash
uname -m                    # Expected: aarch64
cat /etc/os-release          # Expected: Ubuntu 24.04
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip
mkdir -p ~/research && cd ~/research
git clone https://github.com/swayam8624/Foveabench.git
cd Foveabench
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
python -m foveabench run --preset smoke --output results/utm-smoke-001
```

If a git repository already exists, run `git status` first, then `git pull --ff-only` only if you have no uncommitted conflicts. Create an output path different from existing runs; experiments refuse to overwrite evidence.

## Inspect results

```bash
cat results/utm-smoke-001/STATUS.md
cat results/utm-smoke-001/manifest.json
head -n 8 results/utm-smoke-001/summary.csv
```

Open `results/utm-smoke-001/overview.svg` in Firefox or Chromium in Ubuntu. Image previews in `frames/` use lossless binary PPM; install `imagemagick` separately only if you need PNG conversion.

Then run the larger deterministic suite:

```bash
python -m foveabench run --preset study --output results/utm-study-001
```

For a read-only machine diagnostic:

```bash
bash scripts/diagnose_ubuntu.sh
```

## Export evidence without damaging timestamps

The output folder should live on the guest's Linux filesystem. When complete, archive it and copy the archive to the UTM shared folder if configured:

```bash
tar -czf ~/foveabench-utm-smoke-001.tar.gz -C results utm-smoke-001
sha256sum ~/foveabench-utm-smoke-001.tar.gz
```

Record the guest OS, CPU architecture, VM configuration and NumPy/Python versions from `manifest.json`. If pip cannot reach PyPI or the VM lacks memory, report the exact error; do not claim the run passed.

## Interpretation

Any timing in `frames.csv` is the **CPU reference Python model wall time**, not hardware GPU frame time. Performance inside ARM64 UTM is not representative of an XR headset or desktop native GPU. Treat v0.1 as an input/replay, correctness and quality-proxy proof of pipeline only.
