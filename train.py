"""
Скрипт дообучения ИИ-тьютора (SFT — Supervised Fine-Tuning).

Запуск:
    # Полное обучение (QLoRA, 3 эпохи)
    python train.py

    # Тестовый прогон (1 эпоха, 10 шагов, минимальная конфигурация)
    python train.py --mode debug

    # Лёгкая конфигурация (быстрее, меньше VRAM)
    python train.py --mode light

    # Из командной строки:
    python train.py --model_id ./local-model --epochs 5 --batch_size 2 --lr 2e-4

Требования:
    - GPU с VRAM от 48 ГБ (QLoRA 4-bit)
    - Python 3.10+
    - Зависимости: requirements.txt

Автор: Команда ИИ СИТ (Бардаков Д.Н.)
Лицензия: Apache 2.0
"""

from __future__ import annotations

import logging
import os
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path

import torch

# Настройка логирования до импорта тяжелых библиотек
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("train.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Парсинг аргументов командной строки.

    Возвращает:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Дообучение ИИ-тьютора (SFT/QLoRA)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python train.py --mode debug           # Быстрый тест пайплайна
  python train.py --mode light           # Лёгкое обучение
  python train.py                        # Полное обучение
  python train.py --epochs 5 --lr 1e-4  # Кастомные параметры
        """,
    )

    # Режим запуска
    parser.add_argument(
        "--mode",
        type=str,
        choices=["full", "light", "debug"],
        default="full",
        help="Режим обучения: full (полный), light (быстрый), debug (тест). По умолчанию: full.",
    )

    # Модель
    parser.add_argument(
        "--model_id",
        type=str,
        default=os.getenv("MODEL_PATH", "mistralai/Mistral-Small-24B-Instruct-2501"),
        help="ID или путь к базовой модели HuggingFace.",
    )

    # Данные
    parser.add_argument(
        "--train_file",
        type=str,
        default="dataset/data/train.jsonl",
        help="Путь к обучающему датасету (JSONL).",
    )
    parser.add_argument(
        "--val_file",
        type=str,
        default="dataset/data/val.jsonl",
        help="Путь к валидационному датасету (JSONL).",
    )

    # Гиперпараметры обучения
    parser.add_argument("--epochs", type=int, default=None, help="Количество эпох.")
    parser.add_argument("--batch_size", type=int, default=None, help="Размер батча.")
    parser.add_argument("--grad_accum_steps", type=int, default=None, help="Шаги аккумуляции градиентов.")
    parser.add_argument("--lr", type=float, default=None, help="Learning rate.")
    parser.add_argument("--max_seq_length", type=int, default=None, help="Максимальная длина последовательности.")
    parser.add_argument("--warmup_ratio", type=float, default=0.1, help="Доля шагов для warmup.")

    # Сохранение
    parser.add_argument(
        "--output_dir",
        type=str,
        default=None,
        help="Директория для сохранения чекпоинтов.",
    )
    parser.add_argument(
        "--save_steps",
        type=int,
        default=None,
        help="Сохранять чекпоинт каждые N шагов.",
    )
    parser.add_argument(
        "--eval_steps",
        type=int,
        default=None,
        help="Запускать валидацию каждые N шагов.",
    )

    # Восстановление
    parser.add_argument(
        "--resume_from_checkpoint",
        type=str,
        default=None,
        help="Путь к чекпоинту для возобновления обучения.",
    )

    # Логирование
    parser.add_argument(
        "--log_level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Уровень логирования.",
    )

    # Seed
    parser.add_argument("--seed", type=int, default=42, help="Random seed для воспроизводимости.")

    return parser.parse_args()


def load_dataset(file_path: str) -> list[dict]:
    """Загрузка датасета из JSONL-файла.

    Аргументы:
        file_path: Путь к JSONL-файлу.

    Возвращает:
        Список словарей с записями датасета.

    Исключения:
        FileNotFoundError: Если файл не существует.
        ValueError: Если файл пуст или формат некорректен.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Файл датасета не найден: {file_path}")

    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if "messages" not in record:
                    logger.warning(f"Строка {line_num}: отсутствует ключ 'messages', пропуск")
                    continue
                records.append(record)
            except json.JSONDecodeError as e:
                logger.warning(f"Строка {line_num}: ошибка JSON — {e}, пропуск")

    if not records:
        raise ValueError(f"Датасет пуст: {file_path}")

    logger.info(f"Загружен датасет: {file_path} ({len(records)} записей)")
    return records


def get_training_config(mode: str, args: argparse.Namespace):
    """Получение конфигурации обучения в зависимости от режима.

    Аргументы:
        mode: Режим обучения (full, light, debug).
        args: Аргументы командной строки.

    Возвращает:
        Словарь с параметрами обучения.
    """
    configs = {
        "full": {
            "epochs": 3,
            "batch_size": 2,
            "grad_accum_steps": 8,  # Effective batch size = 16
            "lr": 2e-4,
            "max_seq_length": 2048,
            "save_steps": 100,
            "eval_steps": 50,
            "max_steps": None,
        },
        "light": {
            "epochs": 2,
            "batch_size": 2,
            "grad_accum_steps": 4,  # Effective batch size = 8
            "lr": 2e-4,
            "max_seq_length": 1024,
            "save_steps": 200,
            "eval_steps": 100,
            "max_steps": None,
        },
        "debug": {
            "epochs": 1,
            "batch_size": 1,
            "grad_accum_steps": 1,
            "lr": 2e-4,
            "max_seq_length": 512,
            "save_steps": 5,
            "eval_steps": 5,
            "max_steps": 10,  # Всего 10 шагов для быстрого теста
        },
    }

    config = configs[mode]

    # Переопределение из CLI
    if args.epochs is not None:
        config["epochs"] = args.epochs
    if args.batch_size is not None:
        config["batch_size"] = args.batch_size
    if args.grad_accum_steps is not None:
        config["grad_accum_steps"] = args.grad_accum_steps
    if args.lr is not None:
        config["lr"] = args.lr
    if args.max_seq_length is not None:
        config["max_seq_length"] = args.max_seq_length
    if args.save_steps is not None:
        config["save_steps"] = args.save_steps
    if args.eval_steps is not None:
        config["eval_steps"] = args.eval_steps

    return config


def main() -> None:
    """Главная функция дообучения."""
    args = parse_args()

    # Уровень логирования
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Seed
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    logger.info("=" * 60)
    logger.info("ЗАПУСК ДООБУЧЕНИЯ ИИ-ТЬЮТОРА (SFT/QLoRA)")
    logger.info("=" * 60)

    # --- Конфигурация ---
    from lora_config import LoRAConfig, get_debug_config, get_light_config, get_full_config

    config_map = {"full": get_full_config, "light": get_lightweight_config, "debug": get_debug_config}
    # Fix: get_lightweight_config for "light" mode
    config_map = {"full": get_full_config, "light": get_lightweight_config, "debug": get_debug_config}

    lora_cfg = config_map[args.mode]()

    # Переопределение max_seq_length из CLI
    if args.max_seq_length is not None:
        lora_cfg.max_seq_length = args.max_seq_length
    if args.output_dir is not None:
        lora_cfg.output_dir = args.output_dir

    train_params = get_training_config(args.mode, args)
    logger.info(f"Режим: {args.mode}")
    logger.info(lora_cfg.summary())
    logger.info(f"Параметры обучения: {json.dumps(train_params, indent=2)}")

    # --- Загрузка датасета ---
    logger.info("Загрузка датасетов...")
    train_data = load_dataset(args.train_file)
    val_data = load_dataset(args.val_file)

    # --- Импорт тяжёлых библиотек (после логирования) ---
    logger.info("Импорт библиотек для обучения...")
    from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
    from trl import SFTTrainer
    from data_collator import TutorDataCollator

    # --- Загрузка модели ---
    logger.info(f"Загрузка модели: {args.model_id}")

    model_kwargs = {
        "trust_remote_code": True,
        "use_cache": False,  # Обязательно False для gradient_checkpointing
    }

    if lora_cfg.use_qlora:
        bnb_config = lora_cfg.get_bnb_config()
        model_kwargs["quantization_config"] = bnb_config
        logger.info("QLoRA 4-bit квантование включено")

    model = AutoModelForCausalLM.from_pretrained(args.model_id, **model_kwargs)

    # Gradient checkpointing для экономии VRAM
    if lora_cfg.gradient_checkpointing:
        model.gradient_checkpointing_enable()
        model.config.use_cache = False
        logger.info("Gradient checkpointing включён")

    # Логирование параметров модели
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"Параметры: {total_params / 1e9:.2f}B всего, {trainable_params / 1e6:.1f}M обучаемых")

    # --- Загрузка токенизатора ---
    logger.info("Загрузка токенизатора...")
    tokenizer = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # --- Коллатор данных ---
    data_collator = TutorDataCollator(
        tokenizer=tokenizer,
        max_seq_length=lora_cfg.max_seq_length,
        pad_to_multiple_of=8,
    )

    # --- TrainingArguments ---
    output_dir = lora_cfg.output_dir
    os.makedirs(output_dir, exist_ok=True)

    # Расчёт общего количества шагов для warmup
    steps_per_epoch = max(1, len(train_data) // (train_params["batch_size"] * train_params["grad_accum_steps"]))
    total_steps = steps_per_epoch * train_params["epochs"]
    warmup_steps = int(total_steps * args.warmup_ratio)

    training_args = TrainingArguments(
        # Базовые
        output_dir=output_dir,
        num_train_epochs=train_params["epochs"],
        per_device_train_batch_size=train_params["batch_size"],
        per_device_eval_batch_size=train_params["batch_size"],
        gradient_accumulation_steps=train_params["grad_accum_steps"],
        learning_rate=train_params["lr"],
        warmup_steps=warmup_steps,
        lr_scheduler_type="cosine",

        # Сохранение и оценка
        save_strategy="steps",
        save_steps=train_params["save_steps"],
        save_total_limit=3,  # Храним только 3 лучших чекпоинта
        evaluation_strategy="steps",
        eval_steps=train_params["eval_steps"],
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,

        # Оптимизация
        fp16=False,
        bf16=torch.cuda.is_bf16_supported(),
        gradient_checkpointing=lora_cfg.gradient_checkpointing,
        optim="paged_adamw_32bit",  # Оптимизированный AdamW для QLoRA
        max_grad_norm=1.0,

        # Логирование
        logging_dir=lora_cfg.logging_dir,
        logging_strategy="steps",
        logging_steps=10,
        report_to=["tensorboard"],

        # Прочее
        seed=args.seed,
        dataloader_pin_memory=True,
        dataloader_num_workers=2,
        remove_unused_columns=False,

        # Лимиты (для debug-режима)
        max_steps=train_params.get("max_steps", -1),
    )

    # --- SFTTrainer ---
    logger.info("Инициализация SFTTrainer...")
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_data,
        eval_dataset=val_data,
        tokenizer=tokenizer,
        data_collator=data_collator,
        peft_config=lora_cfg.get_peft_config(),
    )

    # --- Восстановление из чекпоинта ---
    if args.resume_from_checkpoint:
        logger.info(f"Возобновление обучения из: {args.resume_from_checkpoint}")
        trainer.train(resume_from_checkpoint=args.resume_from_checkpoint)
    else:
        logger.info("Запуск обучения с нуля...")
        trainer.train()

    # --- Сохранение финальной модели ---
    logger.info("Сохранение финального адаптера...")
    final_dir = os.path.join(output_dir, "final")
    trainer.save_model(final_dir)
    tokenizer.save_pretrained(final_dir)

    # Сохраняем метрики обучения
    metrics = {
        "train_loss": trainer.state.best_metric if hasattr(trainer.state, "best_metric") else None,
        "total_steps": trainer.state.global_step,
        "epochs": train_params["epochs"],
        "mode": args.mode,
        "lora_r": lora_cfg.r,
        "lora_alpha": lora_cfg.lora_alpha,
        "timestamp": datetime.now().isoformat(),
    }
    metrics_path = os.path.join(final_dir, "training_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    logger.info(f"Метрики сохранены: {metrics_path}")

    # Логирование результатов
    logger.info("=" * 60)
    logger.info("ОБУЧЕНИЕ ЗАВЕРШЕНО")
    logger.info(f"  Адаптер сохранён: {final_dir}")
    logger.info(f"  Шагов выполнено: {trainer.state.global_step}")
    if trainer.state.best_metric is not None:
        logger.info(f"  Лучший eval_loss: {trainer.state.best_metric:.4f}")
    logger.info("=" * 60)


# --- Утилита для get_lightweight_config (алиас для лёгкого режима) ---
def get_lightweight_config() -> "LoRAConfig":
    """Алиас для get_lightweight_config из lora_config."""
    from lora_config import get_lightweight_config as _glc
    return _glc()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Обучение прервано пользователем")
        sys.exit(0)
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")
        sys.exit(1)
