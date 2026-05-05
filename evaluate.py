"""
Скрипт оценки качества дообученной модели ИИ-тьютора.

Запуск:
    # Оценка на тестовой выборке
    python evaluate.py --adapter_path ./checkpoints/lora-adapter/final

    # Оценка базовой модели (без адаптера)
    python evaluate.py --no_adapter

    # Генерация отчёта в файл
    python evaluate.py --adapter_path ./checkpoints/lora-adapter/final --output results/

Требования:
    - GPU с VRAM от 48 ГБ
    - Обученный LoRA-адаптер (или базовая модель для baseline)

Автор: Команда ИИ СИТ (Бардаков Д.Н.)
Лицензия: Apache 2.0
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import torch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("evaluate.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(description="Оценка качества ИИ-тьютора")

    # Модель
    parser.add_argument(
        "--model_id",
        type=str,
        default=os.getenv("MODEL_PATH", "mistralai/Mistral-Small-24B-Instruct-2501"),
        help="ID или путь к базовой модели.",
    )
    parser.add_argument(
        "--adapter_path",
        type=str,
        default=None,
        help="Путь к LoRA-адаптеру. Если не указан, оценивается базовая модель.",
    )
    parser.add_argument(
        "--no_adapter",
        action="store_true",
        help="Оценить базовую модель без адаптера.",
    )

    # Данные
    parser.add_argument(
        "--test_file",
        type=str,
        default="dataset/data/test.jsonl",
        help="Путь к тестовому датасету (JSONL).",
    )
    parser.add_argument(
        "--num_samples",
        type=int,
        default=None,
        help="Количество примеров для оценки (None = все).",
    )

    # Параметры генерации
    parser.add_argument("--max_new_tokens", type=int, default=512, help="Максимум токенов для генерации.")
    parser.add_argument("--temperature", type=float, default=0.3, help="Температура (низкая = более детерминированно).")

    # Вывод
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Директория для сохранения результатов.",
    )

    return parser.parse_args()


def load_test_dataset(file_path: str, num_samples: Optional[int] = None) -> list[dict]:
    """Загрузка тестового датасета.

    Аргументы:
        file_path: Путь к JSONL-файлу.
        num_samples: Максимальное количество примеров (None = все).

    Возвращает:
        Список записей датасета.
    """
    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if "messages" in record:
                records.append(record)

    if num_samples is not None and num_samples < len(records):
        records = records[:num_samples]

    logger.info(f"Загружено {len(records)} примеров из {file_path}")
    return records


@torch.no_grad()
def generate_response(model, tokenizer, messages: list[dict], max_new_tokens: int, temperature: float) -> str:
    """Генерация ответа модели для заданного диалога.

    Аргументы:
        model: Языковая модель.
        tokenizer: Токенизатор.
        messages: Список сообщений чата.
        max_new_tokens: Максимум генерируемых токенов.
        temperature: Температура сэмплирования.

    Возвращает:
        Сгенерированный текст ответа.
    """
    # Формируем prompt: все сообщения кроме последнего assistant
    prompt_messages = messages[:-1]  # system + user (без assistant)
    prompt = tokenizer.apply_chat_template(
        prompt_messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=4096).to(model.device)

    outputs = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_p=0.9,
        do_sample=temperature > 0,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id,
    )

    # Декодируем только сгенерированную часть
    generated_ids = outputs[0][inputs["input_ids"].shape[1]:]
    response = tokenizer.decode(generated_ids, skip_special_tokens=True)

    return response.strip()


def compute_basic_metrics(reference: str, prediction: str) -> dict[str, float]:
    """Вычисление базовых метрик качества генерации.

    Метрики:
        - length_ratio: Отношение длины предсказания к эталону.
        - contains_keywords: Доля ключевых слов из эталона, присутствующих в предсказании.
        - exact_match_lines: Доля строк эталона, найденных в предсказании.

    Аргументы:
        reference: Эталонный ответ (assistant).
        prediction: Сгенерированный ответ.

    Возвращает:
        Словарь с метриками.
    """
    if not reference or not prediction:
        return {"length_ratio": 0.0, "keyword_overlap": 0.0, "line_match": 0.0}

    # Длина
    ref_len = len(reference.split())
    pred_len = len(prediction.split())
    length_ratio = pred_len / max(ref_len, 1)

    # Перекрытие ключевых слов (слова длиной от 4 символов)
    ref_words = {w.lower() for w in reference.split() if len(w) >= 4}
    pred_words = {w.lower() for w in prediction.split() if len(w) >= 4}
    if ref_words:
        keyword_overlap = len(ref_words & pred_words) / len(ref_words)
    else:
        keyword_overlap = 0.0

    # Совпадение строк
    ref_lines = {line.strip().lower() for line in reference.split("\n") if line.strip() and len(line.strip()) > 20}
    pred_lines = {line.strip().lower() for line in prediction.split("\n") if line.strip() and len(line.strip()) > 20}
    if ref_lines:
        line_match = len(ref_lines & pred_lines) / len(ref_lines)
    else:
        line_match = 0.0

    return {
        "length_ratio": round(length_ratio, 3),
        "keyword_overlap": round(keyword_overlap, 3),
        "line_match": round(line_match, 3),
    }


def main() -> None:
    """Главная функция оценки."""
    args = parse_args()
    logger.info("=" * 60)
    logger.info("ОЦЕНКА КАЧЕСТВА ИИ-ТЬЮТОРА")
    logger.info("=" * 60)

    # --- Загрузка датасета ---
    test_data = load_test_dataset(args.test_file, args.num_samples)
    logger.info(f"Тестовая выборка: {len(test_data)} примеров")

    # --- Импорт тяжёлых библиотек ---
    from transformers import AutoModelForCausalLM, AutoTokenizer

    # --- Загрузка модели ---
    logger.info(f"Загрузка базовой модели: {args.model_id}")

    model_kwargs = {
        "torch_dtype": torch.float16,
        "device_map": "auto",
        "trust_remote_code": True,
    }

    model = AutoModelForCausalLM.from_pretrained(args.model_id, **model_kwargs)

    if args.adapter_path and not args.no_adapter:
        logger.info(f"Загрузка LoRA-адаптера: {args.adapter_path}")
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, args.adapter_path)
    else:
        logger.info("Оценка базовой модели (без адаптера)")

    tokenizer = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # --- Генерация и оценка ---
    all_metrics = []
    results = []

    total = len(test_data)
    start_time = time.time()

    for i, record in enumerate(test_data):
        messages = record["messages"]
        metadata = record.get("metadata", {})
        reference = messages[-1]["content"] if messages[-1]["role"] == "assistant" else ""

        # Генерация
        t0 = time.time()
        try:
            prediction = generate_response(
                model, tokenizer, messages,
                max_new_tokens=args.max_new_tokens,
                temperature=args.temperature,
            )
            gen_time = time.time() - t0
        except Exception as e:
            logger.error(f"Пример {i+1}: ошибка генерации — {e}")
            prediction = f"[ОШИБКА ГЕНЕРАЦИИ: {e}]"
            gen_time = 0

        # Метрики
        metrics = compute_basic_metrics(reference, prediction)
        metrics["gen_time_sec"] = round(gen_time, 2)
        metrics["tokens_per_sec"] = round(len(prediction.split()) / max(gen_time, 0.01), 1)
        all_metrics.append(metrics)

        # Сохранение результата
        result = {
            "index": i + 1,
            "metadata": metadata,
            "reference_length": len(reference),
            "prediction_length": len(prediction),
            "prediction_preview": prediction[:300] + "..." if len(prediction) > 300 else prediction,
            **metrics,
        }
        results.append(result)

        # Логирование прогресса
        if (i + 1) % 5 == 0 or i == 0 or i == total - 1:
            avg_overlap = sum(m["keyword_overlap"] for m in all_metrics[-5:]) / min(5, len(all_metrics))
            elapsed = time.time() - start_time
            eta = (elapsed / (i + 1)) * (total - i - 1)
            logger.info(
                f"  [{i+1}/{total}] "
                f"keyword_overlap={avg_overlap:.3f}, "
                f"len_ratio={metrics['length_ratio']:.2f}, "
                f"gen_time={gen_time:.1f}s, "
                f"ETA={eta:.0f}s"
            )

    # --- Агрегация результатов ---
    elapsed_total = time.time() - start_time
    avg_metrics = {}
    for key in ["length_ratio", "keyword_overlap", "line_match", "gen_time_sec", "tokens_per_sec"]:
        values = [m[key] for m in all_metrics if key in m]
        if values:
            avg_metrics[f"avg_{key}"] = round(sum(values) / len(values), 3)
            avg_metrics[f"min_{key}"] = round(min(values), 3)
            avg_metrics[f"max_{key}"] = round(max(values), 3)

    summary = {
        "model_id": args.model_id,
        "adapter_path": args.adapter_path,
        "test_file": args.test_file,
        "num_samples": len(test_data),
        "total_time_sec": round(elapsed_total, 1),
        "avg_time_per_sample_sec": round(elapsed_total / max(len(test_data), 1), 2),
        "timestamp": datetime.now().isoformat(),
        **avg_metrics,
    }

    # --- Вывод ---
    logger.info("=" * 60)
    logger.info("РЕЗУЛЬТАТЫ ОЦЕНКИ")
    logger.info("=" * 60)
    logger.info(f"  Модель:             {args.model_id}")
    logger.info(f"  Адаптер:            {args.adapter_path or 'нет'}")
    logger.info(f"  Примеров:           {len(test_data)}")
    logger.info(f"  Общее время:        {elapsed_total:.1f} сек")
    logger.info(f"  Среднее на пример:  {elapsed_total / max(len(test_data), 1):.2f} сек")
    logger.info(f"  Avg keyword_overlap:  {avg_metrics.get('avg_keyword_overlap', 'N/A')}")
    logger.info(f"  Avg line_match:       {avg_metrics.get('avg_line_match', 'N/A')}")
    logger.info(f"  Avg length_ratio:     {avg_metrics.get('avg_length_ratio', 'N/A')}")
    logger.info(f"  Avg tokens/sec:       {avg_metrics.get('avg_tokens_per_sec', 'N/A')}")
    logger.info("=" * 60)

    # --- Сохранение результатов ---
    if args.output:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)

        summary_path = output_dir / "evaluation_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        logger.info(f"Сводка сохранена: {summary_path}")

        details_path = output_dir / "evaluation_details.json"
        with open(details_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Детали сохранены: {details_path}")
    else:
        # Вывод в stdout
        print("\n--- СВОДКА ---")
        print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Оценка прервана пользователем")
        sys.exit(0)
    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")
        sys.exit(1)
