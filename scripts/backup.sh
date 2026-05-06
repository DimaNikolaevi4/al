#!/usr/bin/env bash
# =============================================================================
# Скрипт резервного копирования AI Tutor Project
# Backup Script
# =============================================================================
# Использование:
#   ./backup.sh                           # Резервное копирование (по умолчанию)
#   ./backup.sh --keep 14                 # Хранить 14 копий
#   ./backup.sh --dest /mnt/backups       # Кастомная директория
#   ./backup.sh --components adapters,logs # Только указанные компоненты
#   ./backup.sh --list                    # Показать существующие бекапы
#   ./backup.sh --restore LATEST          # Восстановить из последнего бекапа
#   ./backup.sh --help                    # Помощь
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
step()    { echo -e "\n${CYAN}${BOLD}==> $*${NC}"; "

# ---------------------------------------------------------------------------
# Конфигурация / Configuration
# ---------------------------------------------------------------------------
PROJECT_DIR="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="ai-tutor-backup-${TIMESTAMP}"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.yml"

# Источники резервного копирования
ADAPTERS_DIR="${PROJECT_DIR}/checkpoints"
LOGS_DIR="${PROJECT_DIR}/logs"
ENV_FILE="${PROJECT_DIR}/.env"

# ---------------------------------------------------------------------------
# Парсинг аргументов / Argument parsing
# ---------------------------------------------------------------------------
KEEP_COUNT=7
DEST_DIR="${PROJECT_DIR}/backups"
COMPONENTS="adapters,logs,redis,config"
LIST_ONLY=false
RESTORE_TARGET=""

show_help() {
    cat <<'EOF'
Использование / Usage:
  ./backup.sh [OPTIONS]

Опции / Options:
  --keep N          Количество хранимых резервных копий (по умолчанию: 7)
  --dest PATH       Директория для резервных копий (по умолчанию: ./backups)
  --components LIST Компоненты через запятую (по умолчанию: all)
                    Доступные: adapters, logs, redis, config
  --list            Показать существующие резервные копии
  --restore NAME    Восстановить из копии (или LATEST для последней)
  --help            Показать эту справку

Компоненты / Components:
  adapters   LoRA-адаптеры (checkpoints/)
  logs       Логи приложения (logs/)
  redis      Dump базы данных Redis
  config     Конфигурация (.env)

Примеры:
  ./backup.sh --keep 14 --dest /mnt/backup
  ./backup.sh --components adapters,config
  ./backup.sh --list
  ./backup.sh --restore ai-tutor-backup-20240101_120000
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --keep)       KEEP_COUNT="$2"; shift 2 ;;
        --dest)       DEST_DIR="$2"; shift 2 ;;
        --components) COMPONENTS="$2"; shift 2 ;;
        --list)       LIST_ONLY=true; shift ;;
        --restore)    RESTORE_TARGET="$2"; shift 2 ;;
        --help|-h)    show_help ;;
        *) error "Неизвестный параметр: $1"; echo "Используйте --help"; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Утилиты / Utilities
# ---------------------------------------------------------------------------

# Размер директории в читаемом формате
dir_size() {
    if [[ -d "$1" ]]; then
        du -sh "$1" 2>/dev/null | cut -f1 || echo "0"
    else
        echo "0"
    fi
}

# Создание временной директории для бекапа
TEMP_BACKUP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_BACKUP_DIR"' EXIT

# =============================================================================
# Список бекапов / List backups
# =============================================================================
list_backups() {
    step "Существующие резервные копии"

    if [[ ! -d "$DEST_DIR" ]] || [[ -z "$(ls -A "$DEST_DIR" 2>/dev/null)" ]]; then
        warn "Резервные копии не найдены в ${DEST_DIR}"
        return
    fi

    echo ""
    echo -e "  ${BOLD}Хранилище:${NC} ${DEST_DIR}"
    echo -e "  ${BOLD}Лимит:${NC}    ${KEEP_COUNT} копий"
    echo ""
    printf "  %-40s %-12s %-10s\n" "ИМЯ" "РАЗМЕР" "ДАТА"
    printf "  %-40s %-12s %-10s\n" "----" "------" "----"

    for backup in $(ls -1t "${DEST_DIR}"/ai-tutor-backup-*.tar.gz 2>/dev/null); do
        name=$(basename "$backup")
        size=$(du -h "$backup" | cut -f1)
        # Извлекаем дату из имени
        date_str=$(echo "$name" | grep -oP '\d{8}_\d{6}' | sed 's/_/ /')
        printf "  ${CYAN}%-40s${NC} %-12s %s\n" "$name" "$size" "$date_str"
    done

    local total_size=$(du -sh "$DEST_DIR" | cut -f1)
    echo ""
    info "Общий размер: ${total_size}"
}

# =============================================================================
# Резервное копирование компонентов / Backup components
# =============================================================================

