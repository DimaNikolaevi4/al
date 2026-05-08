#!/bin/bash
# =============================================================================
# Startup script для Qubu — AI Tutor (GGUF variant)
# =============================================================================
# Устанавливает llama-cpp-python из pre-built wheel для CUDA 12.1
# БЕЗ компиляции из исходников (экономия 20-30 минут).
#
# ВАЖНО: Если GGUF загружен через Git LFS в репозиторий Qubu,
# строки с wget можно убрать (модель уже будет в /workspace/model).
# Если GGUF НЕ в репо — раскомментировать блок скачивания.
# =============================================================================

set -e  # Выход при ошибке

echo "=== [STARTUP] Installing llama-cpp-python from pre-built wheel (CUDA 12.1) ==="

pip install --no-cache-dir \
  "https://abetlen.github.io/llama-cpp-python/whl/cu121/llama_cpp_python-0.3.2-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"

echo "=== [STARTUP] llama-cpp-python installed ==="

# =============================================================================
# БЛОК СКАЧИВАНИЯ GGUF — раскомментировать если модель НЕ в Git LFS
# =============================================================================
# echo "=== [STARTUP] Downloading GGUF model (~15 GB) ==="
# mkdir -p /workspace/model
# wget -c -O /workspace/model/Mistral-Small-24B-Instruct-2501-Q4_K_M.gguf \
#   "https://huggingface.co/bartowski/Mistral-Small-24B-Instruct-2501-GGUF/resolve/main/Mistral-Small-24B-Instruct-2501-Q4_K_M.gguf"
# echo "=== [STARTUP] GGUF model downloaded ==="

echo "=== [STARTUP] Startup complete ==="
