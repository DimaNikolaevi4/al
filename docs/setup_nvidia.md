# Настройка сервера для AI Tutor — NVIDIA (CUDA)

> **Вендор GPU:** NVIDIA  
> **Цель:** Подготовить Ubuntu Server 22.04 LTS для запуска AI Tutor с аппаратным ускорением CUDA  
> **Общее время:** ~60–90 минут (зависит от скорости интернета и перезагрузок)

---

## Содержание

1. [Базовая настройка системы](#1-базовая-настройка-системы)
2. [Установка драйверов NVIDIA](#2-установка-драйверов-nvidia)
3. [Установка CUDA Toolkit 12.x](#3-установка-cuda-toolkit-12x)
4. [Установка cuDNN](#4-установка-cudnn)
5. [Python 3.10 + venv + PyTorch с CUDA](#5-python-310--venv--pytorch-с-cuda)
6. [Docker + Docker Compose + NVIDIA Container Toolkit](#6-docker--docker-compose--nvidia-container-toolkit)
7. [Настройка файрвола (UFW)](#7-настройка-файрвола-ufw)
8. [Проверка установки](#8-проверка-установки)
9. [Решение частых проблем](#9-решение-частых-проблем)

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

### Отключение Nouveau (Open Source драйвер NVIDIA)

Если установлен драйвер Nouveau, он может конфликтовать с проприетарным драйвером NVIDIA:

```bash
# Проверяем, загружен ли Nouveau
lsmod | grep nouveau

# Если да — отключаем
sudo bash -c "echo blacklist nouveau > /etc/modprobe.d/blacklist-nouveau.conf"
sudo bash -c "echo options nouveau modeset=0 >> /etc/modprobe.d/blacklist-nouveau.conf"
sudo update-initramfs -u
```

> **После этого потребуется перезагрузка:**

```bash
sudo reboot
```

---

## 2. Установка драйверов NVIDIA

> **Время:** ~10–15 минут  
> **Требование:** Драйвер версии 525 или выше

### Добавление PPA репозитория NVIDIA

```bash
sudo add-apt-repository ppa:graphics-drivers/ppa -y
sudo apt update
```

### Установка драйвера (рекомендуется версия 550)

```bash
sudo apt install -y nvidia-driver-550
```

### Перезагрузка

```bash
sudo reboot
```

### Проверка драйвера

```bash
nvidia-smi
```

**Ожидаемый вывод:**

```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 535.xx    Driver Version: 535.xx    CUDA Version: 12.2         |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|===============================+======================+======================|
```

### ⚠️ Ошибки и решения

| Ошибка | Решение |
|--------|---------|
| `NVIDIA-SMI has failed` | Драйвер не загружен. Выполните `sudo modprobe nvidia` |
| `command not found: nvidia-smi` | Драйвер не установлен. Повторите установку из [шага 2](#2-установка-драйверов-nvidia) |
| Secure Boot блокирует загрузку | Отключите Secure Boot в BIOS/UEFI |
| `modprobe: FATAL: Module nvidia not found` | Установите заголовки ядра: `sudo apt install linux-headers-$(uname -r)` |

---

## 3. Установка CUDA Toolkit 12.x

> **Время:** ~15–20 минут  
> **Заметка:** CUDA Toolkit устанавливается отдельно от драйвера. Версия CUDA Runtime может отличаться от версии, показываемой `nvidia-smi`

### Добавление репозитория NVIDIA CUDA

```bash
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update
```

### Установка CUDA Toolkit 12.2

```bash
sudo apt install -y cuda-toolkit-12-2
```

### Настройка переменных окружения

Добавьте следующие строки в `~/.bashrc`:

```bash
echo 'export PATH=/usr/local/cuda-12.2/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-12.2/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

### Проверка установки CUDA

```bash
nvcc --version
```

**Ожидаемый вывод:**

```
nvcc: NVIDIA (R) Cuda compiler driver
Cuda compilation tools, release 12.2, V12.2.xxx
```

### ⚠️ Ошибки и решения

| Ошибка | Решение |
|--------|---------|
| `command not found: nvcc` | Проверьте PATH: `echo $PATH`. Должен содержать `/usr/local/cuda-12.2/bin` |
| `cuda.h: No such file or directory` | Установите dev-пакет: `sudo apt install cuda-toolkit-12-2` |
| Конфликт версий CUDA | Удалите старые версии: `sudo apt remove --autoremove cuda-*` |
| Не хватает места на диске | CUDA требует ~8 ГБ. Проверьте: `df -h /usr/local` |

---

## 4. Установка cuDNN

> **Время:** ~5–10 минут  
> **Заметка:** Требует регистрации на developer.nvidia.com (бесплатно)

### Установка через apt (рекомендуется)

```bash
sudo apt install -y cudnn
```

### Альтернатива: ручная установка .deb пакетов

1. Скачайте cuDNN с [developer.nvidia.com/rdp/cudnn](https://developer.nvidia.com/rdp/cudnn) (требуется авторизация)
2. Для CUDA 12.x нужны пакеты `cudnn-local-repo-ubuntu2204-9.x.x`

```bash
# Пример (замените на скачанный файл)
sudo dpkg -i cudnn-local-repo-ubuntu2204-9.2.0_1.0-1_amd64.deb
sudo cp /var/cudnn-local-repo-ubuntu2204-9.2.0/include/cudnn*.h /usr/local/cuda-12.2/include
sudo cp /var/cudnn-local-repo-ubuntu2204-9.2.0/lib64/libcudnn* /usr/local/cuda-12.2/lib64
sudo chmod a+r /usr/local/cuda-12.2/include/cudnn*.h
sudo chmod a+r /usr/local/cuda-12.2/lib64/libcudnn*
```

### Проверка cuDNN

```bash
cat /usr/local/cuda-12.2/include/cudnn_version.h | grep CUDNN_MAJOR -A 2
```

### ⚠️ Ошибки и решения

| Ошибка | Решение |
|--------|---------|
| `Cannot open shared object file: libcudnn.so` | Обновите кэш: `sudo ldconfig` |
| Несовместимость версий cuDNN и CUDA | Проверьте матрицу совместимости на сайте NVIDIA |
| `E: Unable to locate package cudnn` | Используйте ручную установку .deb пакетов |

---

## 5. Python 3.10 + venv + PyTorch с CUDA

> **Время:** ~10 минут

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

### Установка PyTorch с поддержкой CUDA 12.x

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Проверка PyTorch + CUDA

```bash
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

**Ожидаемый вывод:**

```
PyTorch: 2.x.x+cu121
CUDA available: True
CUDA version: 12.1
GPU: NVIDIA GeForce RTX XXXX
```

### Установка остальных зависимостей проекта

```bash
pip install -r requirements.txt
```

### ⚠️ Ошибки и решения

| Ошибка | Решение |
|--------|---------|
| `CUDA available: False` | Проверьте драйвер: `nvidia-smi`. Проверьте версию CUDA в PyTorch |
| `RuntimeError: CUDA out of memory` | Уменьшите batch size или используйте модель поменьше |
| `pip install` зависает | Используйте зеркало: `pip install --index-url https://download.pytorch.org/whl/cu121 torch` |
| ImportError: libcuda.so | Драйвер NVIDIA не установлен или не загружен |

---

## 6. Docker + Docker Compose + NVIDIA Container Toolkit

> **Время:** ~10–15 минут

### Установка Docker

```bash
# Добавляем GPG-ключ Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

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
```

> **Важно:** Выйдите из системы и войдите заново, чтобы изменения вступили в силу.

### Установка NVIDIA Container Toolkit

```bash
# Добавляем репозиторий
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Установка
sudo apt update
sudo apt install -y nvidia-container-toolkit
```

### Настройка Docker для работы с NVIDIA GPU

```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### Проверка Docker с GPU

```bash
sudo docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

**Ожидаемый вывод:** `nvidia-smi` должен отобразить информацию о GPU внутри контейнера.

### Проверка Docker Compose

```bash
docker compose version
```

### ⚠️ Ошибки и решения

| Ошибка | Решение |
|--------|---------|
| `could not select device driver "" with capabilities: [[gpu]]` | NVIDIA Container Toolkit не настроен. Повторите шаг настройки |
| `permission denied while trying to connect to the Docker daemon socket` | Выполните `sudo usermod -aG docker $USER` и перезайдите |
| `docker: Got permission denied` | Используйте `sudo` или перезайдите после добавления в группу |
| Контейнер не видит GPU | Убедитесь, что в docker-compose добавлено `deploy: resources: reservations: devices: - capabilities: [gpu]` |

---

## 7. Настройка файрвола (UFW)

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

## 8. Проверка установки

> **Время:** ~5 минут

Запустите все проверочные команды по очереди:

### 1. Проверка драйвера NVIDIA

```bash
nvidia-smi
```

✅ Должен отображаться драйвер версии 525+, информация о GPU, температура, использование памяти.

### 2. Проверка CUDA Compiler

```bash
nvcc --version
```

✅ Должна отображаться версия CUDA 12.x.

### 3. Проверка PyTorch + CUDA

```bash
cd /home/z/my-project/al
source venv/bin/activate
python -c "import torch; print(torch.cuda.is_available())"
```

✅ Должно вывести `True`.

### 4. Проверка cuDNN

```bash
python -c "import torch; print(f'cuDNN version: {torch.backends.cudnn.version()}')"
```

✅ Должна отображаться версия cuDNN (например, 8902).

### 5. Проверка Docker с GPU

```bash
sudo docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

✅ Внутри контейнера должен работать `nvidia-smi`.

### 6. Полный скрипт проверки

```bash
echo "=== Проверка настройки сервера AI Tutor ==="
echo ""
echo "--- NVIDIA Driver ---"
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
echo ""
echo "--- CUDA Toolkit ---"
nvcc --version | grep "release"
echo ""
echo "--- cuDNN ---"
python3 -c "import torch; print(f'cuDNN {torch.backends.cudnn.version()}')" 2>/dev/null || echo "cuDNN не найдена"
echo ""
echo "--- PyTorch CUDA ---"
python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}, version: {torch.version.cuda}')" 2>/dev/null || echo "PyTorch не установлен"
echo ""
echo "--- Docker ---"
docker --version
docker compose version
echo ""
echo "--- UFW ---"
sudo ufw status | head -5
echo ""
echo "=== Проверка завершена ==="
```

---

## 9. Решение частых проблем

### Проблема: GPU не определяется

```bash
# Проверяем, видит ли PCIe шина GPU
lspci | grep -i nvidia

# Проверяем загружен ли модуль ядра
lsmod | grep nvidia

# Загружаем модуль вручную
sudo modprobe nvidia
sudo modprobe nvidia_uvm
sudo modprobe nvidia_drm
```

### Проблема: Out of Memory при обучении

```bash
# Проверьте свободную VRAM
nvidia-smi

# Уменьшите batch_size в конфигурации
# Или используйте градиентное накопление
# Или используйте mixed precision training (fp16/bf16)
```

### Проблема: Несовместимые версии драйвера и CUDA

| Версия драйвера | Минимальная версия CUDA |
|-----------------|------------------------|
| 525.xx          | CUDA 12.0              |
| 535.xx          | CUDA 12.2              |
| 545.xx          | CUDA 12.3              |
| 550.xx          | CUDA 12.4              |

Проверьте матрицу совместимости: [NVIDIA CUDA Release Notes](https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html#cuda-major-component-versions)

### Проблема: Docker не имеет доступа к GPU

```bash
# Перенастройте NVIDIA Container Toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Проверьте конфигурацию
cat /etc/docker/daemon.json
```

Должно содержать:

```json
{
    "runtimes": {
        "nvidia": {
            "path": "nvidia-container-runtime",
            "runtimeArgs": []
        }
    }
}
```

---

## Быстрая установка (одна команда)

> **Внимание:** Используйте только на чистой системе! Скрипт перезагрузит сервер.

```bash
# Сохраните и запустите после ручной перезагрузки
cat > ~/setup_nvidia.sh << 'SCRIPT'
#!/bin/bash
set -e

echo "=== Базовая настройка ==="
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential cmake git curl wget htop tmux nano \
  software-properties-common apt-transport-https ca-certificates gnupg lsb-release \
  python3.10 python3.10-venv python3.10-dev python3-pip

echo "=== Установка драйвера NVIDIA 550 ==="
sudo add-apt-repository ppa:graphics-drivers/ppa -y
sudo apt update
sudo apt install -y nvidia-driver-550

echo "=== Установка CUDA Toolkit 12.2 ==="
wget -q https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt install -y cuda-toolkit-12-2
echo 'export PATH=/usr/local/cuda-12.2/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-12.2/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
sudo apt install -y cudnn

echo "=== Установка Docker ==="
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER

echo "=== NVIDIA Container Toolkit ==="
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

echo "=== Файрвол UFW ==="
sudo ufw allow ssh
sudo ufw allow 8000/tcp
sudo ufw allow 6379/tcp
sudo ufw --force enable

echo "=== Настройка завершена! ==="
echo "Пожалуйста, перезагрузите сервер: sudo reboot"
echo "После перезагрузки запустите:"
echo "  source ~/.bashrc"
echo "  cd /home/z/my-project/al"
echo "  python3.10 -m venv venv && source venv/bin/activate"
echo "  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121"
echo "  pip install -r requirements.txt"
SCRIPT

chmod +x ~/setup_nvidia.sh
```

---

*Документ создан для проекта AI Tutor. При возникновении проблем используйте скрипт `/home/z/my-project/al/scripts/detect_gpu.sh` для диагностики.*
