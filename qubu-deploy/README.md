# qubu-deploy

Деплой ИИ-тьютора для СПО на платформу Qubu (конкурс «Гравитация 2026»).

## Структура

```
qubu-deploy/
├── service.py                   # Основной сервис (BentoML 1.2+, class-based, GGUF)
├── bentofile.yaml               # Конфигурация BentoML
├── requirements.txt             # Python-зависимости (bentoml>=1.2.0)
├── startup_script.sh            # Установка wheel + скачивание GGUF
│
├── deploy_qubu.py               # CLI: деплой через API (--push-lfs, --deploy, --status)
├── push_to_qubu.sh              # Git LFS загрузка GGUF в репо Qubu
│
├── service_transformers.py      # Альтернативный сервис (transformers + QLoRA)
├── requirements_transformers.txt
│
├── README.md                    # Этот файл
├── DEPLOY_GUIDE.md              # Полное руководство (API, troubleshooting)
├── DEPLOY_PLAN.md               # План деплоя (блоки A-F, статусы)
├── QUBU_LIMITS_ANALYSIS.md      # Анализ ограничений и выбор модели
├── SUBMISSION_README.md         # Конкурсная заявка
└── qubu_finetune.ipynb          # Ноутбук дообучения на GPU Qubu
```

## Ключевые параметры

| Параметр | Значение |
|----------|----------|
| GPU | NVIDIA RTX 4000 Ada (20 ГБ VRAM) |
| Таймаут билда | 50 минут (жёсткий) |
| Фреймворк | BentoML 1.2+ (class-based) |
| Инференс | llama-cpp-python (CUDA 12.1 pre-built wheel) |
| Команда запуска | `bentoml serve service:Service` |

## Быстрый старт

### Вариант 1: Через UI (рекомендуется)

1. Открыть страницу модели на Qubu, вкладка «Инференс»
2. Вставить код из `service.py` в поле Code
3. Вставить содержимое `startup_script.sh` в Startup Script
4. Вставить `bentofile.yaml` в bentofile
5. Requirements: `bentoml>=1.2.0`
6. Env vars: `MODEL_PATH=/workspace/model`, `N_CTX=2048`, `N_GPU_LAYERS=-1`
7. Нажать Save/Deploy

### Вариант 2: Через скрипт

```bash
# Обновить конфигурацию и запустить деплой
export QUBU_API_TOKEN="your_token"
python qubu-deploy/deploy_qubu.py --deploy

# Проверить статус
python qubu-deploy/deploy_qubu.py --status
```

### Вариант 3: Git LFS (загрузка GGUF в репо Qubu)

```bash
export QUBU_GIT_TOKEN="your_git_token"
chmod +x qubu-deploy/push_to_qubu.sh
./qubu-deploy/push_to_qubu.sh ./qubu-model-repo
```

## Endpoints сервиса

| Endpoint | Описание |
|----------|----------|
| `GET /health` | Проверка загрузки модели |
| `POST /predict` | Qubu Builder: `inputs.message` → `result.answer` |
| `POST /generate_summary` | Конспект лекции из `inputs.lecture_text` |
| `POST /generate_quiz` | Тест из N вопросов (easy/medium/hard) |
| `POST /chat` | Диалог с историей (`inputs.message` + `inputs.history`) |

## Документация

- **DEPLOY_GUIDE.md** — полное руководство: API Qubu, troubleshooting, 3 неудачных деплоя
- **DEPLOY_PLAN.md** — план по блокам A-F с текущими статусами
- **QUBU_LIMITS_ANALYSIS.md** — расчёт лимитов, таблица моделей, рекомендации
- **SUBMISSION_README.md** — конкурсная заявка для Гравитации 2026
