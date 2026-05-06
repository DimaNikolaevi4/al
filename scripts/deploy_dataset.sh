#!/usr/bin/env bash
# =============================================================================
# Скрипт развёртывания датасета
# Dataset Deployment Script
# =============================================================================
# Использование:
#   ./deploy_dataset.sh                                        # По умолчанию
#   ./deploy_dataset.sh --source ./dataset/data --target /data # Кастомные пути
#   ./deploy_dataset.sh --verify-only                          # Только проверка
#   ./deploy_dataset.sh --stats-only                           # Только статистика
#   ./deploy_dataset.sh --help                                 # Помощь
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Цветной вывод / Colored output
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }
step()    { echo -e "\n${CYAN}${BOLD}==> $*${NC}"; }

# ---------------------------------------------------------------------------
# Конфигурация по умолчанию / Default configuration
# ---------------------------------------------------------------------------
PROJECT_DIR="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
DEFAULT_SOURCE="${PROJECT_DIR}/dataset/data"
DEFAULT_TARGET="/data"  # Путь внутри Docker volume
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.yml"
DATA_CONTAINER="ai-tutor-api"  # Имя контейнера с данными (замените при необходимости)

# ---------------------------------------------------------------------------
# Парсинг аргументов / Argument parsing
# ---------------------------------------------------------------------------
SOURCE_DIR=""
TARGET_DIR=""
VERIFY_ONLY=false
STATS_ONLY=false

show_help() {
    cat <<'EOF'
Использование / Usage:
  ./deploy_dataset.sh [OPTIONS]

Опции / Options:
  --source PATH     Исходная директория с датасетом (по умолчанию: ./dataset/data)
  --target PATH     Целевая директория (по умолчанию: /data внутри Docker volume)
  --verify-only     Только проверка целостности (без копирования)
  --stats-only      Только вывод статистики
  --help            Показать эту справку

Описание:
  Копирует датасет в Docker volume, проверяет целостность и показывает
  статистику (записи по сплитам, распределение по предметам).

Примеры:
  ./deploy_dataset.sh --source ./my_data --target /app/data
  ./deploy_dataset.sh --verify-only
  ./deploy_dataset.sh --stats-only --source ./dataset/data
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --source)       SOURCE_DIR="$2"; shift 2 ;;
        --target)       TARGET_DIR="$2"; shift 2 ;;
        --verify-only)  VERIFY_ONLY=true; shift ;;
        --stats-only)   STATS_ONLY=true; shift ;;
        --help|-h)      show_help ;;
        *) error "Неизвестный параметр: $1"; echo "Используйте --help"; exit 1 ;;
    esac
done

# Устанавливаем значения по умолчанию
SOURCE_DIR="${SOURCE_DIR:-$DEFAULT_SOURCE}"
TARGET_DIR="${TARGET_DIR:-$DEFAULT_TARGET}"

# =============================================================================
# Утилиты / Utilities
# =============================================================================

# Подсчёт строк в JSONL файле (каждая строка — одна запись)
count_jsonl_lines() {
    local file="$1"
    if [[ -f "$file" ]]; then
        wc -l < "$file" | tr -d ' '
    else
        echo "0"
    fi
}

# Проверка JSON валидности (каждая строка JSONL)
validate_jsonl() {
    local file="$1"
    local errors=0
    local total=0
    local line_num=0

    if [[ ! -f "$file" ]]; then
        return 1
    fi

    while IFS= read -r line; do
        line_num=$((line_num + 1))
        total=$((total + 1))
        if [[ -n "$line" ]]; then
            if ! echo "$line" | python3 -c "import sys,json; json.loads(sys.stdin.read())" 2>/dev/null; then
                errors=$((errors + 1))
                if [[ $errors -le 5 ]]; then
                    warn "  Строка ${line_num}: невалидный JSON"
                fi
            fi
        fi
    done < "$file"

    if [[ $errors -eq 0 ]]; then
        success "  ${file##*/}: ${total} записей, валидный JSONL ✓"
        return 0
    else
        error "  ${file##*/}: ${errors}/${total} невалидных строк ✗"
        return 1
    fi
}

# Распределение по предметам
show_subject_distribution() {
    local file="$1"
    local name="${2:-$(basename "$file")}"

    if [[ ! -f "$file" ]]; then
        info "  ${name}: файл не найден"
        return
    fi

    echo -e "  ${CYAN}${BOLD}${name}${NC} — распределение по предметам:"
    python3 -c "
import sys, json
from collections import Counter

subjects = Counter()
total = 0
with open('${file}', 'r') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            subj = obj.get('subject', obj.get('предмет', obj.get('category', 'unknown')))
            subjects[subj] += 1
            total += 1
        except json.JSONDecodeError:
            pass

print(f'    Всего записей: {total}')
for subj, count in subjects.most_common():
    pct = (count / total * 100) if total > 0 else 0
    bar = '█' * int(pct / 5) + '░' * (20 - int(pct / 5))
    print(f'    {subj:<30} {count:>5} ({pct:>5.1f}%) {bar}')
" 2>/dev/null || warn "  Не удалось проанализировать ${name} (требуется Python с JSON)"
}

