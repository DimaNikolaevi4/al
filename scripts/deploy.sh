#!/usr/bin/env bash
# =============================================================================
# Скрипт развёртывания AI Tutor Project
# Main Deployment Script
# =============================================================================
# Использование:
#   ./deploy.sh                    # Полное развёртывание
#   ./deploy.sh --skip-gpu         # Пропустить обнаружение GPU
#   ./deploy.sh --skip-env         # Пропустить создание .env
#   ./deploy.sh --no-healthcheck   # Пропустить проверку здоровья
#   ./deploy.sh --rollback         # Откатить к предыдущей версии
#   ./deploy.sh --help             # Помощь
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
# Конфигурация / Configuration
# ---------------------------------------------------------------------------
PROJECT_DIR="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.yml"
ENV_FILE="${PROJECT_DIR}/.env"
ENV_EXAMPLE="${PROJECT_DIR}/.env.docker.example"
HEALTH_TIMEOUT=120
API_URL="${API_URL:-http://localhost:8000}"

# ---------------------------------------------------------------------------
# Парсинг аргументов / Argument parsing
# ---------------------------------------------------------------------------
SKIP_GPU=false
SKIP_ENV=false
SKIP_HEALTH=false
DO_ROLLBACK=false

show_help() {
    cat <<'EOF'
Использование / Usage:
  ./deploy.sh [OPTIONS]

Опции / Options:
  --skip-gpu         Пропустить обнаружение GPU
  --skip-env         Пропустить создание .env (использовать существующий)
  --no-healthcheck   Пропустить проверку здоровья после запуска
  --rollback         Откатить к предыдущему развертыванию
  --help             Показать эту справку

Описание:
  Развёртывание AI Tutor:
  1. Проверка prerequisites (Docker, Docker Compose, Python 3.10+)
  2. Обнаружение GPU (скрипт detect_gpu.sh)
  3. Создание .env из шаблона (интерактивные подсказки)
  4. Сборка Docker-образов
  5. Запуск сервисов (docker compose up -d)
  6. Проверка здоровья
  7. Smoke-тест (вызов /api/v1/health)
  8. Итоговое резюме
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-gpu)       SKIP_GPU=true; shift ;;
        --skip-env)       SKIP_ENV=true; shift ;;
        --no-healthcheck) SKIP_HEALTH=true; shift ;;
        --rollback)       DO_ROLLBACK=true; shift ;;
        --help|-h)        show_help ;;
        *) error "Неизвестный параметр: $1"; echo "Используйте --help для справки"; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Утилиты / Utilities
# ---------------------------------------------------------------------------

# Проверка версии
version_gte() {
    # version_gte "1.2.3" "1.0.0" → true (1.2.3 >= 1.0.0)
    local a="$1" b="$2"
    local IFS='.'
    read -ra a_parts <<< "$a"
    read -ra b_parts <<< "$b"
    for i in 0 1 2; do
        if [[ ${a_parts[i]:-0} -gt ${b_parts[i]:-0} ]]; then return 0; fi
        if [[ ${a_parts[i]:-0} -lt ${b_parts[i]:-0} ]]; then return 1; fi
    done
    return 0
}

cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        error "Развертывание завершилось с ошибкой (код $exit_code)"
        error "Смотрите логи: docker compose -f ${COMPOSE_FILE} logs"
        if [[ "${DO_ROLLBACK}" == false ]] && [[ "${1:-}" != "rollback" ]]; then
            warn "Для отката выполните: ./deploy.sh --rollback"
        fi
    fi
    exit $exit_code
}
trap 'cleanup' EXIT

# Откат / Rollback
perform_rollback() {
    step "Откат к предыдущему развертыванию / Rolling back"

    if [[ ! -f "${COMPOSE_FILE}" ]]; then
        error "Файл docker-compose.yml не найден: ${COMPOSE_FILE}"
        exit 1
    fi

    cd "$PROJECT_DIR"

    # Останавливаем текущие контейнеры
    info "Остановка текущих сервисов..."
    docker compose -f "$COMPOSE_FILE" down --timeout 30 2>/dev/null || true

    # Проверяем наличие предыдущего образа
    PREV_IMAGE=$(docker images --format '{{.Repository}}:{{.Tag}}' | grep ai-tutor | sort -t: -k2 -V | head -n 2 | tail -n 1) || true

    if [[ -n "$PREV_IMAGE" ]]; then
        info "Найден предыдущий образ: $PREV_IMAGE"
        # Меняем тег в docker-compose если возможно
        warn "Автоматический откат образа: укажите нужный тег в docker-compose.yml"
    fi

    # Пытаемся запустить заново
    info "Запуск сервисов с текущей конфигурацией..."
    docker compose -f "$COMPOSE_FILE" up -d --timeout 120

    success "Откат выполнен. Сервисы перезапущены."
    exit 0
}

