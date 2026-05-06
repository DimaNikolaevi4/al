"""
Generation endpoints — summary, quiz, and chat.

These endpoints proxy requests to the :class:`IntelligentTutor` instance
stored on the FastAPI app state.
"""
# Автор: Команда ИИ СИТ (Бардаков Д.Н., Мышанская Н.Г.)
# Лицензия: Apache 2.0

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request

from api.config import settings
from api.models import (
    ApiResponse,
    ChatData,
    ChatRequest,
    ChatMessage,
    MetaInfo,
    QuizData,
    QuizRequest,
    SummaryData,
    SummaryRequest,
)

if TYPE_CHECKING:
    from tutor import IntelligentTutor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_tutor(request: Request) -> IntelligentTutor:
    """Retrieve the tutor instance from application state."""
    tutor = request.app.state.tutor
    if tutor is None:
        raise RuntimeError("Модель не загружена. Сервер не готов к обработке запросов.")
    return tutor


def _record_request(request: Request, endpoint: str) -> None:
    """Increment in-memory usage counters."""
    stats = request.app.state.stats
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stats["total_requests"] += 1
    stats["by_endpoint"][endpoint] = stats["by_endpoint"].get(endpoint, 0) + 1
    stats["by_day"][today] = stats["by_day"].get(today, 0) + 1


# ---------------------------------------------------------------------------
# POST /api/v1/generate-summary
# ---------------------------------------------------------------------------

@router.post(
    "/generate-summary",
    response_model=ApiResponse[SummaryData],
    summary="Сгенерировать конспект лекции",
    description="Принимает текст лекции и возвращает структурированный конспект.",
)
async def generate_summary(
    body: SummaryRequest,
    request: Request,
) -> ApiResponse[SummaryData]:
    """Генерация структурированного конспекта лекции для студентов СПО."""
    _record_request(request, "/api/v1/generate-summary")

    # Enforce maximum lecture length
    if len(body.lecture_text) > settings.MAX_LECTURE_LENGTH:
        return ApiResponse[SummaryData](
            success=False,
            error=(
                f"Текст лекции превышает максимально допустимую длину "
                f"({len(body.lecture_text)} > {settings.MAX_LECTURE_LENGTH} символов). "
                "Пожалуйста, сократите текст."
            ),
            meta=MetaInfo(generation_time_seconds=0.0),
        )

    tutor = _get_tutor(request)
    t0 = time.perf_counter()

    try:
        summary: str = tutor.generate_lecture_summary(
            lecture_text=body.lecture_text,
            max_new_tokens=body.max_new_tokens,
            temperature=body.temperature,
        )
    except ValueError as exc:
        logger.warning("Validation error in generate_summary: %s", exc)
        return ApiResponse[SummaryData](
            success=False,
            error=str(exc),
            meta=MetaInfo(generation_time_seconds=time.perf_counter() - t0),
        )
    except Exception as exc:
        logger.exception("Unexpected error in generate_summary")
        return ApiResponse[SummaryData](
            success=False,
            error=f"Ошибка при генерации конспекта: {exc}",
            meta=MetaInfo(generation_time_seconds=time.perf_counter() - t0),
        )

    elapsed = time.perf_counter() - t0
    return ApiResponse[SummaryData](
        success=True,
        data=SummaryData(
            summary=summary,
            lecture_length_chars=len(body.lecture_text),
            summary_length_chars=len(summary),
        ),
        meta=MetaInfo(generation_time_seconds=elapsed),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/generate-test
# ---------------------------------------------------------------------------

@router.post(
    "/generate-test",
    response_model=ApiResponse[QuizData],
    summary="Сгенерировать тест по лекции",
    description="Принимает текст лекции и параметры теста, возвращает вопросы с вариантами ответов.",
)
async def generate_test(
    body: QuizRequest,
    request: Request,
) -> ApiResponse[QuizData]:
    """Генерация теста для самопроверки по содержанию лекции."""
    _record_request(request, "/api/v1/generate-test")

    if len(body.lecture_text) > settings.MAX_LECTURE_LENGTH:
        return ApiResponse[QuizData](
            success=False,
            error=(
                f"Текст лекции превышает максимально допустимую длину "
                f"({len(body.lecture_text)} > {settings.MAX_LECTURE_LENGTH} символов). "
                "Пожалуйста, сократите текст."
            ),
            meta=MetaInfo(generation_time_seconds=0.0),
        )

    tutor = _get_tutor(request)
    t0 = time.perf_counter()

    try:
        quiz: str = tutor.generate_quiz(
            lecture_text=body.lecture_text,
            num_questions=body.num_questions,
            difficulty=body.difficulty,
        )
    except ValueError as exc:
        logger.warning("Validation error in generate_test: %s", exc)
        return ApiResponse[QuizData](
            success=False,
            error=str(exc),
            meta=MetaInfo(generation_time_seconds=time.perf_counter() - t0),
        )
    except Exception as exc:
        logger.exception("Unexpected error in generate_test")
        return ApiResponse[QuizData](
            success=False,
            error=f"Ошибка при генерации теста: {exc}",
            meta=MetaInfo(generation_time_seconds=time.perf_counter() - t0),
        )

    elapsed = time.perf_counter() - t0
    return ApiResponse[QuizData](
        success=True,
        data=QuizData(
            quiz=quiz,
            num_questions=body.num_questions,
            difficulty=body.difficulty,
        ),
        meta=MetaInfo(generation_time_seconds=elapsed),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/chat
# ---------------------------------------------------------------------------

@router.post(
    "/chat",
    response_model=ApiResponse[ChatData],
    summary="Диалог с тьютором",
    description="Отправляет сообщение тьютору и получает ответ. Поддерживает историю диалога.",
)
async def chat(
    body: ChatRequest,
    request: Request,
) -> ApiResponse[ChatData]:
    """Диалог с ИИ-тьютором по материалам лекций."""
    _record_request(request, "/api/v1/chat")

    tutor = _get_tutor(request)
    t0 = time.perf_counter()

    # Convert ChatMessage models to plain dicts for the tutor
    history_dicts: list[dict[str, str]] | None = None
    if body.history:
        history_dicts = [{"role": m.role, "content": m.content} for m in body.history]

    try:
        answer: str = tutor.chat(
            user_message=body.message,
            conversation_history=history_dicts,
        )
    except ValueError as exc:
        logger.warning("Validation error in chat: %s", exc)
        return ApiResponse[ChatData](
            success=False,
            error=str(exc),
            meta=MetaInfo(generation_time_seconds=time.perf_counter() - t0),
        )
    except Exception as exc:
        logger.exception("Unexpected error in chat")
        return ApiResponse[ChatData](
            success=False,
            error=f"Ошибка при обработке сообщения: {exc}",
            meta=MetaInfo(generation_time_seconds=time.perf_counter() - t0),
        )

    elapsed = time.perf_counter() - t0
    return ApiResponse[ChatData](
        success=True,
        data=ChatData(
            answer=answer,
            history_length=len(body.history),
        ),
        meta=MetaInfo(generation_time_seconds=elapsed),
    )
