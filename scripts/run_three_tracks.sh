#!/usr/bin/env bash
# Phase 1 and Phase 2 execute concurrently; Phase 3 requires completed Phase 1.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ "$#" -gt 0 ]]; then OUT="$1"; else OUT="results/three-tracks-$(date -u +%Y%m%dT%H%M%SZ)"; fi
if [[ -e "$OUT" ]]; then echo "Refusing overwrite: $OUT" >&2; exit 2; fi
mkdir -p "$OUT"
python3 -m foveabench.phase2 make-trace --output "$OUT/trace.csv" --frames 24
cmake -S native/vulkan_compute -B build/fb-vulkan -DCMAKE_BUILD_TYPE=Release
cmake --build build/fb-vulkan --parallel 2
python3 -m foveabench.phase1 run --output "$OUT/phase1" --seed 20261010 > "$OUT/phase1.log" 2>&1 &
P1=$!
python3 -m foveabench.phase2 run --trace "$OUT/trace.csv" --output "$OUT/phase2" --frames 24 > "$OUT/phase2.log" 2>&1 &
P2=$!
S1=0; S2=0; S3=0
wait "$P1" || S1=$?
if [[ "$S1" -eq 0 ]]; then
  python3 -m foveabench.phase3 run --phase1-frames "$OUT/phase1/frames.csv" --output "$OUT/phase3" > "$OUT/phase3.log" 2>&1 || S3=$?
else
  S3=125
  echo "Phase 3 SKIPPED: Phase 1 failed" > "$OUT/phase3.log"
fi
wait "$P2" || S2=$?
{
 echo "# Three-track execution ledger"
 echo ""
 echo "- Phase 1: $([[ $S1 == 0 ]] && echo PASS || echo FAIL) ($S1)"
 echo "- Phase 2: $([[ $S2 == 0 ]] && echo PASS || echo FAIL) ($S2)"
 echo "- Phase 3: $([[ $S3 == 0 ]] && echo PASS || echo FAIL) ($S3)"
 echo "- Phase 1 and 2 were concurrent. Phase 3 starts after Phase 1 finishes."
 echo "- Separate Vulkan execution is NOT gaze/render synchronization."
} > "$OUT/STATUS.md"
cat "$OUT/STATUS.md"
[[ "$S1" -eq 0 && "$S2" -eq 0 && "$S3" -eq 0 ]]
