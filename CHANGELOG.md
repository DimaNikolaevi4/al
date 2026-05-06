# Журнал изменений (Changelog)

Все заметные изменения проекта ИИ-тьютор для СПО документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/),
и этот проект придерживается [Семантического версионирования](https://semver.org/lang/ru/).

---

## [Unreleased] — Будущие версии

### Планируется
- Дообучение модели на датасете СИТ (ожидает GPU)
- Gold Standard (50 примеров ручной разметки)
- Пилотное внедрение в группе 15.02.14 (Q4 2026)
- Генерация аудиоконтента для доступности
- Потоковый вывод (streaming) для веб-интерфейса
- Интеграция с ИИ-Монолит

---

## [0.3.0] — 2026-05-06

### Добавлено

**API сервер**
- **FastAPI приложение** (`api/main.py`): lifespan с загрузкой/выгрузкой модели, CORS, timing middleware, degraded mode (сервер стартует даже без модели)
- **10 эндпоинтов**: sync (generate-summary, generate-test, chat) + async (submit + status для каждого) + system (health, info, stats)
- **Pydantic модели** (`api/models.py`): 12 схем для валидации запросов/ответов
- **Celery + Redis** (`api/celery_app.py`): singleton-модель в worker, time limits, retry
- **Async задачи** (`api/tasks.py`, `api/routes/async_generate.py`): паттерн submit → poll → result
- **Конфигурация** (`api/config.py`): Pydantic Settings через `.env`

**Интеграция с Moodle**
- **Local Plugin** (`moodle/local/aitutor/`): version.php, settings.php, service.php, AJAX, JS-модуль, lang (ru/en), capabilities, DB (install.xml)
- **Block «ИИ Тьютор»** (`moodle/local/aitutor/block_aitutor/`): PHP-блок, edit_form, CSS, 3 кнопки (конспект/тест/чат), AJAX + модальное окно
- **Документация** (`moodle/docs/README_MOODLE.md`): архитектура, установка, настройка, API-интеграция, troubleshooting

**Дообучение модели**
- **QLoRA конфигурация** (`lora_config.py`): 4-bit NF4, bfloat16, 3 пресета (debug/light/full), 7 target modules
- **SFTTrainer** (`train.py`): gradient checkpointing, cosine scheduler, TensorBoard, resume, 3 режима запуска
- **Data Collator** (`data_collator.py`): chat_template токенизация, динамический паддинг до кратного 8, маскирование prompt-токенов
- **Оценка** (`evaluate.py`): метрики keyword_overlap, line_match, length_ratio, tokens/sec

**Контейнеризация и DevOps**
- **Dockerfile**: multi-stage build, healthcheck, GPU-агностичный
- **Docker Compose** (`docker-compose.yml`): api + celery-worker + redis
- **Dev overlay** (`docker-compose.dev.yml`): hot-reload, volume mounts
- **`.env.docker.example`**: шаблон конфигурации для Docker

**Мониторинг**
- **Prometheus** (`monitoring/prometheus.yml`): scrape API, Celery, Redis
- **Grafana дашборд** (`monitoring/grafana_dashboards/ai_tutor_overview.json`): 6 панелей (requests, latency, tasks, tokens, GPU, system)

**Инфраструктурные скрипты**
- **`scripts/harden_server.sh`**: UFW, SSH hardening, fail2ban, sysctl, auto-updates (idempotent)
- **`scripts/detect_gpu.sh`**: автоопределение GPU (NVIDIA/AMD)
- **`scripts/deploy.sh`**: деплой приложения + smoke test
- **`scripts/deploy_dataset.sh`**: копирование датасета + JSONL-валидация + статистика
- **`scripts/smoke_test.py`**: проверка health, async flow (submit → poll)
- **`scripts/backup.sh`**: бэкап адаптеров, логов, конфигурации
- **`scripts/validate_annotations.py`**: валидация разметки датасета (формат, контент, дубликаты, баланс)

**Документация**
- Инструкция для студентов (`docs/draft_student_instruction.md`, ~3600 слов)
- Инструкция для преподавателей (`docs/draft_teacher_instruction.md`, ~4100 слов)
- План семинара для педагогов (`docs/draft_seminar_plan.md`, 3 часа / 8 блоков)
- Руководство для старост-техподдержки (`docs/draft_student_support_guide.md`)
- Анкета обратной связи студентов (`docs/draft_feedback_form.md`, 17 вопросов)
- Методические рекомендации для других техникумов (`docs/draft_methodology_recommendations.md`, ~6500 слов)
- Черновик статьи в профессиональный журнал (`docs/draft_journal_article.md`, ~6100 слов)
- Шаблон финального отчёта (`docs/draft_final_report.md`, 12 разделов)
- Расчёт ROI (`docs/roi_calculation.md`, 3 сценария)
- Сценарий видео-урока (`docs/draft_video_script.md`, ~30 мин)
- Руководство по Gold Standard (`docs/gold_standard_guidelines.md`)
- Сценарии установки NVIDIA (`docs/setup_nvidia.md`) и AMD (`docs/setup_amd.md`)

**Юридические документы**
- Соглашение об использовании ИИ для студентов (`docs/draft_student_ai_agreement.md`)
- Соглашение об обработке преподавательских материалов (`docs/draft_teacher_materials_agreement.md`)
- Черновик публикации на портале техникума (`docs/draft_portal_publication.md`)
- Презентация для защиты проекта (`docs/ai_tutor_presentation.pptx`, 12 слайдов)

### Изменено

- **CHECKLIST.md**: расширен до 117 задач (было 80), сводка приведена к актуальному состоянию (57%)
- **requirements.txt**: добавлены fastapi, celery, redis, pydantic-settings, httpx, trl
- **Структура репозитория**: добавлены api/, moodle/, monitoring/, scripts/, Dockerfile, docker-compose

---

## [0.2.0] — 2026-04-25

### Добавлено
- **Система логирования**: Комплексное логирование с несколькими уровнями (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Аннотации типов**: Полная поддержка type hints Python 3.10+ для всех функций и методов
- **Обработка ошибок**: Кастомные исключения (`ModelLoadError`, `InferenceError`) с правильным контекстом ошибок
- **Конфигурация**: Поддержка конфигурации через переменные окружения (файл `.env`)
- **Чат-интерфейс**: Базовая возможность диалога с поддержкой истории
- **Генерация тестов**: Начальная реализация генерации тестов/вопросов (экспериментально)
- **Unit-тесты**: Базовая структура тестов с фреймворком pytest

### Изменено
- **Качество кода**: Рефакторинг всей кодовой базы в соответствии с PEP 257
- **Управление памятью**: Добавлена явная очистка памяти при ошибках OOM
- **Документация**: Расширен README с badges, диаграммой архитектуры и подробными инструкциями по установке

### Исправлено
- Конфигурация pad token токенизатора для корректной генерации
- Валидация входных данных для пустых текстов лекций
- Корректная обработка ошибок CUDA out-of-memory

### Безопасность
- Добавлен `.env` в `.gitignore` для предотвращения утечки учётных данных
- Реализован параметр trust_remote_code для загрузки моделей

---

## [0.1.1] — 2026-04-10

### Добавлено
- Базовая структура проекта с requirements.txt
- Начальная документация в README.md
- CHECKLIST.md для отслеживания проекта

### Изменено
- Обновлён путь к модели на Mistral Small 3.1 (24B)
- Улучшено форматирование промптов для лучшей генерации конспектов

### Исправлено
- Device mapping для мульти-GPU систем
- Проблемы кодировки токенизатора с русским текстом

---

## [0.1.0] — 2026-03-01

### Добавлено
- **Основной модуль**: Начальная реализация класса `IntelligentTutor`
- **Загрузка модели**: Поддержка загрузки моделей Mistral из Hugging Face Hub
- **Конспектирование лекций**: Базовая функциональность генерации структурированных конспектов лекций
- **Интеграция PEFT**: Поддержка загрузки LoRA-адаптеров через библиотеку PEFT
- **Поддержка GPU**: Автоматическое размещение устройств с `device_map="auto"`
- **Эффективность памяти**: Точность float16 для снижения объёма памяти

### Технические детали
- Базовая модель: `mistralai/Mistral-Small-24B-Instruct-2501`
- Зависимости: PyTorch 2.0+, Transformers 4.35+, PEFT 0.6+
- Начальный proof-of-concept, демонстрирующий возможность тьютора на базе LLM

---

## Краткая история версий

| Версия | Дата | Описание |
|--------|------|----------|
| 0.3.0 | 2026-05-06 | API сервер, Celery, Moodle-плагин, QLoRA-тренировка, Docker, мониторинг, документация |
| 0.2.0 | 2026-04-25 | Production-ready качество кода, логирование, обработка ошибок |
| 0.1.1 | 2026-04-10 | Структура проекта и улучшения документации |
| 0.1.0 | 2026-03-01 | Начальный прототип с интеграцией Mistral |

---

[Unreleased]: https://github.com/DimaNikolaevi4/al/compare/v0.3.0...main
[0.3.0]: https://github.com/DimaNikolaevi4/al/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/DimaNikolaevi4/al/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/DimaNikolaevi4/al/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/DimaNikolaevi4/al/releases/tag/v0.1.0
