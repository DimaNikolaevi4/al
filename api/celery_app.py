"""
Celery-приложение и определение асинхронных задач ИИ-тьютора.

Содержит:
  - Экземпляр Celery с брокером/бэкендом Redis.
  - Три типа задач: генерация конспекта, генерация теста, чат.
  - Singleton-загрузчик модели (модель загружается один раз на воркер,
    reused для всех последующих задач).
  - Лимиты по времени, автоматический retry при ошибках.
"""
# Автор: Команда ИИ СИТ (Бардаков Д.Н., Мышанская Н.Г.)
# Лицензия: Apache 2.0

from __future__ import annotations

import logging
import os
import sys
import threading
from typing import Any, Optional

from celery import Celery, states
from celery.exceptions import Retry

# Добавляем корень проекта в sys.path, чтобы импорт tutor работал
# как при запуске через celery, так и через uvicorn.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from api.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Celery instance
# ---------------------------------------------------------------------------
celery_app = Celery(
    "ai_tutor",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Moscow",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,          # повторная попытка при падении воркера
    worker_prefetch_multiplier=1,  # одна задача за раз (модель занимает память)
    result_expires=3600,          # TTL результатов — 1 час
)

# ---------------------------------------------------------------------------
# Model singleton — lazy init per worker process
# ---------------------------------------------------------------------------
_tutor_instance: Optional[Any] = None  # IntelligentTutor
_tutor_lock = threading.Lock()


def _get_tutor():
    """Вернуть singleton-экземпляр IntelligentTutor.

    Модель загружается лениво при первом вызове из любого потока
    внутри процесса воркера и переиспользуется для всех последующих задач.
    """
    global _tutor_instance
    if _tutor_instance is not None:
        return _tutor_instance

    with _tutor_lock:
        # Double-checked locking
        if _tutor_instance is not None:
            return _tutor_instance

        logger.info("Загрузка модели (singleton) в воркере Celery …")
        from tutor import IntelligentTutor  # noqa: delayed import

        _tutor_instance = IntelligentTutor(
            base_model_id=settings.MODEL_PATH,
            adapter_path=settings.ADAPTER_PATH,
            device_map=settings.DEVICE_MAP,
        )
        logger.info("Модель загружена и готова к обработке задач.")
        return _tutor_instance


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

_BASE_TASK_OPTIONS = dict(
    soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    time_limit=settings.CELERY_TASK_TIME_LIMIT,
    max_retries=settings.CELERY_TASK_MAX_RETRIES,
    default_retry_delay=settings.CELERY_TASK_RETRY_DELAY,
    acks_late=True,
)


@celery_app.task(bind=True, **_BASE_TASK_OPTIONS, name="tasks.generate_summary")
def generate_summary_task(
    self,
    lecture_text: str,
    params: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Асинхронная генерация конспекта лекции.

    Args:
        lecture_text: Полный текст лекции.
        params: Опциональные параметры генерации
                (max_new_tokens, temperature, top_p, top_k, do_sample).

    Returns:
        Словарь с ключами ``summary`` (str) и ``meta`` (dict).
    """
    self.update_state(state=states.STARTED, meta={"step": "loading_model"})
    tutor = _get_tutor()

    self.update_state(state=states.STARTED, meta={"step": "generating"})
    params = params or {}
    summary = tutor.generate_lecture_summary(
        lecture_text,
        max_new_tokens=params.get("max_new_tokens", 512),
        temperature=params.get("temperature", 0.7),
        top_p=params.get("top_p", 0.9),
        top_k=params.get("top_k", 50),
        do_sample=params.get("do_sample", True),
    )
    return {
        "summary": summary,
        "meta": {"type": "summary", "input_length": len(lecture_text)},
    }


@celery_app.task(bind=True, **_BASE_TASK_OPTIONS, name="tasks.generate_quiz")
def generate_quiz_task(
    self,
    lecture_text: str,
    params: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Асинхронная генерация теста по лекции.

    Args:
        lecture_text: Текст лекции.
        params: Опциональные параметры — ``num_questions`` (int),
                ``difficulty`` (easy/medium/hard).

    Returns:
        Словарь с ключами ``quiz`` (str) и ``meta`` (dict).
    """
    self.update_state(state=states.STARTED, meta={"step": "loading_model"})
    tutor = _get_tutor()

    self.update_state(state=states.STARTED, meta={"step": "generating"})
    params = params or {}
    quiz = tutor.generate_quiz(
        lecture_text,
        num_questions=params.get("num_questions", 5),
        difficulty=params.get("difficulty", "medium"),
    )
    return {
        "quiz": quiz,
        "meta": {
            "type": "quiz",
            "num_questions": params.get("num_questions", 5),
            "difficulty": params.get("difficulty", "medium"),
        },
    }


@celery_app.task(bind=True, **_BASE_TASK_OPTIONS, name="tasks.chat")
def chat_task(
    self,
    message: str,
    history: Optional[list[dict[str, str]]] = None,
) -> dict[str, Any]:
    """Асинхронный диалог с тьютором.

    Args:
        message: Сообщение пользователя.
        history: История диалога в формате
                 ``[{"role": "user"|"assistant", "content": "..."}]``.

    Returns:
        Словарь с ключами ``response`` (str) и ``meta`` (dict).
    """
    self.update_state(state=states.STARTED, meta={"step": "loading_model"})
    tutor = _get_tutor()

    self.update_state(state=states.STARTED, meta={"step": "generating"})
    response = tutor.chat(
        user_message=message,
        conversation_history=history or [],
    )
    return {
        "response": response,
        "meta": {"type": "chat", "history_length": len(history or [])},
    }


# ---------------------------------------------------------------------------
# Error handler (fallback — логирует и позволяет Celery повторить)
# ---------------------------------------------------------------------------

@celery_app.task(base=celery_app.Task)
def on_failure(self, exc, task_id, args, kwargs, einfo):
    """Глобальный обработчик ошибок Celery-задач."""
    logger.error(
        "Задача %s завершилась с ошибкой: %s",
        task_id,
        exc,
        exc_info=True,
    )
