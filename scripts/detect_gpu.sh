#!/bin/bash
#
# detect_gpu.sh — Универсальный скрипт обнаружения GPU
# Проект: AI Tutor
# Описание: Определяет вендора GPU, модель, проверяет установленные драйверы
#           и рекомендует соответствующий гайд по настройке.
#
# Использование:
#   ./detect_gpu.sh
#   ./detect_gpu.sh --json    (вывод в формате JSON-подобной структуры)
#

set -euo pipefail

# ─── Цвета для вывода ───────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'  # No Color

# ─── Функции ────────────────────────────────────────────────────────────────

print_header() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}           ${BOLD}🤖 AI Tutor — Детектор GPU${NC}                               ${BLUE}║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_section() {
    echo -e "${CYAN}── $1 ──${NC}"
}

print_ok() {
    echo -e "  ${GREEN}✅ $1${NC}"
}

print_warn() {
    echo -e "  ${YELLOW}⚠️  $1${NC}"
}

print_err() {
    echo -e "  ${RED}❌ $1${NC}"
}

print_info() {
    echo -e "  ${BLUE}ℹ️  $1${NC}"
}

# Проверка зависимостей
check_dependencies() {
    print_section "Проверка зависимостей скрипта"

    local missing=()

    if ! command -v lspci &>/dev/null; then
        missing+=("lspci")
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        print_err "Не найдены утилиты: ${missing[*]}"
        echo -e "  ${YELLOW}Установите: sudo apt install pciutils${NC}"
        exit 1
    fi

    print_ok "Все зависимости доступны (lspci)"
}

# Обнаружение GPU через lspci
detect_gpu_pci() {
    print_section "Обнаружение GPU (PCI)"

    # Ищем VGA-совместимые контроллеры
    local gpus
    gpus=$(lspci -nn | grep -iE '\[0300\]|\[0302\]|\[0301\]' || true)

    # Также ищем 3D-контроллеры (некоторые NVIDIA отображаются так)
    local gpus_3d
    gpus_3d=$(lspci -nn | grep -i '3d controller' || true)

    if [ -z "$gpus" ] && [ -z "$gpus_3d" ]; then
        print_warn "GPU не обнаружен через lspci"
        echo ""
        print_info "Возможные причины:"
        echo "    • GPU физически не установлена"
        echo "    • Драйвер PCI не загружен"
        echo "    • Виртуальная машина без GPU passthrough"
        return 1
    fi

    local combined="${gpus}"
    if [ -n "$gpus_3d" ]; then
        combined="${combined}"$'\n'"${gpus_3d}"
    fi

    # Определяем вендора и модель
    GPU_VENDOR="UNKNOWN"
    GPU_MODEL="Неизвестно"
    GPU_PCI_ID=""

    if echo "$combined" | grep -qi "nvidia"; then
        GPU_VENDOR="NVIDIA"
        GPU_MODEL=$(echo "$combined" | grep -i nvidia | head -1 | sed 's/.*: //' | sed 's/ (rev.*//')
        GPU_PCI_ID=$(echo "$combined" | grep -i nvidia | head -1 | grep -oP '\[\S+\]')

        print_ok "Обнаружен GPU: ${BOLD}${GPU_MODEL}${NC}"
        print_info "Вендор: ${GPU_VENDOR}"
        print_info "PCI ID: ${GPU_PCI_ID}"

    elif echo "$combined" | grep -qi "amd\|advanced micro devices\|radeon"; then
        GPU_VENDOR="AMD"
        GPU_MODEL=$(echo "$combined" | grep -iE 'amd|radeon' | head -1 | sed 's/.*: //' | sed 's/ (rev.*//')
        GPU_PCI_ID=$(echo "$combined" | grep -iE 'amd|radeon' | head -1 | grep -oP '\[\S+\]')

        print_ok "Обнаружен GPU: ${BOLD}${GPU_MODEL}${NC}"
        print_info "Вендор: ${GPU_VENDOR}"
        print_info "PCI ID: ${GPU_PCI_ID}"

    elif echo "$combined" | grep -qi "intel"; then
        GPU_VENDOR="Intel"
        GPU_MODEL=$(echo "$combined" | grep -i intel | head -1 | sed 's/.*: //' | sed 's/ (rev.*//')

        print_ok "Обнаружен GPU: ${BOLD}${GPU_MODEL}${NC}"
        print_info "Вендор: ${GPU_VENDOR} (интегрированная графика)"
        print_warn "Intel GPU не поддерживается для CUDA/ROCm. Рекомендуется CPU-only установка."

    else
        GPU_VENDOR="UNKNOWN"
        GPU_MODEL=$(echo "$combined" | head -1 | sed 's/.*: //' | sed 's/ (rev.*//')
        print_warn "GPU обнаружен, но вендор не определён: ${GPU_MODEL}"
    fi

    return 0
}

