"""
Утилиты для отправки задач в Celery и проверки их статуса.

Этот модуль — единственная точка входа для маршрутов FastAPI,
через которую задачи ставятся в очередь и запрашиваются результаты.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from celery.result import AsyncResult

from api.celery_app import celery_app, chat_task, generate_quiz_task, generate_summary_task

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Submit helpers
# ---------------------------------------------------------------------------


def submit_summary(
    lecture_text: str,
    params: Optional[dict[str, Any]] = None,
) -> str:
    """Поставить задачу генерации конспекта в очередь.

    Args:
        lecture_text: Текст лекции.
        params: Опциональные параметры генерации.

    Returns:
        ID задачи (task_id) для последующего отслеживания.
    """
    logger.info("Постановка задачи generate_summary в очередь")
    result: AsyncResult = generate_summary_task.delay(lecture_text, params)
    return result.id


def submit_quiz(
    lecture_text: str,
    params: Optional[dict[str, Any]] = None,
) -> str:
    """Поставить задачу генерации теста в очередь.

    Args:
        lecture_text: Текст лекции.
        params: Опциональные параметры (num_questions, difficulty).

    Returns:
        ID задачи.
    """
    logger.info("Постановка задачи generate_quiz в очередь")
    result: AsyncResult = generate_quiz_task.delay(lecture_text, params)
    return result.id


def submit_chat(
    message: str,
    history: Optional[list[dict[str, str]]] = None,
) -> str:
    """Поставить задачу диалога с тьютором в очередь.

    Args:
        message: Сообщение пользователя.
        history: История диалога.

    Returns:
        ID задачи.
    """
    logger.info("Постановка задачи chat в очередь")
    result: AsyncResult = chat_task.delay(message, history)
    return result.id


# ---------------------------------------------------------------------------
# Status checking
# ---------------------------------------------------------------------------

# Маппинг внутренних статусов Celery к человекочитаемым
_STATE_LABELS = {
    "PENDING": "queued",
    "STARTED": "processing",
    "SUCCESS": "completed",
    "FAILURE": "failed",
    "REVOKED": "cancelled",
    "RETRY": "retrying",
}


def get_task_status(task_id: str) -> dict[str, Any]:
    """Получить текущий статус задачи по её ID.

    Args:
        task_id: Идентификатор Celery-задачи.

    Returns:
        Словарь с полями:
          - ``task_id`` — переданный ID;
          - ``status`` — человекочитаемый статус (queued / processing / completed / failed);
          - ``celery_state`` — оригинальный статус Celery (PENDING / STARTED / …);
          - ``result`` — результат задачи (при status == «completed»);
          - ``error``   — текст ошибки (при status == «failed»).
    """
    result: AsyncResult = AsyncResult(task_id, app=celery_app)
    celery_state = result.state

    response: dict[str, Any] = {
        "task_id": task_id,
        "status": _STATE_LABELS.get(celery_state, celery_state.lower()),
        "celery_state": celery_state,
    }

    if celery_state == "SUCCESS":
        response["result"] = result.result
    elif celery_state == "FAILURE":
        exc = result.result
        response["error"] = str(exc) if exc is not None else "Неизвестная ошибка"
    # STARTED — можно передать мета-данные, если они были установлены через update_state
    elif celery_state == "STARTED" and result.info:
        response["meta"] = result.info

    return response