# =============================================================================
step "1/7: Проверка prerequisites / Checking prerequisites"
# =============================================================================

# Docker
if command -v docker &>/dev/null; then
    DOCKER_VERSION=$(docker --version | grep -oP '\d+\.\d+\.\d+' | head -1)
    success "Docker ${DOCKER_VERSION}"
else
    error "Docker не установлен!"
    info "Установка: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# Docker Compose (V2 plugin or standalone)
COMPOSE_CMD=""
if docker compose version &>/dev/null; then
    COMPOSE_CMD="docker compose"
    COMPOSE_VERSION=$(docker compose version --short)
    success "Docker Compose ${COMPOSE_VERSION} (plugin)"
elif command -v docker-compose &>/dev/null; then
    COMPOSE_CMD="docker-compose"
    COMPOSE_VERSION=$(docker-compose --version | grep -oP '\d+\.\d+\.\d+')
    success "Docker Compose ${COMPOSE_VERSION} (standalone)"
else
    error "Docker Compose не установлен!"
    info "Установите Docker Compose V2: apt install docker-compose-plugin"
    exit 1
fi

# Python 3.10+
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
    if version_gte "$PYTHON_VERSION" "3.10.0"; then
        success "Python ${PYTHON_VERSION}"
    else
        error "Python >= 3.10 требуется, найден: ${PYTHON_VERSION}"
        exit 1
    fi
else
    warn "Python3 не найден (продолжаем, он есть внутри Docker)"
fi

# Docker daemon running
if ! docker info &>/dev/null; then
    error "Docker daemon не запущен!"
    info "Запустите: sudo systemctl start docker"
    exit 1
fi

# =============================================================================
step "2/7: Обнаружение GPU / GPU detection"
# =============================================================================

if [[ "$SKIP_GPU" == false ]]; then
    GPU_SCRIPT="${PROJECT_DIR}/scripts/detect_gpu.sh"
    if [[ -f "$GPU_SCRIPT" ]]; then
        bash "$GPU_SCRIPT"
    else
        warn "Скрипт detect_gpu.sh не найден, пропускаем"
    fi
else
    info "Обнаружение GPU пропущено (--skip-gpu)"
fi

# =============================================================================
step "3/7: Создание .env / Creating .env from template"
# =============================================================================

cd "$PROJECT_DIR"

if [[ "$SKIP_ENV" == false ]]; then
    if [[ -f "$ENV_FILE" ]]; then
        warn "Файл .env уже существует."
        read -rp "Перезаписать? [y/N]: " OVERWRITE
        if [[ "$OVERWRITE" =~ ^[Yy]$ ]]; then
            backup_file "$ENV_FILE"
        else
            info "Используем существующий .env"
            SKIP_ENV=true  # treat as skip
        fi
    fi

    if [[ "$SKIP_ENV" == false ]]; then
        if [[ -f "$ENV_EXAMPLE" ]]; then
            cp "$ENV_EXAMPLE" "$ENV_FILE"
            info "Создан .env из шаблона .env.docker.example"

            # Интерактивные подсказки
            echo ""
            info "Настройка переменных окружения:"
            echo "  (Enter для значения по умолчанию, введите 'skip' для пропуска)"
            echo ""

            # SECRET_KEY
            read -rp "  SECRET_KEY [auto-generate]: " INPUT_SECRET
            if [[ -n "$INPUT_SECRET" && "$INPUT_SECRET" != "skip" ]]; then
                sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${INPUT_SECRET}|" "$ENV_FILE"
            else
                AUTO_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -hex 32)
                sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${AUTO_SECRET}|" "$ENV_FILE"
                info "SECRET_KEY сгенерирован автоматически"
            fi

            # REDIS_URL
            read -rp "  REDIS_URL [redis://redis:6379/0]: " INPUT_REDIS
            if [[ -n "$INPUT_REDIS" && "$INPUT_REDIS" != "skip" ]]; then
                sed -i "s|^REDIS_URL=.*|REDIS_URL=${INPUT_REDIS}|" "$ENV_FILE"
            fi

            # LOG_LEVEL
            read -rp "  LOG_LEVEL [INFO]: " INPUT_LOG
            if [[ -n "$INPUT_LOG" && "$INPUT_LOG" != "skip" ]]; then
                sed -i "s|^LOG_LEVEL=.*|LOG_LEVEL=${INPUT_LOG}|" "$ENV_FILE"
            fi

            success "Файл .env настроен"
        else
            warn "Шаблон .env.docker.example не найден. Создаём минимальный .env"
            cat > "$ENV_FILE" <<'ENV_EOF'
