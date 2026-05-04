#!/usr/bin/env python3
"""
dataset/split_dataset.py — Разделение датасета на train/val/test
Задачи 7.2.1–7.2.4: Стратифицированное разделение, проверка, сохранение
Использование:
    python dataset/split_dataset.py --input dataset/data/dataset_normalized.jsonl --seed 42
    python dataset/split_dataset.py --input dataset/data/dataset_normalized.jsonl --output-dir dataset/data/ --seed 42
"""

import json
import hashlib
import argparse
import random
from collections import defaultdict
from pathlib import Path


def compute_hash(record: dict) -> str:
    """Вычисление хеша записи для проверки дубликатов между сплитами."""
    assistant_text = ""
    for m in record.get("messages", []):
        if m["role"] == "assistant":
            assistant_text = m["content"]
    return hashlib.sha256(assistant_text.strip().encode()).hexdigest()


def stratified_split(
    records: list[dict],
    train_ratio: float = 0.80,
    val_ratio: float = 0.10,
    test_ratio: float = 0.10,
    seed: int = 42,
) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Стратифицированное разделение датасета.
    Стратификация по task_type: каждый сплит содержит все типы задач в пропорции.
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 0.001, "Сумма долей должна быть 1.0"

    # Группировка по task_type
    groups = defaultdict(list)
    for record in records:
        task_type = record.get("metadata", {}).get("task_type", "unknown")
        groups[task_type].append(record)

    # Разделение внутри каждой группы
    rng = random.Random(seed)
    train, val, test = [], [], []

    for task_type, group_records in groups.items():
        rng.shuffle(group_records)
        n = len(group_records)
        n_train = max(1, int(n * train_ratio))
        n_val = max(1, int(n * val_ratio))
        # Оставшееся — test
        n_test = n - n_train - n_val
        if n_test < 1:
            n_val = max(1, n_val - 1)
            n_test = n - n_train - n_val

        train.extend(group_records[:n_train])
        val.extend(group_records[n_train:n_train + n_val])
        test.extend(group_records[n_train + n_val:])

    # Перемешивание внутри сплитов
    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)

    return train, val, test


def check_no_duplicates(splits: dict) -> list[str]:
    """7.2.3: Проверка отсутствия дубликатов между сплитами."""
    hash_map = defaultdict(list)
    issues = []

    for split_name, records in splits.items():
        for i, record in enumerate(records):
            h = compute_hash(record)
            hash_map[h].append(f"{split_name}[{i}]")

    for h, locations in hash_map.items():
        if len(locations) > 1:
            issues.append(f"Дубликат (hash {h[:12]}): {', '.join(locations)}")

    return issues


def check_stratification(splits: dict) -> dict:
    """7.2.3: Проверка стратификации (равномерность распределения по типам задач)."""
    all_types = set()
    for records in splits.values():
        for r in records:
            all_types.add(r.get("metadata", {}).get("task_type", "unknown"))

    strat_report = {}
    for task_type in sorted(all_types):
        strat_report[task_type] = {}
        for split_name, records in splits.items():
            count = sum(1 for r in records if r.get("metadata", {}).get("task_type") == task_type)
            pct = count / len(records) * 100 if records else 0
            strat_report[task_type][split_name] = {"count": count, "pct": round(pct, 1)}

    return strat_report


def balance_categories(
    records: list[dict],
    target_per_category: int = None,
) -> list[dict]:
    """7.2.1: Балансировка недопредставленных категорий."""
    if not target_per_category:
        return records  # Без балансировки

    groups = defaultdict(list)
    for record in records:
        task_type = record.get("metadata", {}).get("task_type", "unknown")
        groups[task_type].append(record)

    balanced = []
    for task_type, group_records in groups.items():
        if len(group_records) < target_per_category:
            # Добавляем все записи из недопредставленной категории
            balanced.extend(group_records)
        else:
            # Ограничиваем до целевого значения (undersampling)
            balanced.extend(group_records[:target_per_category])

    return balanced


def save_splits(
    train: list[dict],
    val: list[dict],
    test: list[dict],
    output_dir: str,
):
    """7.2.4: Сохранение финальных файлов."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    splits = {"train": train, "val": val, "test": test}
    for name, records in splits.items():
        filepath = Path(output_dir) / f"{name}.jsonl"
        with open(filepath, 'w', encoding='utf-8') as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        print(f"  {filepath}: {len(records)} записей")


def main():
    parser = argparse.ArgumentParser(description="Разделение датасета (7.2.1–7.2.4)")
    parser.add_argument("--input", required=True, help="Путь к входному JSONL")
    parser.add_argument("--output-dir", default="dataset/data/", help="Директория для выходных файлов")
    parser.add_argument("--train-ratio", type=float, default=0.80)
    parser.add_argument("--val-ratio", type=float, default=0.10)
    parser.add_argument("--test-ratio", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--balance", type=int, default=None, help="Целевое кол-во примеров на категорию")
    args = parser.parse_args()

    # Чтение датасета
    records = []
    with open(args.input, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    print(f"Входной датасет: {len(records)} записей")

    # 7.2.1: Балансировка (если указан параметр)
    if args.balance:
        records = balance_categories(records, args.balance)
        print(f"После балансировки: {len(records)} записей")

    # 7.2.2: Стратифицированное разделение
    train, val, test = stratified_split(
        records, args.train_ratio, args.val_ratio, args.test_ratio, args.seed
    )
    print(f"\nРазделение (seed={args.seed}):")
    print(f"  Train: {len(train)} ({len(train)/len(records)*100:.1f}%)")
    print(f"  Val:   {len(val)} ({len(val)/len(records)*100:.1f}%)")
    print(f"  Test:  {len(test)} ({len(test)/len(records)*100:.1f}%)")

    # 7.2.3: Проверка стратификации
    splits = {"train": train, "val": val, "test": test}

    duplicates = check_no_duplicates(splits)
    if duplicates:
        print(f"\n⚠️  Обнаружены дубликаты между сплитами: {len(duplicates)}")
        for d in duplicates[:5]:
            print(f"  - {d}")
    else:
        print("\n✅ Дубликатов между сплитами не обнаружено")

    stratification = check_stratification(splits)
    print("\nСтратификация по типам задач:")
    for task_type, split_data in stratification.items():
        counts = {k: v["count"] for k, v in split_data.items()}
        print(f"  {task_type:30s}: train={counts.get('train',0):4d}  val={counts.get('val',0):3d}  test={counts.get('test',0):3d}")

    # Проверка: каждый тип есть в каждом сплите
    missing = []
    for task_type, split_data in stratification.items():
        for split_name in ["train", "val", "test"]:
            if split_data[split_name]["count"] == 0:
                missing.append(f"{task_type} отсутствует в {split_name}")
    if missing:
        print(f"\n⚠️  Проблемы стратификации: {missing}")
    else:
        print("\n✅ Стратификация корректна: все типы задач представлены в каждом сплите")

    # 7.2.4: Сохранение
    save_splits(train, val, test, args.output_dir)

    # Сохранение отчёта о разделении
    report = {
        "input_count": len(records),
        "seed": args.seed,
        "splits": {
            "train": {"count": len(train), "ratio": round(len(train)/len(records)*100, 1)},
            "val": {"count": len(val), "ratio": round(len(val)/len(records)*100, 1)},
            "test": {"count": len(test), "ratio": round(len(test)/len(records)*100, 1)},
        },
        "stratification": stratification,
        "duplicates_between_splits": len(duplicates),
    }
    report_path = Path(args.output_dir) / "split_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nОтчёт разделения: {report_path}")


if __name__ == "__main__":
    main()