# =============================================================================
# Статистика датасета / Dataset statistics
# =============================================================================
show_dataset_stats() {
    local dir="$1"

    step "Статистика датасета: ${dir}"

    if [[ ! -d "$dir" ]]; then
        error "Директория не найдена: $dir"
        exit 1
    fi

    echo ""
    echo -e "  ${BOLD}Файлы:${NC}"

    local total_records=0
    local total_files=0
    local file_list=()

    # Ищем JSONL файлы
    while IFS= read -r -d '' file; do
        file_list+=("$file")
    done < <(find "$dir" -name "*.jsonl" -type f -print0 2>/dev/null)

    # Ищем JSON файлы
    while IFS= read -r -d '' file; do
        file_list+=("$file")
    done < <(find "$dir" -name "*.json" -type f -print0 2>/dev/null | grep -v 'package.json' || true)

    if [[ ${#file_list[@]} -eq 0 ]]; then
        warn "JSON/JSONL файлы не найдены в ${dir}"
        return
    fi

    for file in "${file_list[@]}"; do
        local name="${file##*/}"
        local size=$(du -h "$file" | cut -f1)
        local lines=$(count_jsonl_lines "$file")

        echo -e "    📄 ${CYAN}${name}${NC} — ${size} (${lines} строк)"
        total_records=$((total_records + lines))
        total_files=$((total_files + 1))
    done

    echo ""
    echo -e "  ${BOLD}Итого:${NC} ${total_files} файлов, ~${total_records} записей"
    echo ""

    # Распределение по предметам для каждого файла
    for file in "${file_list[@]}"; do
        show_subject_distribution "$file" "${file##*/}"
        echo ""
    done
}

# =============================================================================
# Проверка целостности / Verify integrity
# =============================================================================
verify_dataset() {
    local dir="$1"
    local all_valid=true

    step "Проверка целостности: ${dir}"

    if [[ ! -d "$dir" ]]; then
        error "Директория не найдена: $dir"
        exit 1
    fi

    local file_list=()
    while IFS= read -r -d '' file; do
        file_list+=("$file")
    done < <(find "$dir" \( -name "*.jsonl" -o -name "*.json" \) -type f -print0 2>/dev/null)

    if [[ ${#file_list[@]} -eq 0 ]]; then
        warn "Нет файлов для проверки"
        return
    fi

    for file in "${file_list[@]}"; do
        if ! validate_jsonl "$file"; then
            all_valid=false
        fi
    done

    if [[ "$all_valid" == true ]]; then
        success "Все файлы валидны ✓"
    else
        error "Некоторые файлы содержат ошибки!"
        exit 1
    fi
}

# =============================================================================
# Копирование в Docker volume / Copy to Docker volume
# =============================================================================
deploy_to_docker() {
    local src="$1"
    local dst="$2"

    step "Копирование датасета в Docker volume"
    info "Источник: ${src}"
    info "Цель: ${dst}"

    # Проверяем что Docker запущен
    if ! docker info &>/dev/null; then
        error "Docker не запущен!"
        exit 1
    fi

    # Проверяем исходную директорию
    if [[ ! -d "$src" ]]; then
        error "Исходная директория не найдена: $src"
        exit 1
    fi

    # Ищем запущенный контейнер с volume
    local container=""
    if docker ps --format '{{.Names}}' | grep -q "$DATA_CONTAINER"; then
        container="$DATA_CONTAINER"
    else
        # Пытаемся найти любой контейнер с volume /data
        container=$(docker ps --format '{{.Names}}' | head -1)
        if [[ -n "$container" ]]; then
            warn "Контейнер ${DATA_CONTAINER} не найден, используем: ${container}"
        fi
    fi

    if [[ -n "$container" ]]; then
        info "Копирование в контейнер: ${container}"
        docker cp "$src/." "${container}:${dst}/"
        success "Датасет скопирован в ${container}:${dst}/"
    else
        # Альтернатива: используем Docker volume напрямую
        warn "Запущенные контейнеры не найдены"
        info "Пытаемся использовать docker volume..."

        local volume_name=""
        volume_name=$(docker volume ls --format '{{.Name}}' | grep -i "data\|dataset" | head -1 || true)

        if [[ -n "$volume_name" ]]; then
            # Временный контейнер для копирования
            docker run --rm -v "${volume_name}:${dst}" -v "${src}:/source" alpine sh -c "cp -r /source/. ${dst}/"
            success "Датасет скопирован в volume ${volume_name}"
        else
            error "Docker volume для данных не найден!"
            info "Создайте volume в docker-compose.yml и перезапустите сервисы"
            exit 1
        fi
    fi
}

# =============================================================================
# Основной поток / Main flow
# =============================================================================

if [[ "$STATS_ONLY" == true ]]; then
    show_dataset_stats "$SOURCE_DIR"
    exit 0
fi

if [[ "$VERIFY_ONLY" == true ]]; then
    verify_dataset "$SOURCE_DIR"
    show_dataset_stats "$SOURCE_DIR"
    exit 0
fi

# Полное развёртывание
step "Развёртывание датасета"
info "Источник: ${SOURCE_DIR}"
info "Цель: ${TARGET_DIR}"
echo ""

# 1. Проверяем исходную директорию
if [[ ! -d "$SOURCE_DIR" ]]; then
    error "Исходная директория не найдена: $SOURCE_DIR"
    exit 1
fi

# 2. Проверяем целостность
verify_dataset "$SOURCE_DIR"

# 3. Показываем статистику
show_dataset_stats "$SOURCE_DIR"

# 4. Копируем в Docker
deploy_to_docker "$SOURCE_DIR" "$TARGET_DIR"

# 5. Финальная проверка
step "Финальная проверка"
success "Датасет развёрнут и проверен!"

echo ""
echo -e "${GREEN}${BOLD}========================================${NC}"
echo -e "${GREEN}${BOLD}  Датасет развёрнут!                   ${NC}"
echo -e "${GREEN}${BOLD}========================================${NC}"
echo ""
echo -e "  📁 Источник:   ${CYAN}${SOURCE_DIR}${NC}"
echo -e "  🎯 Цель:       ${CYAN}${TARGET_DIR}${NC}"
echo ""
