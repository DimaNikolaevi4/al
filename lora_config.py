"""
Конфигурация LoRA/QLoRA для дообучения ИИ-тьютора.

Содержит параметры адаптеров Low-Rank Adaptation для эффективного
дообучения модели Mistral Small 24B Instruct на образовательном
датасете СПО.

Режим QLoRA (4-bit квантование) позволяет обучать 24B-параметрическую
модель на GPU с VRAM от 48 ГБ.

Автор: Команда ИИ СИТ (Бардаков Д.Н.)
Лицензия: Apache 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LoRAConfig:
    """Конфигурация LoRA/QLoRA адаптеров.

    Параметры оптимизированы для дообучения Mistral Small 24B Instruct
    на задачах генерации образовательного контента (конспекты, тесты,
    объяснения) для студентов СПО.

    Атрибуты:
        r: Ранг матрицы адаптации. Больше rank — больше обучаемых параметров,
            но выше риск переобучения. Оптимально: 8-64.
        lora_alpha: Шкалирующий коэффициент. Рекомендуется r * 2.
        lora_dropout: Dropout для LoRA-слоёв. Предотвращает переобучение.
        target_modules: Список модулей модели, к которым применяются адаптеры.
        bias: Тип смещения для адаптеров.
        task_type: Тип задачи модели.
        use_qlora: Использовать 4-bit квантование (QLoRA).
        bnb_4bit_quant_type: Тип 4-bit квантования bitsandbytes.
        bnb_4bit_compute_dtype: Тип данных для вычислений при 4-bit квантовании.
        bnb_4bit_use_double_quant: Двойное квантование для дополнительной экономии памяти.
        gradient_checkpointing: Использовать градиентный чекпоинтинг для экономии VRAM.
        max_seq_length: Максимальная длина последовательности в токенах.
    """

    # --- Основные параметры LoRA ---
    r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    target_modules: list[str] = field(default_factory=lambda: [
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ])
    bias: str = "none"
    task_type: str = "CAUSAL_LM"

    # --- Параметры QLoRA (4-bit квантование) ---
    use_qlora: bool = True
    bnb_4bit_quant_type: str = "nf4"  # NormalFloat4 — оптимально для нормальных распределений весов
    bnb_4bit_compute_dtype: str = "bfloat16"  # bfloat16 для стабильности обучения
    bnb_4bit_use_double_quant: bool = True  # Двойное квантование экономит ~0.4 бит на параметр

    # --- Оптимизация памяти ---
    gradient_checkpointing: bool = True
    max_seq_length: int = 2048

    # --- Путь для сохранения ---
    output_dir: str = "./checkpoints/lora-adapter"
    logging_dir: str = "./logs"

    def get_peft_config(self):
        """Создание конфигурации PEFT для передачи в SFTTrainer.

        Возвращает:
            Конфигурацию peft.LoraConfig.
        """
        from peft import LoraConfig

        return LoraConfig(
            r=self.r,
            lora_alpha=self.lora_alpha,
            lora_dropout=self.lora_dropout,
            target_modules=self.target_modules,
            bias=self.bias,
            task_type=self.task_type,
        )

    def get_bnb_config(self):
        """Создание конфигурации bitsandbytes для 4-bit квантования.

        Возвращает:
            Конфигурацию transformers.BitsAndBytesConfig.
            None, если use_qlora == False.
        """
        if not self.use_qlora:
            return None

        import torch
        from transformers import BitsAndBytesConfig

        dtype_map = {
            "bfloat16": torch.bfloat16,
            "float16": torch.float16,
            "float32": torch.float32,
        }

        compute_dtype = dtype_map.get(self.bnb_4bit_compute_dtype, torch.bfloat16)

        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type=self.bnb_4bit_quant_type,
            bnb_4bit_compute_dtype=compute_dtype,
            bnb_4bit_use_double_quant=self.bnb_4bit_use_double_quant,
        )

    def summary(self) -> str:
        """Текстовое описание конфигурации для логирования.

        Возвращает:
            Многострочную строку с параметрами конфигурации.
        """
        lines = [
            "=== Конфигурация LoRA/QLoRA ===",
            f"  Ранг (r):               {self.r}",
            f"  Alpha:                  {self.lora_alpha} (ratio: {self.lora_alpha / self.r:.1f})",
            f"  Dropout:                {self.lora_dropout}",
            f"  Target modules:         {', '.join(self.target_modules)}",
            f"  Bias:                   {self.bias}",
            f"  QLoRA (4-bit):          {self.use_qlora}",
        ]
        if self.use_qlora:
            lines.extend([
                f"    Quant type:           {self.bnb_4bit_quant_type}",
                f"    Compute dtype:        {self.bnb_4bit_compute_dtype}",
                f"    Double quant:         {self.bnb_4bit_use_double_quant}",
            ])
        lines.extend([
            f"  Gradient checkpointing: {self.gradient_checkpointing}",
            f"  Max seq length:         {self.max_seq_length}",
            f"  Output dir:             {self.output_dir}",
            "================================",
        ])
        return "\n".join(lines)


# --- Предустановленные конфигурации ---

def get_lightweight_config() -> LoRAConfig:
    """Лёгкая конфигурация для быстрого тестового прогона.

    Меньше обучаемых параметров — быстрее обучение, подходит для
    проверки пайплайна перед полным запуском.

    Returns:
        LoRAConfig с уменьшенным рангом.
    """
    return LoRAConfig(
        r=8,
        lora_alpha=16,
        target_modules=["q_proj", "v_proj"],
        max_seq_length=1024,
        output_dir="./checkpoints/lora-adapter-light",
    )


def get_full_config() -> LoRAConfig:
    """Полная конфигурация для финального обучения.

    Максимум обучаемых параметров для лучшего качества генерации.
    Требует GPU с VRAM от 48 ГБ.

    Returns:
        LoRAConfig с полным набором целевых модулей.
    """
    return LoRAConfig(
        r=32,
        lora_alpha=64,
        lora_dropout=0.03,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        max_seq_length=2048,
        output_dir="./checkpoints/lora-adapter-full",
    )


def get_debug_config() -> LoRAConfig:
    """Отладочная конфигурация для минимального теста.

    Минимальные параметры для проверки, что пайплайн работает.
    Обучение займёт несколько минут даже на слабом GPU.

    Returns:
        LoRAConfig с минимальными параметрами.
    """
    return LoRAConfig(
        r=4,
        lora_alpha=8,
        lora_dropout=0.1,
        target_modules=["q_proj", "v_proj"],
        use_qlora=True,
        max_seq_length=512,
        output_dir="./checkpoints/lora-adapter-debug",
    )