# Проверка драйверов NVIDIA
check_nvidia_drivers() {
    print_section "Проверка драйверов NVIDIA"

    # Проверяем nvidia-smi
    if command -v nvidia-smi &>/dev/null; then
        local driver_version
        driver_version=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1)
        local cuda_version
        cuda_version=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1) # placeholder
        cuda_version=$(nvidia-smi 2>/dev/null | grep "CUDA Version" | awk '{print $9}' || echo "N/A")

        print_ok "Драйвер NVIDIA установлен"
        echo -e "    Версия драйвера: ${BOLD}${driver_version}${NC}"
        echo -e "    CUDA Version:    ${BOLD}${cuda_version}${NC}"

        # Информация о GPU
        echo ""
        echo -e "    ${BOLD}Информация о GPU:${NC}"
        nvidia-smi --query-gpu=name,memory.total,memory.free,temperature.gpu --format=csv,noheader 2>/dev/null \
            | while IFS=',' read -r name mem_total mem_free temp; do
                echo "    • GPU: $(echo "$name" | xargs)"
                echo "      VRAM: $(echo "$mem_total" | xargs) (свободно: $(echo "$mem_free" | xargs))"
                echo "      Температура: $(echo "$temp" | xargs)"
            done

        NVIDIA_DRIVER_INSTALLED=true

        # Проверяем nvcc (CUDA Toolkit)
        if command -v nvcc &>/dev/null; then
            local nvcc_version
            nvcc_version=$(nvcc --version 2>/dev/null | grep "release" | sed 's/.*release //' | sed 's/,.*//')
            echo -e "    CUDA Toolkit (nvcc): ${BOLD}${nvcc_version}${NC}"
            CUDA_TOOLKIT_INSTALLED=true
        else
            print_warn "CUDA Toolkit (nvcc) не найден"
            CUDA_TOOLKIT_INSTALLED=false
        fi

        # Проверяем cuDNN
        if [ -f /usr/local/cuda/include/cudnn_version.h ]; then
            local cudnn_major cudnn_minor cudnn_patch
            cudnn_major=$(grep "CUDNN_MAJOR" /usr/local/cuda/include/cudnn_version.h 2>/dev/null | awk '{print $3}' || echo "?")
            cudnn_minor=$(grep "CUDNN_MINOR" /usr/local/cuda/include/cudnn_version.h 2>/dev/null | awk '{print $3}' || echo "?")
            cudnn_patch=$(grep "CUDNN_PATCHLEVEL" /usr/local/cuda/include/cudnn_version.h 2>/dev/null | awk '{print $3}' || echo "?")
            echo -e "    cuDNN: ${BOLD}${cudnn_major}.${cudnn_minor}.${cudnn_patch}${NC}"
        else
            print_warn "cuDNN не найден (не критично для базового запуска)"
        fi

    else
        print_err "Драйвер NVIDIA НЕ установлен"
        NVIDIA_DRIVER_INSTALLED=false
        CUDA_TOOLKIT_INSTALLED=false
    fi
}