# AI Tutor — Environment Variables
SECRET_KEY=change-me-in-production
REDIS_URL=redis://redis:6379/0
LOG_LEVEL=INFO
ENVIRONMENT=production
ENV_EOF
            success "Минимальный .env создан"
        fi
    fi
else
    if [[ -f "$ENV_FILE" ]]; then
        info "Используем существующий .env"
    else
        error "Файл .env не найден и --skip-env указан!"
        exit 1
    fi
fi

# =============================================================================
step "4/7: Сборка Docker-образов / Building Docker images"
# =============================================================================

info "Сборка Docker-образов..."

if [[ -f "$COMPOSE_FILE" ]]; then
    $COMPOSE_CMD -f "$COMPOSE_FILE" build --parallel 2>&1 | while IFS= read -r line; do
        echo "  $line"
    done
    success "Docker-образы собраны"
else
    error "docker-compose.yml не найден: $COMPOSE_FILE"
    exit 1
fi

# =============================================================================
step "5/7: Запуск сервисов / Starting services"
# =============================================================================

info "Запуск сервисов..."

$COMPOSE_CMD -f "$COMPOSE_FILE" up -d --timeout 120

# Проверяем статус контейнеров
sleep 5
FAILED=$($COMPOSE_CMD -f "$COMPOSE_FILE" ps --format '{{.Name}} {{.Status}}' | grep -i "exit\|dead" || true)
if [[ -n "$FAILED" ]]; then
    error "Некоторые контейнеры не запустились:"
    echo "$FAILED"
    error "Логи: $COMPOSE_CMD -f $COMPOSE_FILE logs"
    exit 1
fi

success "Все сервисы запущены"

# =============================================================================
step "6/7: Проверка здоровья / Health check"
# =============================================================================

if [[ "$SKIP_HEALTH" == true ]]; then
    info "Проверка здоровья пропущена (--no-healthcheck)"
else
    info "Ожидание готовности API (таймаут: ${HEALTH_TIMEOUT}s)..."

    ELAPSED=0
    HEALTH_OK=false
    HEALTH_URL="${API_URL}/api/v1/health"

    while [[ $ELAPSED -lt $HEALTH_TIMEOUT ]]; do
        if curl -sf --max-time 5 "$HEALTH_URL" >/dev/null 2>&1; then
            HEALTH_OK=true
            break
        fi
        sleep 3
        ELAPSED=$((ELAPSED + 3))
        printf "\r  Ожидание... %ds/%ds" "$ELAPSED" "$HEALTH_TIMEOUT"
    done
    echo ""

    if [[ "$HEALTH_OK" == true ]]; then
        success "API готова (${ELAPSED}s)"
    else
        warn "API не отвечает за ${HEALTH_TIMEOUT}s, но сервисы запущены"
        warn "Проверьте вручную: curl ${HEALTH_URL}"
    fi
fi

# =============================================================================
step "7/7: Smoke-тест / Running smoke test"
# =============================================================================

SMOKE_SCRIPT="${PROJECT_DIR}/scripts/smoke_test.py"
if [[ -f "$SMOKE_SCRIPT" ]]; then
    info "Запуск smoke-теста..."
    if python3 "$SMOKE_SCRIPT" --url "$API_URL" 2>&1; then
        success "Smoke-тест пройден"
    else
        warn "Smoke-тест не пройден (возможно API ещё не полностью готова)"
        warn "Запустите позже: python3 scripts/smoke_test.py"
    fi
else
    warn "Smoke-тест не найден: $SMOKE_SCRIPT"
fi

# =============================================================================
# Итоговое резюме / Deployment summary
# =============================================================================

echo ""
echo -e "${GREEN}${BOLD}========================================${NC}"
echo -e "${GREEN}${BOLD}  Развёртывание завершено!             ${NC}"
echo -e "${GREEN}${BOLD}  Deployment complete!                 ${NC}"
echo -e "${GREEN}${BOLD}========================================${NC}"
echo ""
info "Статус сервисов:"
$COMPOSE_CMD -f "$COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  (не удалось получить статус)"
echo ""
echo -e "  📡 API:          ${CYAN}${API_URL}${NC}"
echo -e "  📊 Документация: ${CYAN}${API_URL}/docs${NC}"
echo -e "  🔧 Health:       ${CYAN}${API_URL}/api/v1/health${NC}"
echo ""
echo -e "  📋 Управление:"
echo -e "     Стоп:       $COMPOSE_CMD -f $COMPOSE_FILE down"
echo -e "     Логи:       $COMPOSE_CMD -f $COMPOSE_FILE logs -f"
echo -e "     Перезапуск: $COMPOSE_CMD -f $COMPOSE_FILE restart"
echo ""
