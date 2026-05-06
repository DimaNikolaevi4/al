"""
System endpoints — health, model info, and usage statistics.

Provides operational visibility into the running service: model status,
GPU utilisation, configuration, and lightweight request counters.
"""
# Автор: Команда ИИ СИТ (Бардаков Д.Н., Мышанская Н.Г.)
# Лицензия: Apache 2.0

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request

from api.models import (
    ApiResponse,
    GPUInfo,
    HealthData,
    MetaInfo,
    ModelInfoData,
    StatsData,
)

if TYPE_CHECKING:
    from tutor import IntelligentTutor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_tutor(request: Request) -> IntelligentTutor | None:
    """Retrieve the tutor instance from application state (may be None during startup)."""
    return getattr(request.app.state, "tutor", None)


def _gpu_info() -> GPUInfo:
    """Collect GPU information if CUDA is available."""
    try:
        import torch

        if not torch.cuda.is_available():
            return GPUInfo(available=False)

        device_props = torch.cuda.get_device_properties(0)
        vram_free = torch.cuda.mem_get_info(0)[0] / (1024 * 1024)
        vram_total = device_props.total_mem / (1024 * 1024)
        return GPUInfo(
            available=True,
            name=device_props.name,
            vram_free_mb=round(vram_free, 1),
            vram_total_mb=round(vram_total, 1),
        )
    except Exception:
        logger.warning("Failed to collect GPU info", exc_info=True)
        return GPUInfo(available=False)


def _model_params_count(tutor: IntelligentTutor) -> int | None:
    """Return total parameter count of the loaded model."""
    try:
        return sum(p.numel() for p in tutor.model.parameters())
    except Exception:
        logger.warning("Failed to count model parameters", exc_info=True)
        return None


# ---------------------------------------------------------------------------
# GET /api/v1/health
# ---------------------------------------------------------------------------

@router.get(
    "/health",
    response_model=ApiResponse[HealthData],
    summary="Проверка состояния сервиса",
    description="Возвращает статус модели, GPU и адаптеров.",
)
async def health(request: Request) -> ApiResponse[HealthData]:
    """Проверка работоспособности сервиса и загруженной модели."""
    tutor = _get_tutor(request)
    gpu = _gpu_info()

    model_loaded = tutor is not None
    model_id: str | None = None
    adapter_loaded = False

    if tutor is not None:
        model_id = tutor.model_id
        adapter_loaded = tutor.adapter_path is not None

    status = "ok" if model_loaded else "degraded"

    return ApiResponse[HealthData](
        success=True,
        data=HealthData(
            status=status,
            model_loaded=model_loaded,
            model_id=model_id,
            adapter_loaded=adapter_loaded,
            gpu=gpu,
        ),
        meta=MetaInfo(generation_time_seconds=0.0),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/info
# ---------------------------------------------------------------------------

@router.get(
    "/info",
    response_model=ApiResponse[ModelInfoData],
    summary="Информация о модели",
    description="Возвращает детали загруженной модели: идентификатор, адаптер, параметры.",
)
async def info(request: Request) -> ApiResponse[ModelInfoData]:
    """Информация о загруженной языковой модели и адаптерах."""
    tutor = _get_tutor(request)

    if tutor is None:
        return ApiResponse[ModelInfoData](
            success=False,
            error="Модель не загружена",
            meta=MetaInfo(generation_time_seconds=0.0),
        )

    param_count = _model_params_count(tutor)

    return ApiResponse[ModelInfoData](
        success=True,
        data=ModelInfoData(
            model_id=tutor.model_id,
            adapter_path=tutor.adapter_path,
            parameters_count=param_count,
            adapter_loaded=tutor.adapter_path is not None,
            dtype="float16",
        ),
        meta=MetaInfo(generation_time_seconds=0.0),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/stats
# ---------------------------------------------------------------------------

@router.get(
    "/stats",
    response_model=ApiResponse[StatsData],
    summary="Статистика использования",
    description="Возвращает счётчики запросов: общее количество, по endpoint и по дням.",
)
async def stats(request: Request) -> ApiResponse[StatsData]:
    """Статистика использования API (хранится в памяти процесса)."""
    usage_stats = getattr(request.app.state, "stats", {})

    return ApiResponse[StatsData](
        success=True,
        data=StatsData(
            total_requests=usage_stats.get("total_requests", 0),
            by_endpoint=dict(usage_stats.get("by_endpoint", {})),
            by_day=dict(usage_stats.get("by_day", {})),
        ),
        meta=MetaInfo(generation_time_seconds=0.0),
    )