# Проверка драйверов AMD / ROCm
check_amd_drivers() {
    print_section "Проверка драйверов AMD / ROCm"

    # Проверяем amdgpu драйвер ядра
    if lsmod | grep -q "amdgpu"; then
        print_ok "Модуль ядра amdgpu загружен"
    else
        print_warn "Модуль ядра amdgpu НЕ загружен"
    fi

    # Проверяем rocm-smi
    ROCM_INSTALLED=false

    if command -v rocm-smi &>/dev/null; then
        print_ok "ROCm установлен (rocm-smi найден)"

        echo ""
        echo -e "    ${BOLD}Информация о GPU (rocm-smi):${NC}"
        rocm-smi --showproductname 2>/dev/null | tail -n +2 | head -5 | sed 's/^/    /' || true

        ROCM_INSTALLED=true

        # Проверяем rocminfo
        if command -v rocminfo &>/dev/null; then
            local gfx_version
            gfx_version=$(rocminfo 2>/dev/null | grep -oP 'gfx[a-z0-9]+' | head -1 || echo "не определена")
            echo -e "    GFX Архитектура: ${BOLD}${gfx_version}${NC}"
        fi

    elif [ -x /opt/rocm/bin/rocm-smi ]; then
        print_warn "ROCm установлен, но не добавлен в PATH"
        echo -e "    Запустите: ${YELLOW}export PATH=/opt/rocm/bin:\$PATH${NC}"
        ROCM_INSTALLED=true
    else
        print_err "ROCm НЕ установлен"
    fi

    # Проверяем HSA_OVERRIDE_GFX_VERSION
    if [ -n "${HSA_OVERRIDE_GFX_VERSION:-}" ]; then
        print_warn "HSA_OVERRIDE_GFX_VERSION=${HSA_OVERRIDE_GFX_VERSION} (GPU не официально поддерживается ROCm)"
    fi
}

# Проверка Docker
check_docker() {
    print_section "Проверка Docker"

    if command -v docker &>/dev/null; then
        local docker_version
        docker_version=$(docker --version 2>/dev/null)
        print_ok "Docker установлен: ${docker_version}"

        # Docker Compose
        if docker compose version &>/dev/null; then
            local compose_version
            compose_version=$(docker compose version 2>/dev/null)
            print_ok "Docker Compose: ${compose_version}"
        elif command -v docker-compose &>/dev/null; then
            print_ok "Docker Compose (standalone): $(docker-compose --version 2>/dev/null)"
        else
            print_warn "Docker Compose не найден"
        fi

        # NVIDIA Container Toolkit
        if command -v nvidia-container-runtime &>/dev/null || command -v nvidia-ctk &>/dev/null; then
            print_ok "NVIDIA Container Toolkit установлен"
        elif [ "$GPU_VENDOR" = "NVIDIA" ]; then
            print_warn "NVIDIA Container Toolkit не установлен (нужен для Docker+GPU)"
        fi

    else
        print_warn "Docker не установлен"
    fi
}

