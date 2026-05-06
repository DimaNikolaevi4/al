"""
Pydantic models for all API request/response schemas.

Defines strict input validation models and consistent response wrappers
used across all API endpoints.
"""
# Автор: Команда ИИ СИТ (Бардаков Д.Н., Мышанская Н.Г.)
# Лицензия: Apache 2.0

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Generic response wrapper
# ---------------------------------------------------------------------------

T = TypeVar("T")


class MetaInfo(BaseModel):
    """Метаданные ответа: время генерации, количество токенов и т.д."""

    generation_time_seconds: float = Field(
        description="Время генерации ответа в секундах",
        ge=0.0,
    )
    input_tokens: Optional[int] = Field(
        default=None,
        description="Количество входных токенов (если доступно)",
    )
    output_tokens: Optional[int] = Field(
        default=None,
        description="Количество выходных токенов (если доступно)",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Временная метка ответа (UTC)",
    )


class ApiResponse(BaseModel, Generic[T]):
    """Универсальная обёртка ответа API.

    Каждый endpoint возвращает объект с полями:
    - success: признак успешности операции
    - data: полезная нагрузка (тип T)
    - error: описание ошибки или None
    - meta: метаданные запроса
    """

    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    meta: MetaInfo


class ValidationErrorResponse(BaseModel):
    """Модель ответа при ошибке валидации входных данных (HTTP 422)."""

    success: bool = False
    error: str = Field(description="Описание ошибки валидации")
    details: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Детали ошибок по полям",
    )


# ---------------------------------------------------------------------------
# Shared / chat models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    """Сообщение в истории диалога."""

    role: str = Field(
        description="Роль отправителя: 'user' или 'assistant'",
    )
    content: str = Field(
        min_length=1,
        description="Содержимое сообщения",
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("user", "assistant"):
            raise ValueError("Роль должна быть 'user' или 'assistant'")
        return v


# ---------------------------------------------------------------------------
# Summary endpoint
# ---------------------------------------------------------------------------

class SummaryRequest(BaseModel):
    """Запрос на генерацию конспекта лекции.

    Пример:
        >>> req = SummaryRequest(lecture_text="Тема: Основы автоматики...")
        >>> req.temperature = 0.5
    """

    lecture_text: str = Field(
        min_length=1,
        description="Текст лекции для конспектирования",
    )
    max_new_tokens: int = Field(
        default=512,
        ge=64,
        le=2048,
        description="Максимальное количество новых токенов для генерации (64–2048)",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.1,
        le=2.0,
        description="Температура сэмплирования (0.1–2.0)",
    )


class SummaryData(BaseModel):
    """Данные ответа генерации конспекта."""

    summary: str = Field(description="Сгенерированный конспект лекции")
    lecture_length_chars: int = Field(description="Длина исходного текста лекции (символы)")
    summary_length_chars: int = Field(description="Длина конспекта (символы)")


# ---------------------------------------------------------------------------
# Quiz endpoint
# ---------------------------------------------------------------------------

class QuizRequest(BaseModel):
    """Запрос на генерацию теста по лекции.

    Пример:
        >>> req = QuizRequest(lecture_text="Тема: ПЛК...", num_questions=10, difficulty="hard")
    """

    lecture_text: str = Field(
        min_length=1,
        description="Текст лекции для генерации вопросов",
    )
    num_questions: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Количество вопросов (1–20)",
    )
    difficulty: str = Field(
        default="medium",
        description="Уровень сложности: 'easy', 'medium' или 'hard'",
    )

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        if v not in ("easy", "medium", "hard"):
            raise ValueError(
                "Уровень сложности должен быть одним из: 'easy', 'medium', 'hard'"
            )
        return v


class QuizData(BaseModel):
    """Данные ответа генерации теста."""

    quiz: str = Field(description="Сгенерированный тест с вопросами и вариантами ответов")
    num_questions: int = Field(description="Запрошенное количество вопросов")
    difficulty: str = Field(description="Уровень сложности теста")


# ---------------------------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """Запрос на диалог с тьютором.

    Пример:
        >>> req = ChatRequest(message="Объясни, что такое ПИД-регулятор")
        >>> req.history = [ChatMessage(role="user", content="Привет")]
    """

    message: str = Field(
        min_length=1,
        description="Сообщение пользователя (вопрос или уточнение)",
    )
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="История диалога (предыдущие сообщения)",
    )


class ChatData(BaseModel):
    """Данные ответа диалога."""

    answer: str = Field(description="Ответ тьютора")
    history_length: int = Field(description="Количество сообщений в истории диалога")


# ---------------------------------------------------------------------------
# System / health endpoints
# ---------------------------------------------------------------------------

class GPUInfo(BaseModel):
    """Информация о GPU."""

    available: bool = Field(description="Доступность GPU")
    name: Optional[str] = Field(default=None, description="Название GPU")
    vram_free_mb: Optional[float] = Field(default=None, description="Свободная VRAM (МБ)")
    vram_total_mb: Optional[float] = Field(default=None, description="Общая VRAM (МБ)")


class HealthData(BaseModel):
    """Данные проверки работоспособности."""

    status: str = Field(description="Статус сервиса: 'ok' или 'degraded'")
    model_loaded: bool = Field(description="Загружена ли модель в память")
    model_id: Optional[str] = Field(default=None, description="Идентификатор модели")
    adapter_loaded: bool = Field(default=False, description="Загружен ли LoRA-адаптер")
    gpu: GPUInfo = Field(description="Информация о GPU")


class ModelInfoData(BaseModel):
    """Информация о загруженной модели."""

    model_id: str = Field(description="Идентификатор базовой модели")
    adapter_path: Optional[str] = Field(default=None, description="Путь к LoRA-адаптерам")
    parameters_count: Optional[int] = Field(
        default=None, description="Количество параметров модели"
    )
    adapter_loaded: bool = Field(default=False, description="Загружен ли LoRA-адаптер")
    dtype: str = Field(default="float16", description="Тип данных весов модели")


class StatsData(BaseModel):
    """Статистика использования API."""

    total_requests: int = Field(description="Общее количество запросов")
    by_endpoint: dict[str, int] = Field(
        description="Количество запросов по каждому endpoint"
    )
    by_day: dict[str, int] = Field(
        description="Количество запросов по дням (YYYY-MM-DD)"
    )
