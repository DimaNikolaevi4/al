#!/bin/bash
# =============================================================================
# Startup script для Qubu — AI Tutor (GGUF variant)
# =============================================================================
# Устанавливает llama-cpp-python из pre-built wheel для CUDA 12.1
# БЕЗ компиляции из исходников (экономия 20-30 минут).
#
# Если GGUF загружен через Git LFS в репозиторий Qubu — блок скачивания
# пропускается автоматически (файл уже в /workspace/model).
# =============================================================================

set -e

MODEL_DIR="/workspace/model"
WHEEL_URL="https://abetlen.github.io/llama-cpp-python/whl/cu121/llama_cpp_python-0.3.2-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"

# --- Step 1: Install llama-cpp-python from pre-built wheel ---
echo "=== [STARTUP] Installing llama-cpp-python from pre-built wheel (CUDA 12.1) ==="
pip install --no-cache-dir "$WHEEL_URL"
echo "=== [STARTUP] llama-cpp-python installed ==="

# --- Step 2: Download GGUF if not already present ---
GGUF_FILE="$MODEL_DIR/$(ls "$MODEL_DIR"/*.gguf 2>/dev/null | head -1 | xargs basename 2>/dev/null || true)"

if [ -z "$GGUF_FILE" ] || [ ! -f "$MODEL_DIR/$GGUF_FILE" ]; then
    echo "=== [STARTUP] No GGUF found in $MODEL_DIR, downloading... ==="
    mkdir -p "$MODEL_DIR"

    GGUF_URL="${GGUF_URL:-https://huggingface.co/bartowski/Mistral-Small-24B-Instruct-2501-GGUF/resolve/main/Mistral-Small-24B-Instruct-2501-Q4_K_M.gguf}"
    GGUF_OUT="$MODEL_DIR/Mistral-Small-24B-Instruct-2501-Q4_K_M.gguf"

    # Try wget with retries, fallback to curl
    if command -v wget &>/dev/null; then
        wget --timeout=30 --tries=3 -c -O "$GGUF_OUT" "$GGUF_URL" || \
            curl -fSL --retry 3 --connect-timeout 30 -o "$GGUF_OUT" "$GGUF_URL"
    else
        curl -fSL --retry 3 --connect-timeout 30 -o "$GGUF_OUT" "$GGUF_URL"
    fi

    echo "=== [STARTUP] GGUF downloaded: $(du -h "$GGUF_OUT" | cut -f1) ==="
else
    echo "=== [STARTUP] GGUF already present: $MODEL_DIR/$GGUF_FILE ==="
fi

echo "=== [STARTUP] Startup complete ==="
