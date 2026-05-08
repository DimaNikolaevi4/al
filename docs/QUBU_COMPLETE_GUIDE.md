# Полное руководство по развертыванию AI-тьютора на Qubu

**Обновлено:** 08 мая 2026
**Конкурс:** Гравитация 2026 (Qubu)
**Проект:** Интеллектуальный тьютор на базе LLM для СПО
**Базовая модель:** Mistral Small 24B-Instruct-2501 (GGUF Q4_K_M)
**Организация:** ГБПОУ РО «Сальский индустриальный техникум» (СИТ)

---

## Содержание

1. [Обзор проекта](#1-обзор-проекта)
2. [Учетные записи и доступы](#2-учетные-записи-и-доступы)
3. [Ссылки на ресурсы Qubu](#3-ссылки-на-ресурсы-qubu)
4. [Архитектура решения](#4-архитектура-решения)
5. [Стратегия развертывания (GGUF + llama-cpp-python)](#5-стратегия-развертывания-gguf--llama-cpp-python)
6. [Файлы проекта](#6-файлы-проекта)
7. [API Qubu —Endpoints и работа с ними](#7-api-qubu--endpoints-и-работа-с-ними)
8. [Пошаговая инструкция деплоя](#8-пошаговая-инструкция-деплоя)
9. [Проблемы и решения (Troubleshooting)](#9-проблемы-и-решения-troubleshooting)
10. [Альтернативные стратегии](#10-альтернативные-стратегии)
11. [Чек-лист готовности](#11-чек-лист-готовности)

---

## 1. Обзор проекта

Система автоматизации учебного процесса для СПО на основе открытых LLM. ИИ-тьютор генерирует конспекты лекций, тесты для самопроверки и поддерживает диалоговый режим.

**Ключевые параметры:**

| Параметр | Значение |
|----------|----------|
| Специальность | 15.02.14 «Оснащение средств автоматизации технологических процессов и производств» |
| Организация | ГБПОУ РО «Сальский индустриальный техникум» (СИТ) |
| Лицензия | Apache 2.0 |
| Модель | Mistral Small 24B-Instruct-2501 |
| Квантование | GGUF Q4_K_M (4-bit, ~15 ГБ) |
| Инференс-фреймворк | llama-cpp-python (CUDA 12.1) |
| Сервисный фреймворк | BentoML 1.2+ |
| GPU на Qubu | RTX 4000 Ada (20 ГБ VRAM) |
| MODEL_PATH | `/workspace/model` |
| Таймаут деплоя | 50 минут |

**Три конечных точки сервиса:**
- `/generate_summary` — структурированный конспект лекции
- `/generate_quiz` — тестовые вопросы с вариантами ответов (easy/medium/hard)
- `/chat` — диалоговый помощник для уточняющих вопросов

---

## 2. Учетные записи и доступы

### Qubu

| Ресурс | Значение |
|--------|----------|
| Email | `REDACTED_EMAIL` |
| Пароль | см. `qubu-deploy/.env.secrets` |
| API-токен | см. `qubu-deploy/.env.secrets` |
| Git-пользователь | `REDACTED_USERNAME` |
| Git-токен | см. `qubu-deploy/.env.secrets` |
| Модель ID | `c9827a6f-be25-40ea-8f80-a71275248188` |

### GitHub

| Ресурс | Значение |
|--------|----------|
| Токен | см. `qubu-deploy/.env.secrets` |
| Репозиторий | `https://github.com/DimaNikolaevi4/al` |
| Локальный путь | `/home/z/my-project/al` |

### Важные замечания по безопасности
- Реальные cred-ы хранятся в `qubu-deploy/.env.secrets` (в .gitignore, НЕ пушится)
- НЕ хранить токены и пароли в файлах, попадающих в git
- Рекомендуется использовать переменные окружения в production
- При потере cred-ов: восстановить через Qubu UI (логин REDACTED_EMAIL)

---

## 3. Ссылки на ресурсы Qubu

### Модель

| Ресурс | URL |
|--------|-----|
| Страница модели | `https://qubu.ai/models/intellektualniy-tyutor-na-osnove-otkrytykh-bolshikh-yazykovykh-modelei-dlya-spo` |
| Редактирование | `https://qubu.ai/models/intellektualniy-tyutor-na-osnove-otkrytykh-bolshikh-yazykovykh-modelei-dlya-spo/edit` |
| Git-репозиторий | `https://git.qubu.ai/REDACTED_USERNAME/ml_model-intellektualniy-tyutor-na-osnove-otkrytykh-bolshikh-yazykovykh-modelei-dlya-spo.git` |

### Датасет

| Ресурс | URL |
|--------|-----|
| Страница датасета | `https://qubu.ai/datasets/intellektualniy-ai-tyutor-dlya-spo` |
| Редактирование | `https://qubu.ai/datasets/intellektualniy-ai-tyutor-dlya-spo/edit` |
| Git-репозиторий | `https://git.qubu.ai/REDACTED_USERNAME/dataset-intellektualniy-ai-tyutor-dlya-spo.git` |

### Git clone с авторизацией

```bash
# Модель (подставить QUBU_GIT_TOKEN из .env.secrets)
git clone https://REDACTED_USERNAME:<QUBU_GIT_TOKEN>@git.qubu.ai/REDACTED_USERNAME/ml_model-intellektualniy-tyutor-na-osnove-otkrytykh-bolshikh-yazykovykh-modelei-dlya-spo.git

# Датасет
git clone https://REDACTED_USERNAME:<QUBU_GIT_TOKEN>@git.qubu.ai/REDACTED_USERNAME/dataset-intellektualniy-ai-tyutor-dlya-spo.git
```

---

## 4. Архитектура решения

### Почему GGUF + llama-cpp-python

На Qubu доступна видеокарта **RTX 4000 Ada с 20 ГБ VRAM**. Полная модель Mistral Small 24B в fp16 требует ~48 ГБ VRAM — не помещается. Решение:

```
Mistral Small 24B-Instruct-2501 (24B, fp16)
    ↓ Квантование Q4_K_M (GGUF)
    ↓ Размер: ~15 ГБ (вмещается в 20 ГБ VRAM + контекст)
    ↓ n_gpu_layers=-1 (все слои на GPU)
    ↓ n_ctx=2048 (контекстное окно)
llama-cpp-python (CUDA 12.1 backend)
    ↓ BentoML Service wrapper
    ↓ 3 API endpoints
AI Tutor Service на Qubu
```

### Почему не transformers + bitsandbytes

1. **bitsandbytes 4-bit** модель все равно требует ~14-15 ГБ VRAM для весов + память под KV cache и активации
2. На RTX 4000 Ada (20 ГБ) это работает, НО при деплое Qubu:
   - bitsandbytes требует компиляцию CUDA-расширений (20-30 минут)
   - transformers скачивает safetensors (~48 ГБ в fp16, хотя загружает в 4-bit)
   - Итого: компиляция + скачивание + загрузка = таймаут 50 минут

3. **GGUF через llama-cpp-python:**
   - Pre-built wheel для CUDA 12.1 (установка за секунды, без компиляции)
   - Один файл ~15 ГБ (скачивание быстрее, чем 48 ГБ safetensors)
   - llama.cpp оптимизирован для инференса на GPU

### Сравнение подходов

| Параметр | transformers + 4-bit | GGUF Q4_K_M + llama.cpp |
|----------|---------------------|-------------------------|
| Размер модели (диск) | ~48 ГБ (safetensors) | ~15 ГБ (1 файл GGUF) |
| VRAM при инференсе | ~14-16 ГБ | ~14-16 ГБ |
| Установка зависимостей | Компиляция bitsandbytes ~20-30 мин | Pre-built wheel, секунды |
| Время деплоя | >50 мин (ТАЙМАУТ!) | ~20-30 мин (должно пройти) |
| Качество генерации | Идентичное | Практически идентичное (Q4_K_M) |

---

## 5. Стратегия развертывания (GGUF + llama-cpp-python)

### Ключевые компоненты

1. **GGUF-файл модели:** `Mistral-Small-24B-Instruct-2501-Q4_K_M.gguf` (~15 ГБ)
   - Источник: `https://huggingface.co/bartowski/Mistral-Small-24B-Instruct-2501-GGUF`
   - Квантование: Q4_K_M (4-bit, 4.58 bits per weight)
   - Автор квантования: bartowski

2. **Pre-built wheel llama-cpp-python:**
   - URL: `https://abetlen.github.io/llama-cpp-python/whl/cu121/`
   - Файл: `llama_cpp_python-0.3.2-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`
   - CUDA версия: 12.1
   - Python версия: 3.11
   - Установка БЕЗ компиляции!

3. **BentoML 1.2+** — фреймворк для инференс-сервиса

### Два варианта загрузки GGUF на Qubu

#### Вариант 1: Startup script (wget из HuggingFace)
- В startup script добавляется `wget -c` для скачивания GGUF
- Проблема: 15 ГБ через wget может не успеть за таймаут 50 мин
- Результат: 3 деплоя упали по таймауту

#### Вариант 2: Git LFS (рекомендованный)
- GGUF загружается в git-репозиторий Qubu через Git LFS
- При деплое модель подтягивается из внутреннего репо Qubu (быстрее, чем HuggingFace)
- Теория: Qubu клонирует свой репо при билде, GGUF уже внутри
- Команды:
  ```bash
  git lfs install
  git lfs track "*.gguf"
  git add .gitattributes
  git add Mistral-Small-24B-Instruct-2501-Q4_K_M.gguf
  git commit -m "Add GGUF model via LFS"
  git push origin main
  ```

---

## 6. Файлы проекта

### `service_gguf.py` — основной сервисный файл

Находится в git-репозитории модели на Qubu. Это файл, который BentoML использует как точку входа.

```python
import os
import glob
import logging
from typing import Any, Dict, List, Optional

from llama_cpp import Llama
from bentoml import Service

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

MODEL_PATH = os.environ.get("MODEL_PATH", "/workspace/model")

service = Service("ai_tutor_gguf")

@service.on_startup
def load_model():
    """Load GGUF model on startup."""
    gguf_files = glob.glob(os.path.join(MODEL_PATH, "*.gguf"))
    if not gguf_files:
        raise FileNotFoundError(f"No GGUF file found in {MODEL_PATH}")
    logger.info("Loading GGUF model: %s", gguf_files[0])
    service.model = Llama(
        model_path=gguf_files[0],
        n_ctx=2048,
        n_gpu_layers=-1,
        verbose=False
    )
    logger.info("Model loaded successfully")

@service.api
def health() -> Dict[str, Any]:
    return {"status": "ok"}

@service.api
def generate_summary(ctx, inputs: Dict[str, Any]) -> Dict[str, Any]:
    lecture_text = inputs.get("lecture_text", "")
    if not lecture_text:
        return {"success": False, "error": "lecture_text is empty"}
    prompt = (
        "Ты — интеллектуальный тьютор для СПО (специальность 15.02.14). "
        "Сделай краткий структурированный конспект лекции с ключевыми терминами.\n\n"
        f"Лекция:\n{lecture_text}\n\nКонспект:"
    )
    response = ctx.model_obj.create(
        prompt=prompt,
        max_tokens=512,
        temperature=0.7,
        top_p=0.9,
    )
    return {"success": True, "summary": response["choices"][0]["text"].strip()}

@service.api
def generate_quiz(ctx, inputs: Dict[str, Any]) -> Dict[str, Any]:
    lecture_text = inputs.get("lecture_text", "")
    difficulty = inputs.get("difficulty", "medium")
    num_questions = inputs.get("num_questions", 5)
    if not lecture_text:
        return {"success": False, "error": "lecture_text is empty"}
    prompt = (
        "Ты — преподаватель СПО (специальность 15.02.14). "
        f"Создай тест из {num_questions} вопросов (сложность: {difficulty}) "
        "с 4 вариантами ответов (A, B, C, D) и правильным ответом.\n\n"
        f"Лекция:\n{lecture_text}\n\nТест:"
    )
    response = ctx.model_obj.create(
        prompt=prompt,
        max_tokens=1024,
        temperature=0.8,
        top_p=0.9,
    )
    return {"success": True, "quiz": response["choices"][0]["text"].strip()}

@service.api
def chat(ctx, inputs: Dict[str, Any]) -> Dict[str, Any]:
    message = inputs.get("message", "")
    history = inputs.get("history", [])
    if not message:
        return {"success": False, "error": "message is empty"}
    # Build conversation from history
    prompt = ""
    for msg in history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            prompt += f"[INST] {content} [/INST]\n"
        else:
            prompt += f"{content}\n"
    prompt += f"[INST] {message} [/INST]"
    response = ctx.model_obj.create(
        prompt=prompt,
        max_tokens=256,
        temperature=0.7,
        top_p=0.9,
    )
    return {"success": True, "answer": response["choices"][0]["text"].strip()}
```

### `bentofile.yaml` — конфигурация BentoML

```yaml
service: "service_gguf:service"
description: "AI Tutor для СПО на базе Mistral Small 24B (GGUF Q4_K_M)"
labels:
  owner: REDACTED_USERNAME
  project: ai-tutor-spo
include:
  - "*.py"
  - "bentofile.yaml"
python:
  packages:
    - bentoml>=1.2.0
  # ВАЖНО: llama-cpp-python устанавливается через startup script
  # из pre-built wheel для CUDA 12.1
```

### `requirements.txt` для Qubu (GGUF вариант)

```
bentoml>=1.2.0
```

> Примечание: `llama-cpp-python` НЕ указан в requirements.txt, т.к. устанавливается через startup script из pre-built wheel. Это связано с тем, что на Qubu нет CUDA toolkit для сборки из исходников, а стандартный wheel с PyPI не включает CUDA-поддержку.

### Startup script (для установки llama-cpp-python из pre-built wheel)

```bash
#!/bin/bash
# Установка llama-cpp-python из pre-built wheel (CUDA 12.1)
pip install --no-cache-dir \
  "https://abetlen.github.io/llama-cpp-python/whl/cu121/llama_cpp_python-0.3.2-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"

# Скачивание GGUF модели (если не через Git LFS)
mkdir -p /workspace/model
wget -c -O /workspace/model/Mistral-Small-24B-Instruct-2501-Q4_K_M.gguf \
  "https://huggingface.co/bartowski/Mistral-Small-24B-Instruct-2501-GGUF/resolve/main/Mistral-Small-24B-Instruct-2501-Q4_K_M.gguf"
```

---

## 7. API Qubu — Endpoints и работа с ними

### Базовый URL
```
https://qubu.ai/api
```

### Авторизация
```
Authorization: Bearer <QUBU_API_TOKEN>
```

Или через cookie после логина (REDACTED_EMAIL).

### Ключевые Endpoints

#### 1. Получение конфигурации инференса

```
GET /api/models/{model_id}/inference/config
```

**Пример:**
```bash
curl -H "Authorization: Bearer <QUBU_API_TOKEN>" \
  "https://qubu.ai/api/models/c9827a6f-be25-40ea-8f80-a71275248188/inference/config"
```

**Ответ:**
```json
{
  "id": "...",
  "code": "import os\nfrom llama_cpp import Llama\n...",
  "requirements": "bentoml>=1.2.0",
  "env": "...",
  "startup_script": "#!/bin/bash\npip install ...",
  " bentofile": "service: ..."
}
```

#### 2. Обновление конфигурации инференса

```
PUT /api/models/{model_id}/inference/config
```

**Важно:** Этот endpoint принимает JSON с полями `code`, `requirements`, `env`, `startup_script`, `bentofile`. Он СОХРАНЯЕТ конфигурацию.

**Пример обновления через curl:**
```bash
curl -X PUT \
  -H "Authorization: Bearer <QUBU_API_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "import os\nfrom llama_cpp import Llama\nfrom bentoml import Service\n...",
    "requirements": "bentoml>=1.2.0",
    "startup_script": "#!/bin/bash\npip install ...",
    "bentofile": "service: ..."
  }' \
  "https://qubu.ai/api/models/c9827a6f-be25-40ea-8f80-a71275248188/inference/config"
```

#### 3. Триггер деплоя

```
POST /api/models/{model_id}/inference/proxy
```

Этот endpoint запускает развертывание модели.

**Пример:**
```bash
curl -X POST \
  -H "Authorization: Bearer <QUBU_API_TOKEN>" \
  "https://qubu.ai/api/models/c9827a6f-be25-40ea-8f80-a71275248188/inference/proxy"
```

#### 4. Статус деплоя

```
GET /api/models/{model_id}/inference/proxy
```

**Ответ:**
```json
{
  "status": "BUILDING",  // или "READY", "FAILED", "STOPPED"
  "url": "https://proxy-..."
}
```

Возможные статусы:
- `BUILDING` — процесс сборки и развертывания (до 50 минут)
- `READY` — модель готова к использованию
- `FAILED` — ошибка при деплое
- `STOPPED` — модель остановлена

### Сломанные/нерабочие Endpoints

| Endpoint | Проблема |
|----------|----------|
| `POST /api/models/{slug}/files` | Возвращает 500 при загрузке файлов |
| `PUT /api/models/{slug}/files` | Возвращает 500 при загрузке файлов |
| Старый deployment-config (PUT) | Возвращает 404 или ok:true но code:null |

**Решение:** Использовать `PUT /api/models/{id}/inference/config` для сохранения конфигурации и Git для загрузки файлов.

### Загрузка кода через браузер (CodeMirror)

API-метод `PUT /api/models/{id}/inference/config` работает, но иногда через curl может быть неудобно для длинного кода. Альтернатива — через браузер:

1. Открыть `https://qubu.ai/models/intellektualniy-tyutor-na-osnove-otkrytykh-bolshikh-yazykovykh-modelei-dlya-spo/edit`
2. Перейти на вкладку «Инференс»
3. Поле кода использует CodeMirror. Для заполнения через DevTools:
   ```javascript
   eval("document.querySelector('.CodeMirror').CodeMirror.setValue('<код сервиса>')")
   ```
   **Важно:** использовать `setValue()` (заменяет), а не `fill()` (добавляет)!
4. Заполнить Requirements, Startup Script, bentofile.yaml аналогично
5. Сохранить (кнопка Save/Deploy)

---

## 8. Пошаговая инструкция деплоя

### Подготовка (один раз)

1. Установить Git LFS (если не установлен):
   ```bash
   # Ubuntu/Debian
   sudo apt install git-lfs
   git lfs install
   ```

2. Склонировать репозиторий модели Qubu:
   ```bash
   git clone https://REDACTED_USERNAME:<QUBU_GIT_TOKEN>@git.qubu.ai/REDACTED_USERNAME/ml_model-intellektualniy-tyutor-na-osnove-otkrytykh-bolshikh-yazykovykh-modelei-dlya-spo.git
   cd ml_model-intellektualniy-tyutor-na-osnove-otkrytykh-bolshikh-yazykovykh-modelei-dlya-spo
   ```

### Загрузка GGUF через Git LFS

3. Настроить LFS для GGUF:
   ```bash
   git lfs install
   git lfs track "*.gguf"
   git add .gitattributes
   ```

4. Скачать GGUF модель (~15 ГБ):
   ```bash
   wget -c -O Mistral-Small-24B-Instruct-2501-Q4_K_M.gguf \
     "https://huggingface.co/bartowski/Mistral-Small-24B-Instruct-2501-GGUF/resolve/main/Mistral-Small-24B-Instruct-2501-Q4_K_M.gguf"
   ```

5. Добавить файлы в репозиторий:
   ```bash
   git add Mistral-Small-24B-Instruct-2501-Q4_K_M.gguf
   git add service_gguf.py bentofile.yaml requirements.txt
   git commit -m "Add GGUF model and service files"
   git push origin main
   ```
   **Внимание:** Пуш 15 ГБ через LFS может занять 15-30 минут.

### Конфигурация на Qubu

6. Обновить конфигурацию инференса. Зайти на страницу редактирования модели:
   ```
   https://qubu.ai/models/intellektualniy-tyutor-na-osnove-otkrytykh-bolshikh-yazykovykh-modelei-dlya-spo/edit
   ```
   Перейти на вкладку «Инференс» и заполнить:

   **Code (service_gguf.py):** Вставить код сервиса (см. раздел 6)

   **Requirements:**
   ```
   bentoml>=1.2.0
   ```

   **Startup Script:**
   ```bash
   #!/bin/bash
   pip install --no-cache-dir \
     "https://abetlen.github.io/llama-cpp-python/whl/cu121/llama_cpp_python-0.3.2-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
   ```

   **bentofile.yaml:**
   ```yaml
   service: "service_gguf:service"
   description: "AI Tutor для СПО (GGUF Q4_K_M)"
   labels:
     owner: REDACTED_USERNAME
   include:
     - "*.py"
     - "bentofile.yaml"
   python:
     packages:
       - bentoml>=1.2.0
   ```

   **Важно:** Если GGUF загружен через Git LFS, startup script НЕ должен содержать `wget` для скачивания модели. Если GGUF НЕ загружен через LFS — добавить wget в startup script.

### Запуск деплоя

7. Через API:
   ```bash
   # Сохранить конфигурацию
   curl -X PUT \
     -H "Authorization: Bearer <QUBU_API_TOKEN>" \
     -H "Content-Type: application/json" \
     -d @config.json \
     "https://qubu.ai/api/models/c9827a6f-be25-40ea-8f80-a71275248188/inference/config"

   # Запустить деплой
   curl -X POST \
     -H "Authorization: Bearer <QUBU_API_TOKEN>" \
     "https://qubu.ai/api/models/c9827a6f-be25-40ea-8f80-a71275248188/inference/proxy"
   ```

8. Или через UI: нажать кнопку «Deploy» на странице модели.

### Мониторинг деплоя

9. Проверять статус:
   ```bash
   curl -H "Authorization: Bearer <QUBU_API_TOKEN>" \
     "https://qubu.ai/api/models/c9827a6f-be25-40ea-8f80-a71275248188/inference/proxy"
   ```

10. Дождаться статус `READY` (обычно 20-30 минут при успешном деплое).

### Тестирование

11. Проверить health endpoint модели (URL из поля proxy response).
12. Протестировать generate_summary, generate_quiz, chat.
13. Проверить время ответа и стабильность.

---

## 9. Проблемы и решения (Troubleshooting)

### Проблема 1: Таймаут деплоя 50 минут (3 раза!)

**Причина:** Компиляция llama-cpp-python из исходников (~20-30 мин) + скачивание GGUF с HuggingFace (~15 ГБ, 10-20 мин) + загрузка модели в VRAM.

**Решение:**
- Использовать pre-built wheel для llama-cpp-python (CUDA 12.1): установка за секунды
- Загрузить GGUF через Git LFS в репо Qubu (подтягивается при билде быстрее, чем с HuggingFace)
- Убрать `CMAKE_ARGS="-DGGML_CUDA=on"` из startup script

### Проблема 2: API загрузки файлов возвращает 500

**Endpoint:** `POST/PUT /api/models/{slug}/files`

**Решение:** Загружать файлы через Git (clone, add, commit, push). API загрузки файлов на Qubu сломан.

### Проблема 3: PUT inference/config возвращает ok:true но code:null

**Причина:** Использовался старый endpoint или неверный формат JSON.

**Решение:** Использовать `PUT /api/models/{id}/inference/config` (с UUID модели, не slug). Передавать в теле `code`, `requirements`, `startup_script`, `bentofile`.

### Проблема 4: CodeMirror fill() добавляет текст вместо замены

**Решение:** Использовать JavaScript `eval()`:
```javascript
eval("document.querySelector('.CodeMirror').CodeMirror.setValue('новый код')")
```
Не использовать `fill()` — он добавляет текст к существующему.

### Проблема 5: bitsandbytes требует компиляции

**Причина:** На Qubu нет CUDA toolkit для сборки из исходников.

**Решение:** Перейти на GGUF + llama-cpp-python с pre-built wheel.

### Проблема 6: Модель не помещается в VRAM

**Причина:** Mistral Small 24B в fp16 = ~48 ГБ, а на Qubu RTX 4000 Ada = 20 ГБ.

**Решение:** Квантование Q4_K_M через GGUF (~15 ГБ). Параметры:
- `n_gpu_layers=-1` — все слои на GPU
- `n_ctx=2048` — достаточно для тьюторских задач
- При необходимости уменьшить n_ctx до 1024 для экономии VRAM

### Проблема 7: RuntimeError при загрузке GGUF

Возможные причины:
- Файл поврежден при скачивании (проверить размер: должен быть ~15 ГБ)
- Неверный путь к файлу (MODEL_PATH)
- Не хватает VRAM

**Диагностика:**
```python
import os, glob
print(os.environ.get("MODEL_PATH", "/workspace/model"))
print(glob.glob("/workspace/model/*.gguf"))
```

---

## 10. Альтернативные стратегии

### Стратегия A: Меньшая модель (запасной вариант)

Если Q4_K_M все равно не успевает по таймауту:
- Использовать **Q3_K_M** (~12 ГБ) — меньше размер, быстрее скачивание
- Или вообще другую модель: **Qwen2.5-14B-Instruct Q4_K_M** (~8.5 ГБ)
- Или **Mistral-7B-Instruct-v0.3 Q5_K_M** (~5.5 ГБ)

URL для альтернативных GGUF:
```
https://huggingface.co/bartowski/Qwen2.5-14B-Instruct-GGUF
https://huggingface.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF
```

### Стратегия B: Разделить билд на этапы

1. Первый деплой: пустой сервис (проверить что BentoML работает)
2. Второй деплой: добавить startup script с установкой wheel
3. Третий деплой: добавить загрузку модели

### Стратегия C: Свой Docker-образ

Если Qubu поддерживает кастомные Docker-образы:
- Собрать образ локально с уже установленным llama-cpp-python
- Загрузить на Docker Hub
- Указать Qubu использовать этот образ

### Стратегия D: Уменьшить контекстное окно

- `n_ctx=2048` → `n_ctx=1024` (экономия ~2 ГБ VRAM)
- `n_ctx=512` (экономия ~4 ГБ VRAM, но короткие ответы)

---

## 11. Чек-лист готовности

Перед деплоем проверить:

- [ ] service_gguf.py содержит корректный код (импорт llama_cpp, bentoml)
- [ ] bentofile.yaml указывает на `service_gguf:service`
- [ ] requirements.txt минимальный (bentoml>=1.2.0)
- [ ] Startup script устанавливает llama-cpp-python из pre-built wheel (CUDA 12.1)
- [ ] GGUF файл загружен через Git LFS ИЛИ startup script содержит wget
- [ ] MODEL_PATH=/workspace/model
- [ ] n_gpu_layers=-1 (все на GPU)
- [ ] n_ctx=2048 (или меньше при нехватке VRAM)
- [ ] Конфигурация сохранена через PUT /api/models/{id}/inference/config
- [ ] Деплой запущен через POST /api/models/{id}/inference/proxy

После успешного деплоя:

- [ ] /health возвращает {"status": "ok"}
- [ ] generate_summary работает на тестовой лекции
- [ ] generate_quiz генерирует вопросы с ответами
- [ ] chat отвечает на вопросы по теме
- [ ] Время ответа приемлемое (<30 сек)
- [ ] Модель не выдает галлюцинаций на базовых вопросах

---

## История изменений

| Дата | Изменение |
|------|-----------|
| 07.05.2026 | Начало работы по плану QUBU_PLAN.md |
| 07.05.2026 | Датасет загружен и настроен (7 файлов через Git LFS) |
| 07.05.2026 | Код сервиса заменен на AI-тьютор (transformers + 4-bit) |
| 07.05.2026 | Первый деплой — ТАЙМАУТ (компиляция + скачивание > 50 мин) |
| 07.05.2026 | Второй деплой — ТАЙМАУТ |
| 07.05.2026 | Третий деплой — ТАЙМАУТ |
| 07-08.05.2026 | Пересмотр стратегии: GGUF + pre-built wheel |
| 08.05.2026 | Создано полное руководство (этот документ) |
