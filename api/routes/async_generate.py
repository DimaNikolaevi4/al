"""
Асинхронные REST-эндпоинты для генерации контента ИИ-тьютором.

Все эндпоинсы возвращают task_id немедленно; клиент опрашивает
``GET /async/status/{task_id}`` для получения результата.
"""
# Автор: Команда ИИ СИТ (Бардаков Д.Н., Мышанская Н.Г.)
# Лицензия: Apache 2.0

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.tasks import get_task_status, submit_chat, submit_quiz, submit_summary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/async", tags=["async-generation"])


# ---------------------------------------------------------------------------
# Pydantic models (request / response)
# ---------------------------------------------------------------------------


class SummaryRequest(BaseModel):
    """Запрос на асинхронную генерацию конспекта."""

    lecture_text: str = Field(
        ...,
        min_length=10,
        description="Текст лекции для конспектирования",
    )
    max_new_tokens: int = Field(default=512, ge=64, le=2048)
    temperature: float = Field(default=0.7, ge=0.1, le=2.0)
    top_p: float = Field(default=0.9, ge=0.1, le=1.0)
    top_k: int = Field(default=50, ge=0, le=200)


class QuizRequest(BaseModel):
    """Запрос на асинхронную генерацию теста."""

    lecture_text: str = Field(
        ...,
        min_length=10,
        description="Текст лекции для генерации теста",
    )
    num_questions: int = Field(default=5, ge=1, le=20)
    difficulty: str = Field(default="medium", pattern=r"^(easy|medium|hard)$")


class ChatRequest(BaseModel):
    """Запрос на асинхронный диалог с тьютором."""

    message: str = Field(
        ...,
        min_length=1,
        description="Сообщение пользователя",
    )
    history: Optional[list[dict[str, str]]] = Field(
        default=None,
        description="История диалога: [{\"role\": \"user|assistant\", \"content\": \"...\"}]",
    )


class TaskSubmitted(BaseModel):
    """Ответ при успешной постановке задачи в очередь."""

    task_id: str = Field(..., description="Идентификатор задачи для отслеживания статуса")


class TaskStatusResponse(BaseModel):
    """Ответ с текущим статусом задачи."""

    task_id: str
    status: str = Field(..., description="queued | processing | completed | failed")
    celery_state: Optional[str] = Field(None, description="Оригинальный статус Celery")
    result: Optional[Any] = Field(None, description="Результат задачи (при status=completed)")
    error: Optional[str] = Field(None, description="Текст ошибки (при status=failed)")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/generate-summary",
    response_model=TaskSubmitted,
    summary="Асинхронная генерация конспекта",
    description="Ставит задачу генерации конспекта в очередь и возвращает task_id.",
    status_code=202,
)
async def async_generate_summary(body: SummaryRequest) -> TaskSubmitted:
    """Поставить задачу генерации конспекта лекции."""
    params = body.model_dump(exclude={"lecture_text"})
    try:
        task_id = submit_summary(lecture_text=body.lecture_text, params=params)
    except Exception as exc:
        logger.error("Ошибка постановки задачи generate_summary: %s", exc)
        raise HTTPException(status_code=500, detail="Не удалось поставить задачу в очередь") from exc

    logger.info("Задача generate_summary поставлена: %s", task_id)
    return TaskSubmitted(task_id=task_id)


@router.post(
    "/generate-test",
    response_model=TaskSubmitted,
    summary="Асинхронная генерация теста",
    description="Ставит задачу генерации теста в очередь и возвращает task_id.",
    status_code=202,
)
async def async_generate_test(body: QuizRequest) -> TaskSubmitted:
    """Поставить задачу генерации теста по лекции."""
    params = body.model_dump(exclude={"lecture_text"})
    try:
        task_id = submit_quiz(lecture_text=body.lecture_text, params=params)
    except Exception as exc:
        logger.error("Ошибка постановки задачи generate_quiz: %s", exc)
        raise HTTPException(status_code=500, detail="Не удалось поставить задачу в очередь") from exc

    logger.info("Задача generate_quiz поставлена: %s", task_id)
    return TaskSubmitted(task_id=task_id)


@router.post(
    "/chat",
    response_model=TaskSubmitted,
    summary="Асинхронный диалог с тьютором",
    description="Ставит задачу диалога в очередь и возвращает task_id.",
    status_code=202,
)
async def async_chat(body: ChatRequest) -> TaskSubmitted:
    """Поставить задачу диалога с ИИ-тьютором."""
    try:
        task_id = submit_chat(message=body.message, history=body.history)
    except Exception as exc:
        logger.error("Ошибка постановки задачи chat: %s", exc)
        raise HTTPException(status_code=500, detail="Не удалось поставить задачу в очередь") from exc

    logger.info("Задача chat поставлена: %s", task_id)
    return TaskSubmitted(task_id=task_id)


@router.get(
    "/status/{task_id}",
    response_model=TaskStatusResponse,
    summary="Статус задачи",
    description="Возвращает текущий статус и результат (если готов) задачи по task_id.",
)
async def task_status(task_id: str) -> TaskStatusResponse:
    """Получить статус ранее поставленной задачи."""
    status_info = get_task_status(task_id)
    return TaskStatusResponse(**status_info)
