#!/usr/bin/env python3
"""
dataset/analyze_balance.py — Анализ распределения примеров в датасете
Задачи 7.1.1–7.1.3: Статистика по предметам, типам задач, уровню сложности
Использование:
    python dataset/analyze_balance.py --input dataset/data/dataset_normalized.jsonl --output dataset/data/stats.json
    python dataset/analyze_balance.py --input dataset/data/dataset_normalized.jsonl --output dataset/data/stats.json --verbose
"""

import json
import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path


def count_chars(text: str) -> int:
    """Подсчёт символов без пробелов."""
    return len(text.replace(" ", ""))


def count_words(text: str) -> int:
    """Подсчёт слов."""
    return len(text.split())


def estimate_tokens(text: str) -> int:
    """Оценка количества токенов (коэффициент ~1.3 токена на слово для русского)."""
    return int(len(text.split()) * 1.3)


def analyze_dataset(input_path: str, verbose: bool = False) -> dict:
    """Анализ датасета: распределение по предметам, типам задач, сложности."""
    records = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    if not records:
        print("ОШИБКА: Датасет пуст")
        return {}

    # Базовые счётчики
    stats = {
        "total_examples": len(records),
        "by_subject": Counter(),
        "by_task_type": Counter(),
        "by_difficulty": Counter(),
        "by_source": Counter(),
        "by_topic": Counter(),
        "token_stats": {
            "system_lengths": [],
            "user_lengths": [],
            "assistant_lengths": [],
            "total_lengths": [],
        },
        "char_stats": {
            "user_lengths": [],
            "assistant_lengths": [],
        },
    }

    for record in records:
        metadata = record.get("metadata", {})
        stats["by_subject"][metadata.get("subject", "unknown")] += 1
        stats["by_task_type"][metadata.get("task_type", "unknown")] += 1
        stats["by_difficulty"][metadata.get("difficulty", "unknown")] += 1
        stats["by_source"][metadata.get("source", "unknown")] += 1
        stats["by_topic"][metadata.get("topic", "unknown")] += 1

        # Длина сообщений
        for m in record.get("messages", []):
            tokens = estimate_tokens(m.get("content", ""))
            if m["role"] == "system":
                stats["token_stats"]["system_lengths"].append(tokens)
            elif m["role"] == "user":
                stats["token_stats"]["user_lengths"].append(tokens)
                stats["char_stats"]["user_lengths"].append(count_chars(m.get("content", "")))
            elif m["role"] == "assistant":
                stats["token_stats"]["assistant_lengths"].append(tokens)
                stats["char_stats"]["assistant_lengths"].append(count_chars(m.get("content", "")))

        # Общая длина (user + assistant)
        total_tokens = sum(
            estimate_tokens(m.get("content", ""))
            for m in record.get("messages", [])
            if m["role"] in ("user", "assistant")
        )
        stats["token_stats"]["total_lengths"].append(total_tokens)

    # Вычисление сводных статистик
    def compute_summary(values: list) -> dict:
        if not values:
            return {"avg": 0, "min": 0, "max": 0, "median": 0}
        sorted_v = sorted(values)
        n = len(sorted_v)
        return {
            "avg": round(sum(values) / n),
            "min": sorted_v[0],
            "max": sorted_v[-1],
            "median": sorted_v[n // 2],
            "p25": sorted_v[n // 4],
            "p75": sorted_v[3 * n // 4],
        }

    stats["token_summary"] = {
        "system": compute_summary(stats["token_stats"]["system_lengths"]),
        "user": compute_summary(stats["token_stats"]["user_lengths"]),
        "assistant": compute_summary(stats["token_stats"]["assistant_lengths"]),
        "total": compute_summary(stats["token_stats"]["total_lengths"]),
    }

    # 7.1.1: Распределение по предметам
    stats["subject_distribution"] = dict(stats["by_subject"])
    subject_pcts = {}
    for subj, count in stats["by_subject"].most_common():
        subject_pcts[subj] = round(count / len(records) * 100, 1)
    stats["subject_percentages"] = subject_pcts

    # 7.1.2: Распределение по типам задач
    stats["task_type_distribution"] = dict(stats["by_task_type"])
    task_pcts = {}
    for task, count in stats["by_task_type"].most_common():
        task_pcts[task] = round(count / len(records) * 100, 1)
    stats["task_type_percentages"] = task_pcts

    # 7.1.3: Распределение по уровню сложности
    stats["difficulty_distribution"] = dict(stats["by_difficulty"])
    diff_pcts = {}
    for diff, count in stats["by_difficulty"].most_common():
        diff_pcts[diff] = round(count / len(records) * 100, 1)
    stats["difficulty_percentages"] = diff_pcts

    # Покрытие тем
    stats["topic_coverage"] = {
        "unique_topics": len(stats["by_topic"]),
        "top_topics": dict(stats["by_topic"].most_common(20)),
    }

    # Проверка дисбаланса
    stats["imbalance_warnings"] = []
    for cat_name, cat_dist in [
        ("subject", stats["by_subject"]),
        ("task_type", stats["by_task_type"]),
        ("difficulty", stats["by_difficulty"]),
    ]:
        if cat_dist:
            counts = list(cat_dist.values())
            max_ratio = max(counts) / min(counts) if min(counts) > 0 else float('inf')
            if max_ratio > 3.0:
                stats["imbalance_warnings"].append(
                    f"Дисбаланс по {cat_name}: макс/мин = {max_ratio:.1f} (рекомендуется ≤3.0)"
                )

    # Очистка внутренних данных для вывода
    del stats["by_subject"]
    del stats["by_task_type"]
    del stats["by_difficulty"]
    del stats["by_source"]
    del stats["by_topic"]
    del stats["token_stats"]
    del stats["char_stats"]

    return stats


def print_report(stats: dict):
    """Вывод отчёта в консоль."""
    print("=" * 60)
    print("АНАЛИЗ БАЛАНСА ДАТАСЕТА")
    print("=" * 60)
    print(f"\nВсего примеров: {stats['total_examples']}")

    # 7.1.1
    print("\n--- 7.1.1: Распределение по предметам ---")
    for subj, count in sorted(stats["subject_distribution"].items()):
        pct = stats["subject_percentages"][subj]
        bar = "█" * int(pct / 2)
        print(f"  {subj:30s}: {count:4d} ({pct:5.1f}%) {bar}")

    # 7.1.2
    print("\n--- 7.1.2: Распределение по типам задач ---")
    for task, count in sorted(stats["task_type_distribution"].items()):
        pct = stats["task_type_percentages"][task]
        bar = "█" * int(pct / 2)
        print(f"  {task:30s}: {count:4d} ({pct:5.1f}%) {bar}")

    # 7.1.3
    print("\n--- 7.1.3: Распределение по уровню сложности ---")
    for diff, count in sorted(stats["difficulty_distribution"].items()):
        pct = stats["difficulty_percentages"][diff]
        bar = "█" * int(pct / 2)
        print(f"  {diff:30s}: {count:4d} ({pct:5.1f}%) {bar}")

    # Токены
    print("\n--- Статистика по токенам ---")
    ts = stats["token_summary"]
    for key in ["system", "user", "assistant", "total"]:
        s = ts[key]
        print(f"  {key:12s}: avg={s['avg']:5d}  min={s['min']:5d}  max={s['max']:5d}  median={s['median']:5d}")

    # Предупреждения
    if stats.get("imbalance_warnings"):
        print("\n⚠️  ПРЕДУПРЕЖДЕНИЯ О ДИСБАЛАНСЕ:")
        for w in stats["imbalance_warnings"]:
            print(f"  - {w}")
    else:
        print("\n✅ Дисбаланс не обнаружен")

    print("\n--- Покрытие тем ---")
    print(f"  Уникальных тем: {stats['topic_coverage']['unique_topics']}")
    print(f"  Топ-10 тем:")
    for topic, count in list(stats["topic_coverage"]["top_topics"].items())[:10]:
        print(f"    - {topic}: {count} примеров")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Анализ баланса датасета (7.1.1–7.1.3)")
    parser.add_argument("--input", required=True, help="Путь к входному JSONL")
    parser.add_argument("--output", required=True, help="Путь к выходному stats.json")
    parser.add_argument("--verbose", "-v", action="store_true", help="Подробный вывод")
    args = parser.parse_args()

    stats = analyze_dataset(args.input, args.verbose)
    if stats:
        print_report(stats)
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"\nСтатистика сохранена: {args.output}")
