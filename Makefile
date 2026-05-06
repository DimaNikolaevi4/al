# =============================================================================
# ИИ-тьютор для СПО — Makefile
# =============================================================================
# Использование:
#   make help        — показать все цели
#   make install     — создать venv и установить зависимости
#   make lint        — проверить стиль кода (ruff)
#   make test        — запустить тесты (pytest)
#   make deploy      — развернуть через scripts/deploy.sh
#   make up          — docker compose up (production)
#   make down        — docker compose down
# =============================================================================

.PHONY: help install venv lint test train deploy up down logs backup \
        smoke-test gpu-check clean

# ---------------------------------------------------------------------------
# Переменные
# ---------------------------------------------------------------------------
VENV        := .venv
PYTHON      := $(VENV)/bin/python
PIP         := $(VENV)/bin/pip
DOCKER_COMPOSE := docker compose

# ---------------------------------------------------------------------------
# Основные цели
# ---------------------------------------------------------------------------

help: ## Показать справку по целям
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Окружение / Environment
# ---------------------------------------------------------------------------

venv: ## Создать виртуальное окружение
	python3 -m venv $(VENV)

install: venv ## Создать venv и установить зависимости
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

# ---------------------------------------------------------------------------
# Качество кода / Code quality
# ---------------------------------------------------------------------------

lint: ## Проверить стиль кода (ruff)
	$(PYTHON) -m pip install -q ruff 2>/dev/null || true
	$(PYTHON) -m ruff check . --line-length=120
	$(PYTHON) -m ruff format --check .

format: ## Автоформатирование кода (ruff)
	$(PYTHON) -m pip install -q ruff 2>/dev/null || true
	$(PYTHON) -m ruff check . --line-length=120 --fix
	$(PYTHON) -m ruff format .

# ---------------------------------------------------------------------------
# Тестирование / Testing
# ---------------------------------------------------------------------------

test: ## Запустить тесты (pytest)
	$(PYTHON) -m pytest test_tutor.py -v --tb=short

smoke-test: ## Smoke test API (требует запущенный сервер)
	$(PYTHON) scripts/smoke_test.py

# ---------------------------------------------------------------------------
# Обучение / Training
# ---------------------------------------------------------------------------

train: ## Запустить дообучение (debug-режим)
	$(PYTHON) train.py --mode debug

train-full: ## Запустить полное дообучение
	$(PYTHON) train.py --mode full

# ---------------------------------------------------------------------------
# Docker / Deployment
# ---------------------------------------------------------------------------

up: ## Запустить сервисы (docker compose up -d)
	$(DOCKER_COMPOSE) up -d

down: ## Остановить сервисы
	$(DOCKER_COMPOSE) down

logs: ## Логи всех сервисов (tail -f)
	$(DOCKER_COMPOSE) logs -f

deploy: ## Полное развёртывание (через deploy.sh)
	bash scripts/deploy.sh

backup: ## Бэкап адаптеров и логов
	bash scripts/backup.sh

# ---------------------------------------------------------------------------
# Утилиты / Utilities
# ---------------------------------------------------------------------------

gpu-check: ## Проверить наличие GPU
	bash scripts/detect_gpu.sh

clean: ## Очистить артефакты (кэш, __pycache__, логи)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache
	rm -f tutor.log
