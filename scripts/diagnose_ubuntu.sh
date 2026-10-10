#!/usr/bin/env bash
# Read-only environment report. Does not run or inspect ILLIXR starter tasks.
set -u
echo "=== FoveaBench UTM guest diagnostics ==="
date -Is
uname -a
cat /etc/os-release 2>/dev/null | head -n 5 || true
python3 --version
python3 -c 'import numpy; print("NumPy:",numpy.__version__)' || true
command -v vulkaninfo >/dev/null && vulkaninfo --summary 2>&1 | head -n 60 || echo "Vulkan tooling unavailable (not required for CPU model)"
command -v clang++ >/dev/null && clang++ --version | head -n 1 || true
command -v cmake >/dev/null && cmake --version | head -n 1 || true
df -h .
echo "=== End diagnostics ==="
