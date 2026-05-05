"""
Централизованная конфигурация API и Celery-воркеров.

Загружает все параметры из переменных окружения с разумными значениями
по умолчанию для локальной разработки. Использует pydantic-settings
для валидации и типизации.
"""

from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Конфигурация приложения, загружаемая из переменных окружения.

    Все параметры имеют значения по умолчанию, подходящие для
    локальной разработки. Для продакшена переопределите через .env
    или переменные окружения.
    """

    # --- Модель ---
    MODEL_PATH: str = "mistralai/Mistral-Small-24B-Instruct-2501"
    ADAPTER_PATH: Optional[str] = None
    DEVICE_MAP: str = "auto"

    # --- Redis / Celery ---
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""
    CELERY_TASK_SOFT_TIME_LIMIT: int = 120
    CELERY_TASK_TIME_LIMIT: int = 180
    CELERY_TASK_MAX_RETRIES: int = 1
    CELERY_TASK_RETRY_DELAY: int = 5

    # --- API ---
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    API_KEY: Optional[str] = None
    MAX_LECTURE_LENGTH: int = 50000
    RATE_LIMIT_PER_MINUTE: int = 30

    # --- Логирование ---
    LOG_LEVEL: str = "INFO"

    # --- HuggingFace ---
    HUGGINGFACE_TOKEN: Optional[str] = None

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # Celery URL по умолчанию = Redis URL
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = self.REDIS_URL
        if not self.CELERY_RESULT_BACKEND:
            self.CELERY_RESULT_BACKEND = self.REDIS_URL

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Глобальный синглтон
settings = Settings()
