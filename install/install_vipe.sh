#!/usr/bin/env bash
# Step 2 of 4: ViPE (camera solve) in its own environment, without sudo. Safe to re-run.
# Miniforge (user space) supplies nvcc 12.8 + native libs; uv builds .venv with cu128 torch.
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
export UV_HTTP_TIMEOUT="${UV_HTTP_TIMEOUT:-600}"  # torch wheels are ~0.9 GB; uv's 30 s default times out on slow links
# The CUDA extensions are compiled by the conda env's gcc, which does not search Ubuntu's multiarch
# include dir (/usr/include/x86_64-linux-gnu), so a venv on the system Python 3.12 fails with
# "pyconfig.h: No such file or directory". uv's own Python keeps all its headers in one place.
export UV_PYTHON_PREFERENCE=only-managed
ROOT="$HOME/afv"; VIPE="$ROOT/vipe"; CONDA="$ROOT/miniforge"
log() { echo "[$(date +%H:%M:%S)] $*"; }
ARCH="${AFV_CUDA_ARCH:-$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -1 | tr -d ' ')}"  # e.g. 12.0 (RTX 50), 8.9 (RTX 40), 8.6 (RTX 30)

if [ ! -x "$CONDA/bin/conda" ]; then
  log "miniforge"
  curl -fsSL https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -o /tmp/miniforge.sh
  bash /tmp/miniforge.sh -b -p "$CONDA"
fi
source "$CONDA/etc/profile.d/conda.sh"
[ -d "$VIPE/.git" ] || git clone https://github.com/nv-tlabs/vipe.git "$VIPE"
cd "$VIPE"; git rev-parse HEAD
# A .venv left by an earlier run on the system Python is rebuilt on uv's Python (see above).
if [ -e .venv/bin/python ] && [[ "$(readlink -f .venv/bin/python)" != "$(uv python dir)"/* ]]; then
  log "removing .venv built on the system Python"; rm -rf .venv
fi
if ! conda env list | grep -q "^cu128 "; then log "conda env cu128"; conda env create -f envs/cu128.yml; fi
set +u; conda activate cu128; set -u
export CUDA_HOME="$CONDA_PREFIX" TORCH_CUDA_ARCH_LIST="$ARCH" MAX_JOBS=6
nvcc --version | tail -1
log "uv sync (builds CUDA extensions for compute capability $ARCH)"
uv sync
log "smoke"
.venv/bin/vipe --help | head -20
.venv/bin/python -c "import torch;print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_arch_list())"
OUT="$ROOT/provenance"; LIC="$OUT/licences/$(date +%F)"; mkdir -p "$LIC"
echo "vipe commit: $(git rev-parse HEAD)" > "$OUT/vipe_lock.txt"
cp LICENSE "$LIC/ViPE_LICENSE.txt" 2>/dev/null || true
log "DONE"
