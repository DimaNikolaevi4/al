# Qubu Deploy — Краткая шпаргалка
# ===================================
# Обновлено: 08.05.2026

## Быстрый деплой (если GGUF уже в Git LFS)

```bash
# 1. Обновить конфигурацию и запустить деплой через API
python qubu-deploy/deploy_qubu.py --deploy

# 2. Проверить статус
python qubu-deploy/deploy_qubu.py --status
```

## Полный деплой (включая загрузку GGUF через LFS)

```bash
# 1. Загрузить GGUF в репозиторий Qubu (~30-60 мин)
python qubu-deploy/deploy_qubu.py --push-lfs --deploy

# Или по шагам:
chmod +x qubu-deploy/push_to_qubu.sh
./qubu-deploy/push_to_qubu.sh ./qubu-model-repo

# 2. Обновить конфигурацию инференса на Qubu
python qubu-deploy/deploy_qubu.py --deploy

# 3. Мониторить статус
python qubu-deploy/deploy_qubu.py --status
```

## Через UI (если API не работает)

1. Открыть: https://qubu.ai/models/intellektualniy-tyutor-na-osnove-otkrytykh-bolshikh-yazykovykh-modelei-dlya-spo/edit
2. Вкладка «Инференс»
3. Вставить код service_gguf.py в поле Code
4. Вставить startup_script.sh в Startup Script
5. Вставить bentofile.yaml в bentofile
6. Requirements: `bentoml>=1.2.0`
7. Нажать Save/Deploy

## Ключевые URL

| Ресурс | URL |
|--------|-----|
| Страница модели | https://qubu.ai/models/intellektualniy-tyutor-na-osnove-otkрыты... |
| Редактирование | .../edit |
| Git repo | git.qubu.ai/REDACTED_USERNAME/ml_model-... |

## Ключевые переменные

| Переменная | Значение |
|------------|----------|
| MODEL_PATH | /workspace/model |
| N_CTX | 2048 |
| N_GPU_LAYERS | -1 (все на GPU) |
| GPU | RTX 4000 Ada (20 ГБ) |
| GGUF размер | ~15 ГБ |
| Таймаут деплоя | 50 мин |
| Модель ID | c9827a6f-be25-40ea-8f80-a71275248188 |

## Pre-built wheel llama-cpp-python

```
https://abetlen.github.io/llama-cpp-python/whl/cu121/llama_cpp_python-0.3.2-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
```
CUDA 12.1, Python 3.11, установка БЕЗ компиляции.
