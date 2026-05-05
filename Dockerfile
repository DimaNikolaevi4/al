# =============================================================================
# ИИ-тьютор для СПО — Dockerfile
# =============================================================================
# Multi-stage build. GPU-agnostic: драйверы монтируются с хоста.
# Сборка:  docker build -t ai-tutor .
# Запуск:  docker run --gpus all -p 8000:8000 ai-tutor
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: builder — компиляция зависимостей
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# Системные зависимости для компиляции Python-пакетов
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Дополнительные зависимости для API и Celery
RUN pip install --no-cache-dir --prefix=/install \
    fastapi>=0.104.0 \
    uvicorn[standard]>=0.24.0 \
    celery[redis]>=5.3.0 \
    redis>=5.0.0 \
    pydantic>=2.5.0 \
    python-dotenv>=1.0.0 \
    httpx>=0.25.0

# ---------------------------------------------------------------------------
# Stage 2: runtime — минимальный образ
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

LABEL maintainer="Команда ИИ СИТ (Бардаков Д.Н., Мышанская Н.Г.)"
LABEL description="ИИ-тьютор для СПО — FastAPI + Celery"
LABEL version="0.2.0"
LABEL org.opencontainers.image.source="https://github.com/ai-tutor-spo"

WORKDIR /app

# Минимальные runtime-зависимости (без компиляторов)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        && rm -rf /var/lib/apt/lists/*

# Копируем собранные Python-пакеты из builder
COPY --from=builder /install /usr/local

# Копируем исходный код проекта
COPY . .

# Директория для кэша HuggingFace (монтируется как volume при необходимости)
ENV HF_HOME=/app/.cache/huggingface
ENV TRANSFORMERS_CACHE=/app/.cache/huggingface
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Healthcheck — проверяем, что API отвечает на /health
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Команда по умолчанию — FastAPI-сервер (перезаписывается в docker-compose для celery-worker)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
