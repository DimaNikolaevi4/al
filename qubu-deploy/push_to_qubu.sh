#!/bin/bash
# =============================================================================
# Скрипт для загрузки файлов в Qubu через Git LFS
# =============================================================================
# Использование:
#   chmod +x push_to_qubu.sh
#   ./push_to_qubu.sh /путь/к/папке/репозитория
# =============================================================================

set -e

# --- Конфигурация ---
QUBU_GIT_TOKEN="${QUBU_GIT_TOKEN:?Set QUBU_GIT_TOKEN env var (see .env.secrets)}"
QUBU_GIT_URL="https://REDACTED_USERNAME:${QUBU_GIT_TOKEN}@git.qubu.ai/REDACTED_USERNAME/ml_model-intellektualniy-tyutor-na-osnove-otkrytykh-bolshikh-yazykovykh-modelei-dlya-spo.git"
GGUF_URL="https://huggingface.co/bartowski/Mistral-Small-24B-Instruct-2501-GGUF/resolve/main/Mistral-Small-24B-Instruct-2501-Q4_K_M.gguf"
GGUF_FILE="Mistral-Small-24B-Instruct-2501-Q4_K_M.gguf"

REPO_DIR="${1:-./qubu-model-repo}"

echo "=== Qubu Git LFS Deploy Script ==="
echo "=== Repo: $REPO_DIR ==="

# --- Шаг 1: Клонировать или обновить репозиторий ---
if [ -d "$REPO_DIR/.git" ]; then
    echo "[1/6] Updating existing repository..."
    cd "$REPO_DIR"
    git pull origin main || true
else
    echo "[1/6] Cloning Qubu repository..."
    git clone "$QUBU_GIT_URL" "$REPO_DIR"
    cd "$REPO_DIR"
fi

# --- Шаг 2: Настроить Git LFS ---
echo "[2/6] Setting up Git LFS..."
git lfs install
git lfs track "*.gguf"
git add .gitattributes 2>/dev/null || true

# --- Шаг 3: Скачать GGUF (если нет) ---
if [ ! -f "$GGUF_FILE" ]; then
    echo "[3/6] Downloading GGUF model (~15 GB)... This may take 15-30 minutes."
    wget -c -O "$GGUF_FILE" "$GGUF_URL"
    echo "[3/6] GGUF downloaded: $(du -h $GGUF_FILE | cut -f1)"
else
    echo "[3/6] GGUF already exists: $(du -h $GGUF_FILE | cut -f1)"
fi

# --- Шаг 4: Скопировать файлы проекта ---
echo "[4/6] Copying service files..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Копируем сервисный файл
if [ -f "$SCRIPT_DIR/service_gguf.py" ]; then
    cp "$SCRIPT_DIR/service_gguf.py" .
    echo "  - service_gguf.py copied"
fi

# Копируем bentofile.yaml
if [ -f "$SCRIPT_DIR/bentofile.yaml" ]; then
    cp "$SCRIPT_DIR/bentofile.yaml" .
    echo "  - bentofile.yaml copied"
fi

# Копируем requirements
if [ -f "$SCRIPT_DIR/requirements_gguf.txt" ]; then
    cp "$SCRIPT_DIR/requirements_gguf.txt" ./requirements.txt
    echo "  - requirements.txt copied"
fi

# --- Шаг 5: Закоммитить ---
echo "[5/6] Committing changes..."
git add -A
git commit -m "Deploy: GGUF model + llama-cpp-python service (Q4_K_M)" || \
    echo "  (nothing to commit or already committed)"

# --- Шаг 6: Запушить ---
echo "[6/6] Pushing to Qubu... (15 GB via LFS, may take 15-30 min)"
git push origin main

echo ""
echo "=== SUCCESS! Files pushed to Qubu repository ==="
echo "=== Next step: Update inference config on Qubu and trigger deploy ==="
echo "=== URL: https://qubu.ai/models/intellektualniy-tyutor-na-osnove-otkrytykh-bolshikh-yazykovykh-modelei-dlya-spo/edit ==="