# Проверка Python + PyTorch
check_python_pytorch() {
    print_section "Проверка Python и PyTorch"

    # Ищем python3
    local python_cmd=""
    if command -v python3 &>/dev/null; then
        python_cmd="python3"
    elif command -v python &>/dev/null; then
        python_cmd="python"
    fi

    if [ -z "$python_cmd" ]; then
        print_err "Python не найден"
        return
    fi

    local py_version
    py_version=$($python_cmd --version 2>&1 || echo "неизвестно")
    echo -e "    Python: ${BOLD}${py_version}${NC}"

    # Проверяем PyTorch
    if $python_cmd -c "import torch" 2>/dev/null; then
        local pt_version
        pt_version=$($python_cmd -c "import torch; print(torch.__version__)" 2>/dev/null)
        echo -e "    PyTorch: ${BOLD}${pt_version}${NC}"

        # Проверяем доступность GPU
        local cuda_available
        cuda_available=$($python_cmd -c "print(torch.cuda.is_available())" 2>/dev/null)

        if [ "$cuda_available" = "True" ]; then
            local gpu_name
            gpu_name=$($python_cmd -c "print(torch.cuda.get_device_name(0))" 2>/dev/null)
            print_ok "PyTorch видит GPU: ${gpu_name}"

            local cuda_version
            cuda_version=$($python_cmd -c "print(torch.version.cuda)" 2>/dev/null)
            echo -e "    PyTorch CUDA: ${BOLD}${cuda_version}${NC}"
        else
            # Проверяем MPS (macOS)
            local mps_available
            mps_available=$($python_cmd -c "print(torch.backends.mps.is_available())" 2>/dev/null)
            if [ "$mps_available" = "True" ]; then
                print_ok "PyTorch использует MPS (Metal Performance Shaders — macOS)"
            else
                print_warn "PyTorch установлен, но GPU недоступен"
                echo -e "    torch.cuda.is_available() = ${RED}${cuda_available}${NC}"
                print_info "Возможные решения:"
                if [ "$GPU_VENDOR" = "NVIDIA" ]; then
                    echo "      • Установите PyTorch с CUDA: pip install torch --index-url https://download.pytorch.org/whl/cu121"
                    echo "      • Проверьте драйвер NVIDIA: nvidia-smi"
                elif [ "$GPU_VENDOR" = "AMD" ]; then
                    echo "      • Установите PyTorch с ROCm: pip install torch --index-url https://download.pytorch.org/whl/rocm6.0"
                    echo "      • Проверьте ROCm: rocm-smi"
                    echo "      • Попробуйте: export HSA_OVERRIDE_GFX_VERSION=10.3.0"
                fi
            fi
        fi
    else
        print_warn "PyTorch не установлен"
    fi
}

# Проверка групп пользователя
check_user_groups() {
    print_section "Группы пользователя"

    local user_groups
    user_groups=$(groups 2>/dev/null || echo "не удалось определить")
    echo -e "    Группы: ${user_groups}"

    if [ "$GPU_VENDOR" = "NVIDIA" ]; then
        # Для NVIDIA обычно не нужна специальная группа
        :
    elif [ "$GPU_VENDOR" = "AMD" ]; then
        if echo "$user_groups" | grep -q "video"; then
            print_ok "Пользователь в группе video"
        else
            print_err "Пользователь НЕ в группе video (нужно для ROCm)"
            echo -e "    Исправление: ${YELLOW}sudo usermod -aG video \$USER${NC}"
        fi

        if echo "$user_groups" | grep -q "render"; then
            print_ok "Пользователь в группе render"
        else
            print_warn "Пользователь НЕ в группе render (рекомендуется для ROCm)"
            echo -e "    Исправление: ${YELLOW}sudo usermod -aG render \$USER${NC}"
        fi
    fi
}

# Рекомендации
print_recommendations() {
    echo ""
    print_section "РЕКОМЕНДАЦИИ"

    local docs_dir
    docs_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/docs"

    echo ""
    case "$GPU_VENDOR" in
        NVIDIA)
            if [ "${NVIDIA_DRIVER_INSTALLED:-false}" = "true" ] && [ "${CUDA_TOOLKIT_INSTALLED:-false}" = "true" ]; then
                print_ok "Система полностью готова к работе с NVIDIA CUDA!"
                echo ""
                print_info "Ваш гайд по настройке:"
                echo -e "    📄 ${CYAN}${docs_dir}/setup_nvidia.md${NC}"
            elif [ "${NVIDIA_DRIVER_INSTALLED:-false}" = "true" ]; then
                print_warn "Драйвер установлен, но CUDA Toolkit не найден"
                echo ""
                print_info "Следуйте шагам 3-4 из гайда:"
                echo -e "    📄 ${CYAN}${docs_dir}/setup_nvidia.md${NC}"
            else
                print_err "Система не готова к работе с NVIDIA CUDA"
                echo ""
                print_info "Выполните полную настройку по гайду:"
                echo -e "    📄 ${CYAN}${docs_dir}/setup_nvidia.md${NC}"
                echo ""
                echo -e "    Быстрый старт:"
                echo -e "    ${YELLOW}cat ~/setup_nvidia.sh | bash && sudo reboot${NC}"
            fi
            ;;
        AMD)
            if [ "${ROCM_INSTALLED:-false}" = "true" ]; then
                print_ok "ROCm установлен! Проверьте PyTorch выше."
                echo ""
                print_info "Ваш гайд по настройке:"
                echo -e "    📄 ${CYAN}${docs_dir}/setup_amd.md${NC}"
            else
                print_err "ROCm не установлен"
                echo ""
                print_info "Выполните полную настройку по гайду:"
                echo -e "    📄 ${CYAN}${docs_dir}/setup_amd.md${NC}"
                echo ""
                echo -e "    Быстрый старт:"
                echo -e "    ${YELLOW}cat ~/setup_amd.sh | bash${NC}"
                echo -e "    ${YELLOW}# затем ВЫЙДИТЕ и ВОЙДИТЕ ЗАНОВО${NC}"
            fi
            ;;
        Intel)
            print_warn "Intel GPU обнаружена — CUDA/ROCm не поддерживаются"
            echo ""
            print_info "Для AI Tutor рекомендуется:"
            echo "    • Установить NVIDIA GPU (любая карта с 8+ ГБ VRAM)"
            echo "    • Или использовать CPU-only режим (медленнее)"
            ;;
        UNKNOWN)
            print_err "GPU не обнаружена или вендор не определён"
            echo ""
            print_info "Возможные действия:"
            echo "    • Проверьте физическое подключение GPU"
            echo "    • Выполните: lspci | grep -iE 'vga|3d|display'"
            echo "    • Если GPU установлена — обновите PCI database:"
            echo "      sudo update-pciids"
            ;;
    esac
}