backup_adapters() {
    local dest="$1"
    step "Резервное копирование LoRA-адаптеров"

    if [[ ! -d "$ADAPTERS_DIR" ]] || [[ -z "$(ls -A "$ADAPTERS_DIR" 2>/dev/null)" ]]; then
        warn "Директория adapters пуста или не существует: ${ADAPTERS_DIR}"
        return
    fi

    mkdir -p "${dest}/adapters"
    cp -r "$ADAPTERS_DIR"/* "${dest}/adapters/" 2>/dev/null || true
    local size=$(dir_size "$ADAPTERS_DIR")
    success "LoRA-адаптеры: ${size}"
}

backup_logs() {
    local dest="$1"
    step "Резервное копирование логов"

    local log_dirs=("$LOGS_DIR")
    # Добавляем Docker-логи
    if command -v docker &>/dev/null; then
        mkdir -p "${dest}/docker-logs"
        docker compose -f "$COMPOSE_FILE" logs --no-color > "${dest}/docker-logs/docker-compose.log" 2>/dev/null || true
        log_dirs+=("/var/log/ai-tutor")
    fi

    mkdir -p "${dest}/logs"
    for log_dir in "${log_dirs[@]}"; do
        if [[ -d "$log_dir" ]]; then
            cp -r "$log_dir"/* "${dest}/logs/" 2>/dev/null || true
        fi
    done

    local size=$(dir_size "${dest}/logs")
    success "Логи: ${size}"
}

backup_redis() {
    local dest="$1"
    step "Резервное копирование Redis"

    if ! command -v docker &>/dev/null; then
        warn "Docker не доступен, пропускаем Redis backup"
        return
    fi

    mkdir -p "${dest}/redis"

    # Пытаемся получить RDB dump из контейнера Redis
    local redis_container=$(docker ps --format '{{.Names}}' | grep -i redis | head -1 || true)

    if [[ -n "$redis_container" ]]; then
        # Триггер BGSAVE
        docker exec "$redis_container" redis-cli BGSAVE 2>/dev/null || true
        sleep 2

        # Копируем dump
        docker cp "${redis_container}:/data/dump.rdb" "${dest}/redis/dump.rdb" 2>/dev/null || \
            warn "Не удалось скопировать dump.rdb"

        # Альтернативно: используем redis-cli для экспорта
        docker exec "$redis_container" redis-cli --rdb - > "${dest}/redis/export.rdb" 2>/dev/null || true
    else
        # Локальный Redis
        if command -v redis-cli &>/dev/null; then
            redis-cli BGSAVE 2>/dev/null || true
            sleep 2
            if [[ -f /var/lib/redis/dump.rdb ]]; then
                sudo cp /var/lib/redis/dump.rdb "${dest}/redis/dump.rdb" 2>/dev/null || true
            fi
        else
            warn "Redis не найден, пропускаем"
        fi
    fi

    local size=$(dir_size "${dest}/redis")
    success "Redis dump: ${size}"
}

backup_config() {
    local dest="$1"
    step "Резервное копирование конфигурации"

    mkdir -p "${dest}/config"

    local copied=false

    # .env
    if [[ -f "$ENV_FILE" ]]; then
        cp "$ENV_FILE" "${dest}/config/.env"
        copied=true
    fi

    # docker-compose.yml
    if [[ -f "$COMPOSE_FILE" ]]; then
        cp "$COMPOSE_FILE" "${dest}/config/docker-compose.yml"
        copied=true
    fi

    # Dockerfile
    for df in "${PROJECT_DIR}"/Dockerfile*; do
        [[ -f "$df" ]] && cp "$df" "${dest}/config/" && copied=true
    done

    # requirements.txt
    for req in "${PROJECT_DIR}"/requirements*.txt; do
        [[ -f "$req" ]] && cp "$req" "${dest}/config/" && copied=true
    done

    # Monitoring config
    for mc in "${PROJECT_DIR}"/monitoring/*.yml; do
        [[ -f "$mc" ]] && cp "$mc" "${dest}/config/" && copied=true
    done

    if [[ "$copied" == true ]]; then
        success "Конфигурация скопирована"
    else
        warn "Файлы конфигурации не найдены"
    fi
}

# =============================================================================
# Ротация бекапов / Rotate old backups
# =============================================================================

rotate_backups() {
    step "Ротация: хранить последние ${KEEP_COUNT} копий"

    local count=0
    for backup in $(ls -1t "${DEST_DIR}"/ai-tutor-backup-*.tar.gz 2>/dev/null); do
        count=$((count + 1))
        if [[ $count -gt $KEEP_COUNT ]]; then
            rm -f "$backup"
            info "Удалена старая копия: $(basename "$backup")"
        fi
    done

    success "Ротация завершена (хранится: ${count} из ${KEEP_COUNT})"
}

# =============================================================================
# Восстановление / Restore
# =============================================================================

perform_restore() {
    local target="$1"

    step "Восстановление из резервной копии: ${target}"

    if [[ "$target" == "LATEST" ]]; then
        target=$(ls -1t "${DEST_DIR}"/ai-tutor-backup-*.tar.gz 2>/dev/null | head -1)
        if [[ -z "$target" ]]; then
            error "Резервные копии не найдены!"
            exit 1
        fi
    fi

    if [[ ! -f "$target" ]]; then
        error "Файл не найден: $target"
        exit 1
    fi

    info "Источник: ${target}"
    warn "ВНИМАНИЕ: Это перезапишет текущие данные!"

    read -rp "Продолжить? [y/N]: " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        info "Отменено"
        exit 0
    fi

    # Распаковка во временную директорию
    local restore_dir=$(mktemp -d)
    tar -xzf "$target" -C "$restore_dir"

    info "Файлы в копии:"
    ls -la "$restore_dir/"

    # Восстановление компонентов
    if [[ -d "${restore_dir}/adapters" ]]; then
        mkdir -p "$ADAPTERS_DIR"
        cp -r "${restore_dir}/adapters"/* "$ADAPTERS_DIR/" 2>/dev/null || true
        success "LoRA-адаптеры восстановлены"
    fi

    if [[ -f "${restore_dir}/config/.env" ]]; then
        cp "${restore_dir}/config/.env" "$ENV_FILE"
        success "Конфигурация (.env) восстановлена"
    fi

    if [[ -d "${restore_dir}/redis" ]]; then
        local redis_container=$(docker ps --format '{{.Names}}' | grep -i redis | head -1 || true)
        if [[ -n "$redis_container" ]]; then
            docker cp "${restore_dir}/redis/dump.rdb" "${redis_container}:/data/dump.rdb" 2>/dev/null || true
            docker restart "$redis_container" 2>/dev/null || true
            success "Redis восстановлен (контейнер перезапущен)"
        fi
    fi

    # Очистка
    rm -rf "$restore_dir"

    echo ""
    success "Восстановление завершено из: $(basename "$target")"
    warn "Перезапустите сервисы: docker compose restart"
    exit 0
}

# =============================================================================
# Основной поток / Main flow
# =============================================================================

# Список бекапов
if [[ "$LIST_ONLY" == true ]]; then
    list_backups
    exit 0
fi

# Восстановление
if [[ -n "$RESTORE_TARGET" ]]; then
    perform_restore "$RESTORE_TARGET"
    exit 0
fi

# Полное резервное копирование
step "Создание резервной копии: ${BACKUP_NAME}"

# Создаём директорию назначения
mkdir -p "$DEST_DIR"

# Парсинг компонентов
IFS=',' read -ra COMP_ARRAY <<< "$COMPONENTS"
for comp in "${COMP_ARRAY[@]}"; do
    comp=$(echo "$comp" | xargs)  # trim whitespace
    case "$comp" in
        adapters) backup_adapters "$TEMP_BACKUP_DIR" ;;
        logs)     backup_logs "$TEMP_BACKUP_DIR" ;;
        redis)    backup_redis "$TEMP_BACKUP_DIR" ;;
        config)   backup_config "$TEMP_BACKUP_DIR" ;;
        all|"")
            backup_adapters "$TEMP_BACKUP_DIR"
            backup_logs "$TEMP_BACKUP_DIR"
            backup_redis "$TEMP_BACKUP_DIR"
            backup_config "$TEMP_BACKUP_DIR"
            break
            ;;
        *) warn "Неизвестный компонент: ${comp} (пропускаем)" ;;
    esac
done

# Создаём метаданные
cat > "${TEMP_BACKUP_DIR}/backup-info.txt" <<META
AI Tutor Backup
===============
Date:       $(date -Iseconds)
Hostname:   $(hostname)
Project:    ${PROJECT_DIR}
Components: ${COMPONENTS}
Compressor: gzip
META

# Архивация
step "Сжатие архива"

ARCHIVE_PATH="${DEST_DIR}/${BACKUP_NAME}.tar.gz"
tar -czf "$ARCHIVE_PATH" -C "$TEMP_BACKUP_DIR" .

if [[ -f "$ARCHIVE_PATH" ]]; then
    ARCHIVE_SIZE=$(du -h "$ARCHIVE_PATH" | cut -f1)
    success "Архив создан: ${ARCHIVE_PATH} (${ARCHIVE_SIZE})"
else
    error "Не удалось создать архив!"
    exit 1
fi

# Ротация
rotate_backups

# MD5 чексумма
if command -v md5sum &>/dev/null; then
    md5sum "$ARCHIVE_PATH" > "${ARCHIVE_PATH}.md5"
    success "Контрольная сумма: $(basename "${ARCHIVE_PATH}.md5")"
fi

# Итог
echo ""
echo -e "${GREEN}${BOLD}========================================${NC}"
echo -e "${GREEN}${BOLD}  Резервное копирование завершено!      ${NC}"
echo -e "${GREEN}${BOLD}========================================${NC}"
echo ""
echo -e "  💾 Архив:  ${CYAN}${ARCHIVE_PATH}${NC}"
echo -e "  📏 Размер: ${ARCHIVE_SIZE}"
echo -e "  📋 Компоненты: ${COMPONENTS}"
echo -e "  🔄 Хранение: ${KEEP_COUNT} копий"
echo ""
echo -e "  📂 Восстановление:"
echo -e "     ./backup.sh --restore ${BACKUP_NAME}"
echo -e "     ./backup.sh --restore LATEST"
echo ""
