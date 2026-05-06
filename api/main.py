"""
FastAPI application entry point.

Creates the application, registers middleware, exception handlers,
and manages the model lifecycle via an async lifespan context manager.
"""
# Автор: Команда ИИ СИТ (Бардаков Д.Н., Мышанская Н.Г.)
# Лицензия: Apache 2.0

from __future__ import annotations

import logging
import sys
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.config import settings
from api.routes import async_generate, generate, system

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — model loading / cleanup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load the model on startup and release resources on shutdown.

    The :class:`IntelligentTutor` instance is stored on ``app.state.tutor``
    so that route handlers can access it via ``request.app.state.tutor``.
    """
    from tutor import IntelligentTutor, ModelLoadError

    # --- startup ---
    logger.info("Загрузка модели ИИ-тьютора...")
    logger.info("MODEL_PATH = %s", settings.MODEL_PATH)
    if settings.ADAPTER_PATH:
        logger.info("ADAPTER_PATH = %s", settings.ADAPTER_PATH)

    # Initialise in-memory usage stats
    app.state.stats = {
        "total_requests": 0,
        "by_endpoint": {},
        "by_day": {},
    }

    try:
        app.state.tutor = IntelligentTutor(
            base_model_id=settings.MODEL_PATH,
            adapter_path=settings.ADAPTER_PATH,
        )
        logger.info("Модель успешно загружена и готова к работе.")
    except ModelLoadError as exc:
        logger.critical("Не удалось загрузить модель: %s", exc)
        if exc.original_error:
            logger.debug("Исходная ошибка: %s", exc.original_error)
        app.state.tutor = None
        # Application starts in degraded mode — health check will report failure
    except Exception as exc:
        logger.exception("Непредвиденная ошибка при загрузке модели")
        app.state.tutor = None

    yield

    # --- shutdown ---
    logger.info("Завершение работы сервера. Освобождение ресурсов...")
    # Explicitly release GPU memory
    if app.state.tutor is not None:
        try:
            import torch

            del app.state.tutor
            torch.cuda.empty_cache()
            logger.info("Ресурсы GPU освобождены.")
        except Exception:
            logger.warning("Ошибка при освобождении ресурсов GPU.", exc_info=True)
    logger.info("Сервер остановлен.")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance.

    Separated from module-level code so that tests can import the app
    without triggering model loading.
    """
    app = FastAPI(
        title="ИИ-Тьютор СПО",
        description=(
            "API интеллектуального тьютора для среднего профессионального образования. "
            "Генерация конспектов лекций, тестов и диалоговая поддержка на базе "
            "Mistral Small 24B с LoRA-адаптацией."
        ),
        version="0.3.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # --- CORS ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Request timing middleware ---
    @app.middleware("http")
    async def add_request_timing(request: Request, call_next):
        """Measure and attach request processing time as a response header."""
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time-ms"] = f"{elapsed_ms:.2f}"
        return response

    # --- Exception handlers ---
    from tutor import InferenceError, ModelLoadError

    @app.exception_handler(ModelLoadError)
    async def model_load_error_handler(_request: Request, exc: ModelLoadError):
        """Обработчик ошибок загрузки модели."""
        logger.error("ModelLoadError: %s", exc)
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": f"Ошибка загрузки модели: {exc}",
                "data": None,
                "meta": {"generation_time_seconds": 0.0},
            },
        )

    @app.exception_handler(InferenceError)
    async def inference_error_handler(_request: Request, exc: InferenceError):
        """Обработчик ошибок инференса."""
        logger.error("InferenceError: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Ошибка генерации: {exc}",
                "data": None,
                "meta": {"generation_time_seconds": 0.0},
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(_request: Request, exc: ValueError):
        """Обработчик ошибок валидации (пользовательский ввод)."""
        logger.warning("ValueError: %s", exc)
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": f"Ошибка ввода: {exc}",
                "data": None,
                "meta": {"generation_time_seconds": 0.0},
            },
        )

    # --- Routers ---
    app.include_router(generate.router)
    app.include_router(async_generate.router)
    app.include_router(system.router)

    return app


# Module-level application instance for ``uvicorn api.main:app``
app = create_app()