# Итоговое резюме
print_summary() {
    echo ""
    echo -e "${BLUE}══════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD} Итоговое резюме:${NC}"
    echo ""
    echo -e "  Вендор GPU:    ${BOLD}${GPU_VENDOR}${NC}"
    echo -e "  Модель GPU:    ${BOLD}${GPU_MODEL}${NC}"
    echo -e "  Вендор драйвера: ${BOLD}$(if [ "$GPU_VENDOR" = "NVIDIA" ] && [ "${NVIDIA_DRIVER_INSTALLED:-false}" = "true" ]; then echo "Установлен"; elif [ "$GPU_VENDOR" = "AMD" ] && [ "${ROCM_INSTALLED:-false}" = "true" ]; then echo "ROCm установлен"; else echo "Не установлен"; fi)${NC}"
    echo ""
    echo -e "${BLUE}══════════════════════════════════════════════════════════════════════${NC}"
}

# ─── Основная логика ────────────────────────────────────────────────────────

# Глобальные переменные
GPU_VENDOR="UNKNOWN"
GPU_MODEL="Неизвестно"
GPU_PCI_ID=""
NVIDIA_DRIVER_INSTALLED=false
CUDA_TOOLKIT_INSTALLED=false
ROCM_INSTALLED=false

# Проверяем флаг --json
JSON_MODE=false
if [ "${1:-}" = "--json" ]; then
    JSON_MODE=true
fi

if [ "$JSON_MODE" = true ]; then
    # Минимальный вывод для скриптов
    detect_gpu_pci 2>/dev/null || true
    check_nvidia_drivers 2>/dev/null || true
    check_amd_drivers 2>/dev/null || true
    echo "{\"vendor\":\"${GPU_VENDOR}\",\"model\":\"${GPU_MODEL}\",\"nvidia_driver\":${NVIDIA_DRIVER_INSTALLED},\"rocm\":${ROCM_INSTALLED}}"
    exit 0
fi

# Полный интерактивный вывод
print_header
check_dependencies
echo ""
detect_gpu_pci || true
echo ""
check_user_groups
echo ""

# Проверяем драйверы в зависимости от обнаруженного вендора
case "$GPU_VENDOR" in
    NVIDIA)
        check_nvidia_drivers
        ;;
    AMD)
        check_amd_drivers
        ;;
    *)
        print_section "Проверка драйверов"
        print_warn "Вендор GPU неизвестен — проверяем все драйверы..."
        check_nvidia_drivers
        check_amd_drivers
        ;;
esac

echo ""
check_docker
echo ""
check_python_pytorch
echo ""
print_recommendations
print_summary
echo ""
