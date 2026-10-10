#!/usr/bin/env bash
# Execute Phase 1 and Phase 2 concurrently with disjoint result directories.
# Phase 2 MUST have a working Vulkan installation; it will not silently fall back to CPU emulation.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DATE="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${1:-results/parallel-$DATE}"
if [[ -e "$OUT" ]];then echo "Refusing overwrite: $OUT" >&2;exit 2;fi
mkdir -p "$OUT"
python3 -m foveabench.phase2 make-trace --output "$OUT/input.csv" --frames 32
# Build first; no broad automatic OS mutation or special driver installation.
cmake -S native/vulkan_compute -B build/fb-vulkan -DCMAKE_BUILD_TYPE=Release
cmake --build build/fb-vulkan --parallel 2
python3 -m foveabench.phase1 run --output "$OUT/phase1" --seed 20261010 >"$OUT/phase1.log" 2>&1 &
P1=$!
python3 -m foveabench.phase2 run --trace "$OUT/input.csv" --output "$OUT/phase2" --frames 32 >"$OUT/phase2.log" 2>&1 &
P2=$!
S1=0;S2=0
wait "$P1" || S1=$?
wait "$P2" || S2=$?
{
 echo '# Concurrent research execution ledger'
 echo ''
 echo "- Phase 1: $([[ $S1 -eq 0 ]] && echo PASS || echo FAIL) (exit $S1)"
 echo "- Phase 2: $([[ $S2 -eq 0 ]] && echo PASS || echo FAIL) (exit $S2)"
 echo "- Results location: $OUT"
 echo '- Runs were independent and concurrent; neither phase implicitly validated the other.'
 echo '- No unattended human subject/device data was collected.'
} > "$OUT/STATUS.md"
echo "Concurrent run done: Phase1=$S1 Phase2=$S2 => $OUT"
[[ $S1 -eq 0 && $S2 -eq 0 ]]
