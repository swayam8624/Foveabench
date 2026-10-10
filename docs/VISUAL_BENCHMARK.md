# FB-VISUAL-01: watch native Vulkan captures like a GPU benchmark

## What you see, and what you do not

FB-VISUAL-01 captures **actual image outputs of the headless native Vulkan compute
shader**, records all 4 policies on both synthetic diagnostic scenes, converts
its PPM images to PNG, and generates a standalone interactive HTML replay.
The visual output is not synthesized in the browser; browser playback happens
**after** the Vulkan commands finish and cannot stand in for real-time XR.

Visible comparisons: full-quality reference; center-only fixed foveation;
tracked gaze; 40ms-lagged tracking. Play, pause, scrub frames, switch two
scenes, change replay speed, inspect timestamped truth/used gaze crosshairs and
per-frame quality / sampling proxy graph. The HTML does **not** require web
internet or a JavaScript package installation and can open as a local file.

The current Vulkan backend dispatches **every pixel** through a compute shader,
so lower sample fraction proxies do not mean fewer fragment invocations or real
GPU speedup. On the UTM guest, llvmpipe provides functional software Vulkan;
reported Vulkan timestamp queries are not M2 Pro GPU measurements. Recorded
browser playback is not a live benchmark. Scenes are diagnostic chirp and edges,
not realistic 3D XR scenes, and perceptual error proxies are not human ratings.

## One command inside the existing UTM Ubuntu VM

```bash
cd ~/research/Foveabench
source .venv/bin/activate
git pull --ff-only origin main
python -m pip install -e .
bash scripts/run_visual_all.sh
```

Expected: tqdm checkpoint inspection, 72 native frame times × 2 scenes × 4
policies = **576 actual Vulkan dispatches**, 576 converted captured PNGs and a
browser viewer. If the Ubuntu desktop cannot launch automatically, open the
exact path printed at the end using `xdg-open` or Firefox. An actual trained
model's diagnostic values are printed when `results/ml-utm-20261010T153731Z`
exists, and when a saved `results/.../traces/pursuit-learned.csv` exists,
the first visual demonstration replays **that learned predictor's gaze**.
Otherwise it falls back to a standalone synthetic hybrid trace. It
remains an exploratory replay of previously used synthetic evidence.

To visualize previously exported trained-model predictions, supply their
canonical trace (from `foveabench.learn_bridge prepare`, e.g.,
`results/learned-render-.../traces/pursuit-learned.csv`) with:

```bash
python -m foveabench.showcase run \
  --trace results/learned-render-.../traces/pursuit-learned.csv \
  --output results/visual-learned-pursuit-001 \
  --frames 120 --width 256 --height 144 --open
```

The `--frames` parameter limits replay to the first N frames of the input
trace. Use a unique output directory for each benchmark; previous evidence is
not overwritten. To ensure paired policy comparisons, always use the same
source trace, scenes, resolution and settings for the respective methods.

The output holds `native/frames.csv`, `native/manifest.json`, per-frame PPMs,
`viewer/assets/*.png`, `viewer/index.html`, `viewer/manifest.json` with SHA-256
provenance, plus a summary `report.md`. The viewer's browser controls do NOT
change the native rendering policy, only the recorded playback configuration.
