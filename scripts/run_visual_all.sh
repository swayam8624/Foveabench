#!/usr/bin/env bash
# One command, fully visible UTM demonstration with original ML checkpoint.
# Preserves existing benchmark runs and ILLIXR source; no downloads or GPU privileges.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONUNBUFFERED=1

ML="${1:-results/ml-utm-20261010T153731Z}"
OUT="${2:-results/visual-$(date -u +%Y%m%dT%H%M%SZ)}"
[[ ! -e "$OUT" ]] || { echo "Refusing to overwrite $OUT" >&2; exit 2; }

echo '============================================================'
echo ' FOVEABENCH VISUAL DEMONSTRATION + FROZEN MODEL DIAGNOSTICS'
echo '============================================================'
echo "Model: $ML"
echo "New visual evidence: $OUT"
python3 -m unittest discover -s tests -p 'test_showcase.py' -v
python3 -m unittest discover -s tests -p 'test_paper_validation.py' -v
echo '----- PUBLISHED PAPER REPRODUCTION CONTRACTS -----'
python3 -m foveabench.paper_validation registry
if [[ -f "$ML/test_predictions.csv" ]]; then
  echo '----- NEURAL MODEL BLEND-WEIGHT DIAGNOSTIC -----'
  python3 -m foveabench.learn_transfer inspect --ml-output "$ML"
else
  echo "No existing checkpoint predictions at $ML; rendering standalone synthetic traces."
fi

echo '----- VULKAN OFFSCREEN RENDER AND BROWSER REPLAY -----'
# Reuse the user's actual saved trained-model gaze prediction if available.
# No retraining or relabeling: this is exploratory playback of earlier evidence.
LEARNED_TRACE="$(find results -maxdepth 4 -path '*/traces/pursuit-learned.csv' -print 2>/dev/null | sort | tail -n 1)"
if [[ -n "$LEARNED_TRACE" && -f "$LEARNED_TRACE" ]]; then
  echo "Using actual saved neural model predictions: $LEARNED_TRACE"
  python3 -u -m foveabench.showcase run --output "$OUT" \
    --trace "$LEARNED_TRACE" --frames 72 --width 256 --height 144 --open
else
  echo 'Using synthetic hybrid demo; no saved trained-model trace found.'
  python3 -u -m foveabench.showcase run --output "$OUT" \
    --motion hybrid --delay-ms 60 --frames 72 --width 256 --height 144 --open
fi

echo '----- RESULTS -----'
cat "$OUT/report.md"
echo "Open viewer: $(realpath "$OUT/viewer/index.html")"
echo "Ubuntu command if browser did not launch: xdg-open '$(realpath "$OUT/viewer/index.html")'"
