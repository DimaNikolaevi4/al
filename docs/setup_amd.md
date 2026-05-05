# Настройка сервера для AI Tutor — AMD (ROCm)

> **Вендор GPU:** AMD  
> **Цель:** Подготовить Ubuntu Server 22.04 LTS для запуска AI Tutor с аппаратным ускорением ROCm  
> **Общее время:** ~60–90 минут (зависит от скорости интернета и перезагрузок)

---

## Важные замечания

- ROCm официально поддерживает **ограниченный список GPU** (в основном серии Radeon Instinct, Radeon Pro и некоторые потребительские карты Rx Vega, RX 5000/6000/7000)
- Для неподдерживаемых GPU можно использовать переменную окружения `HSA_OVERRIDE_GFX_VERSION=10.3.0` (на свой страх и риск)
- ROCm работает только на **Linux** (Ubuntu 22.04 — основная поддерживаемая ОС)

---

## Содержание

1. [Базовая настройка системы](#1-базовая-настройка-системы)
2. [Установка AMD ROCm 6.x](#2-установка-amd-rocm-6x)
3. [Настройка переменных окружения ROCm](#3-настройка-переменных-окружения-rocm)
4. [Python 3.10 + venv + PyTorch с ROCm](#4-python-310--venv--pytorch-с-rocm)
5. [Docker + Docker Compose с поддержкой ROCm](#5-docker--docker-compose-с-поддержкой-rocm)
6. [Настройка файрвола (UFW)](#6-настройка-файрвола-ufw)
7. [Проверка установки](#7-проверка-установки)
8. [Решение частых проблем](#8-решение-частых-проблем)

---

## 1. Базовая настройка системы

> **Время:** ~10 минут

### Обновление системы

```bash
sudo apt update && sudo apt upgrade -y
```

### Установка базовых утилит

```bash
sudo apt install -y \
  build-essential \
  cmake \
  git \
  curl \
  wget \
  htop \
  tmux \
  nano \
  software-properties-common \
  apt-transport-https \
  ca-certificates \
  gnupg \
  lsb-release
```

### Добавление пользователя в группу video (важно для ROCm!)

```bash
sudo usermod -aG video $USER
sudo usermod -aG render $USER
```

> **Важно:** Выйдите из системы и войдите заново, чтобы изменения вступили в силу. ROCm требует доступа к устройствам AMD через группу `video` и `render`.

---

## 2. Установка AMD ROCm 6.x

> **Время:** ~20–30 минут  
> **Требование:** Ubuntu 22.04 LTS, GPU из списка поддерживаемых или установка с override

### Добавление репозитория AMD ROCm

```bash
# Добавляем GPG-ключ AMD
curl -fsSL https://repo.radeon.com/rocm/rocm.gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/rocm.gpg

# Добавляем репозиторий ROCm 6.x
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/rocm.gpg] https://repo.radeon.com/rocm/apt/6.0 jammy main" | \
  sudo tee /etc/apt/sources.list.d/rocm.list
```

### Обновление и установка ROCm

```bash
sudo apt update
sudo apt install -y rocm-libs
sudo apt install -y rocm-dev
```

> **Заметка:** Если у вас **неподдерживаемый GPU** (например, RX 7900 XTX), ROCm установится, но для работы PyTorch потребуется переменная окружения `HSA_OVERRIDE_GFX_VERSION` (см. [Раздел 3](#3-настройка-переменных-окружения-rocm)).

### Проверка базовой установки

```bash
/opt/rocm/bin/rocminfo
```

**Ожидаемый вывод:** Информация об агенте HSA (ваша AMD GPU).

```bash
/opt/rocm-6.0.0/bin/rocm-smi
```

**Ожидаемый вывод:**

```
===================================== ROCm System Management Interface =====================================
==================================================== Concise Info ===================================================
GPU  Temp (Edge)  AvgPwr  SCLK     MCLK    Fan     Perf  PwrCap  VRAM%  GPU%  
0    42.0C        45.0W   800MHz   500MHz  20.0%   auto  220.0W   0%     0%    
=====================================================================================================================
```

### ⚠️ Ошибки и решения

| Ошибка | Решение |
|--------|---------|
| `HSA_STATUS_ERROR_OUT_OF_RESOURCES` | Пользователь не в группе `video`: `sudo usermod -aG video $USER` |
| `rocminfo` не видит GPU | Проверьте: `lspci | grep -i vga`. Проверьте поддержку: [ROCm GPU Support](https://rocm.docs.amd.com/en/latest/release/gpu-support.html) |
| `No ROCm-capable agent found` | GPU не поддерживается. Попробуйте `HSA_OVERRIDE_GFX_VERSION` (см. ниже) |
| Ошибка GPG-ключа | Удалите старый ключ: `sudo rm /usr/share/keyrings/rocm.gpg` и повторите установку |
| `E: Unable to locate package rocm-libs` | Проверьте файл `/etc/apt/sources.list.d/rocm.list` |
| Конфликт с amdgpu драйвером | `sudo apt install -y amdgpu-dkms` |

---

## 3. Настройка переменных окружения ROCm

> **Время:** ~5 минут

### Базовые переменные окружения

Добавьте следующие строки в `~/.bashrc`:

```bash
# ROCm paths
export PATH=/opt/rocm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:$LD_LIBRARY_PATH

# Для некоторых AMD GPU (RX 6000/7000 серии) — override GFX версии
# UNCOMMENT ТОЛЬКО ЕСЛИ GPU НЕ ОФИЦИАЛЬНО ПОДДЕРЖИВАЕТСЯ:
# export HSA_OVERRIDE_GFX_VERSION=10.3.0

# Для отладки ROCm (раскомментируйте при проблемах):
# export HSA_ENABLE_SDMA=0
# export ROCM_ENABLE_PRE_VEGA=0
```

Примените изменения:

```bash
source ~/.bashrc
```

### Определение GFX-версии вашего GPU

```bash
/opt/rocm/bin/rocminfo | grep gfx
```

Это покажет архитектуру вашего GPU (например, `gfx1030`, `gfx1100`). Запишите эту версию — она понадобится для PyTorch.

### ⚠️ Версии GFX и какие GPU им соответствуют

| Архитектура | GFX-версия | GPU |
|-------------|-----------|-----|
| RDNA 2      | `gfx1030` | RX 6800, RX 6800 XT, RX 6900 XT |
| RDNA 2 (APU) | `gfx1032` | Ryzen 6000G |
| RDNA 3      | `gfx1100` | RX 7900 XTX, RX 7900 XT |
| RDNA 3      | `gfx1101` | RX 7800 XT, RX 7700 XT |
| CDNA 2      | `gfx90a`  | MI250X, MI250 |
| CDNA 3      | `gfx942`  | MI300X, MI300A |

> Для неподдерживаемых GPU используйте `HSA_OVERRIDE_GFX_VERSION=10.3.0` (RDNA 2 совместимость).

---

## 4. Python 3.10 + venv + PyTorch с ROCm

> **Время:** ~10–15 минут

### Установка Python 3.10

```bash
sudo apt install -y python3.10 python3.10-venv python3.10-dev python3-pip
```

### Создание виртуального окружения

```bash
cd /home/z/my-project/al
python3.10 -m venv venv
source venv/bin/activate
```

### Обновление pip

```bash
pip install --upgrade pip setuptools wheel
```

### Установка PyTorch с поддержкой ROCm 6.0

```bash
# PyTorch с ROCm 6.0 (для Python 3.10, CUDA 12.1 ABI)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.0
```

> **Заметка:** Если ROCm 6.0 недоступен, попробуйте ROCm 5.7:
> ```bash
> pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm5.7
> ```

### Проверка PyTorch + ROCm

```bash
python -c "
import torch
print(f'PyTorch: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'HIP available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'GPU count: {torch.cuda.device_count()}')
    # Быстрый тест вычислений на GPU
    x = torch.rand(5, 5).cuda()
    print(f'Tensor on GPU: {x.device}')
    print('GPU вычисления работают корректно!')
else:
    print('ОШИБКА: GPU не обнаружен PyTorch!')
"
```

**Ожидаемый вывод:**

```
PyTorch: 2.x.x+rocm6.0
CUDA available: True
HIP available: True
GPU: AMD Radeon RX 7900 XTX
GPU count: 1
Tensor on GPU: cuda:0
GPU вычисления работают корректно!
```

### Установка остальных зависимостей проекта

```bash
pip install -r requirements.txt
```

### ⚠️ Ошибки и решения

| Ошибка | Решение |
|--------|---------|
| `CUDA available: False` | Проверьте ROCm: `rocminfo`. Проверьте группу: `groups`. Установите `HSA_OVERRIDE_GFX_VERSION` |
| `hipErrorNoImage` | GFX-версия не поддерживается этой версией PyTorch. Попробуйте другую версию ROCm |
| `ImportError: libamdhip64.so` | Добавьте ROCm в `LD_LIBRARY_PATH`: `export LD_LIBRARY_PATH=/opt/rocm/lib:$LD_LIBRARY_PATH` |
| `HSA_STATUS_ERROR_OUT_OF_RESOURCES` | Перезагрузитесь после добавления в группу `video` |
| `pip install` зависает при загрузке torch | PyTorch для ROCm весит ~2.5 ГБ. Используйте `--no-cache-dir` если повторная установка |
| Ошибка ` Illegal instruction` | Добавьте `export HSA_OVERRIDE_GFX_VERSION=10.3.0` в `~/.bashrc` |

---

## 5. Docker + Docker Compose с поддержкой ROCm

> **Время:** ~10–15 минут

### Установка Docker

```bash
# Добавляем GPG-ключ Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /usr/share/keyrings/docker.gpg

# Добавляем репозиторий Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Установка Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### Добавление пользователя в группу docker

```bash
sudo usermod -aG docker $USER
sudo usermod -aG video $USER
sudo usermod -aG render $USER
```

> **Важно:** Выйдите из системы и войдите заново.

### Настройка Docker для работы с ROCm / HIP

ROCm использует устройство `/dev/kfd` для доступа к GPU. Настройте Docker:

```bash
# Создаем/обновляем конфигурацию Docker
sudo tee /etc/docker/daemon.json > /dev/null << 'EOF'
{
    "runtimes": {
        "rocm": {
            "path": "/opt/rocm/bin/rocminfo",
            "runtimeArgs": []
        }
    },
    "default-runtime": "runc"
}
EOF

# Перезапускаем Docker
sudo systemctl restart docker
```

### Тестовый запуск ROCm контейнера

```bash
sudo docker run --rm \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add=video \
  -it rocm/pytorch:latest \
  python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

> **Примечание:** Для доступа к GPU внутри Docker-контейнера ROCm используются флаги `--device=/dev/kfd --device=/dev/dri --group-add=video` вместо флага `--gpus all` (который используется в NVIDIA Container Toolkit).

### Проверка Docker Compose

```bash
docker compose version
```

### Пример docker-compose.yml для ROCm

```yaml
services:
  ai-tutor:
    build: .
    image: ai-tutor:latest
    ports:
      - "8000:8000"
    environment:
      - HSA_OVERRIDE_GFX_VERSION=10.3.0  # Только если GPU не поддерживается официально
    devices:
      - /dev/kfd
      - /dev/dri
    group_add:
      - video
      - render
    restart: unless-stopped
```

### ⚠️ Ошибки и решения

| Ошибка | Решение |
|--------|---------|
| `permission denied` при доступе к `/dev/kfd` | Добавьте пользователя в группу `video`: `sudo usermod -aG video $USER` |
| `No ROCm-capable agent found` внутри контейнера | Проверьте флаги `--device=/dev/kfd --device=/dev/dri` |
| Контейнер не видит GPU | Убедитесь, что ROCm установлен на хосте. Проверьте: `rocminfo` |
| `docker: Got permission denied` | Выполните `sudo usermod -aG docker $USER` и перезайдите |
| Образ `rocm/pytorch` не найден | Проверьте доступные образы: `docker search rocm` |

---

## 6. Настройка файрвола (UFW)

> **Время:** ~5 минут

### Включение UFW

```bash
sudo ufw enable
```

### Разрешение SSH (важно — чтобы не потерять доступ!)

```bash
sudo ufw allow ssh
sudo ufw allow 22/tcp
```

### Открытие портов для AI Tutor

```bash
# API сервер (FastAPI)
sudo ufw allow 8000/tcp

# Redis (если используется на этом сервере)
sudo ufw allow 6379/tcp
```

### Проверка статуса

```bash
sudo ufw status verbose
```

**Ожидаемый вывод:**

```
Status: Active
To                         Action      From
--                         ------      ----
22/tcp                     ALLOW IN    Anywhere
8000/tcp                   ALLOW IN    Anywhere
6379/tcp                   ALLOW IN    Anywhere
22/tcp (v6)                ALLOW IN    Anywhere (v6)
8000/tcp (v6)              ALLOW IN    Anywhere (v6)
6379/tcp (v6)              ALLOW IN    Anywhere (v6)
```

### ⚠️ Ошибки и решения

| Ошибка | Решение |
|--------|---------|
| Потеря SSH-доступа после `ufw enable` | Подключитесь через консоль сервера и выполните `sudo ufw allow 22/tcp` |
| Порт 6379 открыт в сети | Если Redis не нужен извне, ограничьте: `sudo ufw allow from 10.0.0.0/8 to any port 6379` |
| `command not found: ufw` | Установите: `sudo apt install ufw` |

---

## 7. Проверка установки

> **Время:** ~5 минут

Запустите все проверочные команды по очереди:

### 1. Проверка ROCm — информация о GPU

```bash
rocm-smi
```

✅ Должна отображаться информация о GPU AMD: температура, частоты, использование памяти.

### 2. Проверка агента HSA

```bash
rocminfo
```

✅ Должен быть указан хотя бы один агент (ваша AMD GPU) с типом `gfx***`.

### 3. Проверка PyTorch + ROCm

```bash
cd /home/z/my-project/al
source venv/bin/activate
python -c "import torch; print(torch.cuda.is_available())"
```

✅ Должно вывести `True`.

### 4. Проверка PyTorch + MPS (альтернатива)

```bash
python -c "import torch; print(torch.cuda.is_available() or torch.backends.mps.is_available())"
```

✅ Должно вывести `True`. (MPS — Metal Performance Shaders — работает только на macOS, но проверка включена для совместимости.)

### 5. Полный скрипт проверки

```bash
echo "=== Проверка настройки сервера AI Tutor (AMD ROCm) ==="
echo ""
echo "--- ROCm SMI ---"
rocm-smi 2>/dev/null || /opt/rocm/bin/rocm-smi || echo "rocm-smi не найден"
echo ""
echo "--- ROCm Info ---"
rocminfo 2>/dev/null | grep -E "Name:| gfx" || echo "rocminfo не найден"
echo ""
echo "--- PyTorch ROCm ---"
python3 -c "import torch; print(f'CUDA/HIP available: {torch.cuda.is_available()}'); print(f'PyTorch: {torch.__version__}')" 2>/dev/null || echo "PyTorch не установлен"
echo ""
echo "--- Docker ---"
docker --version
docker compose version
echo ""
echo "--- UFW ---"
sudo ufw status | head -5
echo ""
echo "--- Группы пользователя ---"
groups
echo ""
echo "=== Проверка завершена ==="
```

---

## 8. Решение частых проблем

### Проблема: GPU не определяется через ROCm

```bash
# Проверяем, видит ли PCIe шина GPU
lspci | grep -i amd

# Проверяем драйвер amdgpu
sudo dmesg | grep amdgpu

# Проверяем agенты ROCm
rocminfo

# Если GPU не поддерживается — пробуем override
export HSA_OVERRIDE_GFX_VERSION=10.3.0
python -c "import torch; print(torch.cuda.is_available())"
```

### Проблема: PyTorch видит GPU, но вычисления падают

```bash
# Отключите SDMA (иногда вызывает проблемы)
export HSA_ENABLE_SDMA=0

# Или включите явную синхронизацию
export PYTORCH_ROCM_ARCH=gfx1030

# Замените gfx1030 на вашу версию GPU (из rocminfo)
```

### Проблема: Out of Memory при обучении

```bash
# Проверьте свободную VRAM
rocm-smi

# Уменьшите batch_size в конфигурации
# Или используйте градиентное накопление
# Или используйте mixed precision training (fp16/bf16)
```

### Проблема: Несовместимость версий ROCm и PyTorch

| Версия ROCm | Версия PyTorch | Флаг установки |
|-------------|---------------|----------------|
| ROCm 6.0    | PyTorch 2.2+  | `--index-url https://download.pytorch.org/whl/rocm6.0` |
| ROCm 5.7    | PyTorch 2.1+  | `--index-url https://download.pytorch.org/whl/rocm5.7` |
| ROCm 5.6    | PyTorch 2.0+  | `--index-url https://download.pytorch.org/whl/rocm5.6` |

Проверьте совместимость: [PyTorch ROCm Support](https://pytorch.org/get-started/locally/)

### Проблема: `HSA_STATUS_ERROR_OUT_OF_RESOURCES`

Это самая частая ошибка при работе с ROCm:

```bash
# 1. Проверьте, что вы в группе video
groups | grep video

# 2. Если нет — добавьте и перезайдите
sudo usermod -aG video $USER
sudo usermod -aG render $USER
# ВЫЙДИТЕ И ВОЙДИТЕ ЗАНОВО

# 3. Проверьте права доступа к устройствам
ls -la /dev/kfd
ls -la /dev/dri/

# 4. Если права неверные:
sudo chmod 666 /dev/kfd
sudo chmod 666 /dev/dri/render*
```

### Проблема: Docker контейнер не видит GPU

```bash
# Убедитесь, что устройства доступны
ls -la /dev/kfd /dev/dri/

# Проверьте ROCm внутри контейнера
sudo docker run --rm \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add=video \
  rocm/pytorch:latest \
  rocminfo
```

---

## Быстрая установка (одна команда)

> **Внимание:** Используйте только на чистой системе!

```bash
cat > ~/setup_amd.sh << 'SCRIPT'
#!/bin/bash
set -e

echo "=== Базовая настройка ==="
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential cmake git curl wget htop tmux nano \
  software-properties-common apt-transport-https ca-certificates gnupg lsb-release \
  python3.10 python3.10-venv python3.10-dev python3-pip

echo "=== Добавление пользователя в группы ==="
sudo usermod -aG video $USER
sudo usermod -aG render $USER

echo "=== Установка ROCm 6.0 ==="
curl -fsSL https://repo.radeon.com/rocm/rocm.gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/rocm.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/rocm.gpg] https://repo.radeon.com/rocm/apt/6.0 jammy main" | sudo tee /etc/apt/sources.list.d/rocm.list
sudo apt update
sudo apt install -y rocm-libs rocm-dev

echo "=== Переменные окружения ROCm ==="
echo 'export PATH=/opt/rocm/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/opt/rocm/lib:$LD_LIBRARY_PATH' >> ~/.bashrc
echo '# export HSA_OVERRIDE_GFX_VERSION=10.3.0  # Раскомментируйте если GPU не поддерживается' >> ~/.bashrc

echo "=== Установка Docker ==="
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER

echo "=== Файрвол UFW ==="
sudo ufw allow ssh
sudo ufw allow 8000/tcp
sudo ufw allow 6379/tcp
sudo ufw --force enable

echo "=== Настройка завершена! ==="
echo "Пожалуйста, ВЫЙДИТЕ И ВОЙДИТЕ ЗАНОВО (для применения групп)."
echo "После входа:"
echo "  source ~/.bashrc"
echo "  cd /home/z/my-project/al"
echo "  python3.10 -m venv venv && source venv/bin/activate"
echo "  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.0"
echo "  pip install -r requirements.txt"
SCRIPT

chmod +x ~/setup_amd.sh
```

---

## Сравнение NVIDIA и ROCm

| Параметр | NVIDIA (CUDA) | AMD (ROCm) |
|----------|---------------|------------|
| Утилита мониторинга | `nvidia-smi` | `rocm-smi` |
| Информация о GPU | `nvidia-smi -L` | `rocminfo` |
| Переменные окружения | `CUDA_HOME=/usr/local/cuda` | `ROCM_PATH=/opt/rocm` |
| Docker GPU флаг | `--gpus all` | `--device=/dev/kfd --device=/dev/dri` |
| PyTorch индекс | `cu121` | `rocm6.0` |
| Распознавание в PyTorch | `torch.cuda.is_available()` | `torch.cuda.is_available()` (та же API через HIP) |

---

*Документ создан для проекта AI Tutor. При возникновении проблем используйте скрипт `/home/z/my-project/al/scripts/detect_gpu.sh` для диагностики.*
