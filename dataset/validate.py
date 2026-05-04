#!/usr/bin/env python3
"""
dataset/validate.py — Автоматическая валидация датасета перед обучением
Задачи 8.1.1–8.1.6: Проверка JSONL, токенов, дубликатов, баланса, статистика
Использование:
    python dataset/validate.py --train dataset/data/train.jsonl --val dataset/data/val.jsonl --test dataset/data/test.jsonl
    python dataset/validate.py --train dataset/data/train.jsonl --val dataset/data/val.jsonl --test dataset/data/test.jsonl --output dataset/data/stats.json
"""

import json
import hashlib
import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path


# --- Параметры модели ---
MODEL_CONTEXT = 32768     # Mistral Small 3.1: ~32K токенов
MAX_SYSTEM_TOKENS = 500
MIN_USER_TOKENS = 128
MAX_USER_TOKENS = 2048
MIN_ASSISTANT_TOKENS = 64
MAX_ASSISTANT_TOKENS = 4096
TOKENS_PER_WORD = 1.3    # Коэффициент для русского языка


def estimate_tokens(text: str) -> int:
    """Оценка количества токенов."""
    return int(len(text.split()) * TOKENS_PER_WORD)


# --- 8.1.1: Проверка JSONL формата ---
def validate_jsonl_format(filepath: str) -> list[dict]:
    """8.1.1: Проверка всех строк на валидный JSONL."""
    errors = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                # Проверка структуры
                if 'messages' not in obj:
                    errors.append({"line": i, "error": "missing 'messages' field"})
                elif not isinstance(obj['messages'], list):
                    errors.append({"line": i, "error": "'messages' is not a list"})
                elif len(obj['messages']) < 3:
                    errors.append({"line": i, "error": f"expected 3+ messages, got {len(obj['messages'])}"})
                else:
                    roles = [m.get('role', '') for m in obj['messages']]
                    valid_roles = {'system', 'user', 'assistant'}
                    for j, role in enumerate(roles):
                        if role not in valid_roles:
                            errors.append({"line": i, "error": f"invalid role '{role}' at message {j}"})
                    if 'system' not in roles:
                        errors.append({"line": i, "error": "missing 'system' message"})
                    if 'user' not in roles:
                        errors.append({"line": i, "error": "missing 'user' message"})
                    if 'assistant' not in roles:
                        errors.append({"line": i, "error": "missing 'assistant' message"})
                    # Проверка полей content
                    for j, m in enumerate(obj['messages']):
                        if 'content' not in m:
                            errors.append({"line": i, "error": f"message {j} missing 'content'"})
                        elif not isinstance(m['content'], str):
                            errors.append({"line": i, "error": f"message {j} 'content' is not string"})
            except json.JSONDecodeError as e:
                errors.append({"line": i, "error": f"JSON parse error: {str(e)[:100]}"})

    return errors


# --- 8.1.2: Проверка длины токенов ---
def validate_token_lengths(filepath: str) -> list[dict]:
    """8.1.2: Проверка длины токенов для каждой записи."""
    warnings = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                total_tokens = 0
                for m in obj.get('messages', []):
                    content = m.get('content', '')
                    tokens = estimate_tokens(content)
                    total_tokens += tokens
                    role = m['role']

                    if role == 'system':
                        if tokens > MAX_SYSTEM_TOKENS:
                            warnings.append({"line": i, "warning": f"system prompt too long: {tokens} > {MAX_SYSTEM_TOKENS}"})
                    elif role == 'user':
                        if tokens < MIN_USER_TOKENS:
                            warnings.append({"line": i, "warning": f"user too short: {tokens} < {MIN_USER_TOKENS}"})
                        if tokens > MAX_USER_TOKENS:
                            warnings.append({"line": i, "warning": f"user too long: {tokens} > {MAX_USER_TOKENS}"})
                    elif role == 'assistant':
                        if tokens < MIN_ASSISTANT_TOKENS:
                            warnings.append({"line": i, "warning": f"assistant too short: {tokens} < {MIN_ASSISTANT_TOKENS}"})
                        if tokens > MAX_ASSISTANT_TOKENS:
                            warnings.append({"line": i, "warning": f"assistant too long: {tokens} > {MAX_ASSISTANT_TOKENS}"})

                if total_tokens > MODEL_CONTEXT:
                    warnings.append({"line": i, "warning": f"total too long: {total_tokens} > {MODEL_CONTEXT}"})
            except json.JSONDecodeError:
                pass  # Ошибки JSON уже найдены в 8.1.1

    return warnings


# --- 8.1.3: Проверка дубликатов между сплитами ---
def validate_no_cross_duplicates(splits: dict[str, str]) -> list[dict]:
    """8.1.3: Проверка отсутствия дубликатов между train/val/test."""
    hash_map = defaultdict(list)
    duplicates = []

    for split_name, filepath in splits.items():
        with open(filepath, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    assistant_text = ""
                    for m in obj.get('messages', []):
                        if m['role'] == 'assistant':
                            assistant_text = m['content']
                    h = hashlib.sha256(assistant_text.strip().encode()).hexdigest()
                    hash_map[h].append(f"{split_name}:line{i}")
                except json.JSONDecodeError:
                    pass

    for h, locations in hash_map.items():
        if len(locations) > 1:
            split_names = set(loc.split(":")[0] for loc in locations)
            if len(split_names) > 1:  # Дубликаты между разными сплитами
                duplicates.append({"hash": h[:12], "locations": locations})

    return duplicates


# --- 8.1.4: Проверка баланса типов задач ---
def validate_balance(filepath: str) -> dict:
    """8.1.4: Проверка баланса классов и типов задач."""
    task_types = Counter()
    subjects = Counter()
    difficulties = Counter()
    total = 0

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                metadata = obj.get("metadata", {})
                task_types[metadata.get("task_type", "unknown")] += 1
                subjects[metadata.get("subject", "unknown")] += 1
                difficulties[metadata.get("difficulty", "unknown")] += 1
                total += 1
            except json.JSONDecodeError:
                pass

    result = {
        "total": total,
        "task_types": {k: {"count": v, "pct": round(v/total*100, 1)} for k, v in task_types.most_common()},
        "subjects": {k: {"count": v, "pct": round(v/total*100, 1)} for k, v in subjects.most_common()},
        "difficulties": {k: {"count": v, "pct": round(v/total*100, 1)} for k, v in difficulties.most_common()},
    }

    # Проверка минимального порога (>=5% от сплита)
    result["warnings"] = []
    for task, info in result["task_types"].items():
        if info["pct"] < 5.0 and total > 0:
            result["warnings"].append(f"task_type '{task}': {info['pct']}% < 5% threshold")

    return result


# --- 8.1.5: Статистический анализ ---
def compute_statistics(filepath: str) -> dict:
    """8.1.5: Статистический анализ (длина, распределение, покрытие)."""
    system_lens = []
    user_lens = []
    assistant_lens = []
    total_lens = []
    topics = set()

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                total = 0
                for m in obj.get('messages', []):
                    tokens = estimate_tokens(m.get('content', ''))
                    total += tokens
                    if m['role'] == 'system':
                        system_lens.append(tokens)
                    elif m['role'] == 'user':
                        user_lens.append(tokens)
                    elif m['role'] == 'assistant':
                        assistant_lens.append(tokens)
                total_lens.append(total)
                topics.add(obj.get("metadata", {}).get("topic", "unknown"))
            except json.JSONDecodeError:
                pass

    def summary(values):
        if not values:
            return {"avg": 0, "min": 0, "max": 0, "median": 0}
        s = sorted(values)
        n = len(s)
        return {"avg": round(sum(s)/n), "min": s[0], "max": s[-1], "median": s[n//2]}

    return {
        "records": len(total_lens),
        "system_tokens": summary(system_lens),
        "user_tokens": summary(user_lens),
        "assistant_tokens": summary(assistant_lens),
        "total_tokens": summary(total_lens),
        "unique_topics": len(topics),
    }


def main():
    parser = argparse.ArgumentParser(description="Автоматическая валидация датасета (8.1.1–8.1.6)")
    parser.add_argument("--train", required=True, help="Путь к train.jsonl")
    parser.add_argument("--val", required=True, help="Путь к val.jsonl")
    parser.add_argument("--test", required=True, help="Путь к test.jsonl")
    parser.add_argument("--output", default=None, help="Путь к stats.json")
    args = parser.parse_args()

    splits = {"train": args.train, "val": args.val, "test": args.test}
    all_passed = True
    report = {"model": "Mistral Small 3.1 (24B)", "context_window": MODEL_CONTEXT}

    # 8.1.1: Проверка JSONL формата
    print("=" * 60)
    print("8.1.1: Проверка JSONL формата")
    print("-" * 60)
    for name, path in splits.items():
        errors = validate_jsonl_format(path)
        if errors:
            print(f"  {name}: ❌ {len(errors)} ошибок")
            for e in errors[:5]:
                print(f"    line {e['line']}: {e['error']}")
            all_passed = False
        else:
            count = sum(1 for line in open(path) if line.strip())
            print(f"  {name}: ✅ {count} строк, 0 ошибок")
        report[f"{name}_jsonl_errors"] = len(errors)

    # 8.1.2: Проверка длины токенов
    print("\n8.1.2: Проверка длины токенов")
    print("-" * 60)
    for name, path in splits.items():
        warnings = validate_token_lengths(path)
        if warnings:
            print(f"  {name}: ⚠️  {len(warnings)} предупреждений")
            for w in warnings[:5]:
                print(f"    line {w['line']}: {w['warning']}")
        else:
            print(f"  {name}: ✅ Все записи в пределах лимитов")
        report[f"{name}_token_warnings"] = len(warnings)

    # 8.1.3: Проверка дубликатов между сплитами
    print("\n8.1.3: Проверка дубликатов между сплитами")
    print("-" * 60)
    cross_dups = validate_no_cross_duplicates(splits)
    if cross_dups:
        print(f"  ❌ Обнаружено {len(cross_dups)} кросс-дубликатов (data leakage!)")
        for d in cross_dups[:5]:
            print(f"    hash {d['hash']}: {d['locations']}")
        all_passed = False
    else:
        print(f"  ✅ Кросс-дубликатов не обнаружено")
    report["cross_duplicates"] = len(cross_dups)

    # 8.1.4: Проверка баланса
    print("\n8.1.4: Проверка баланса типов задач")
    print("-" * 60)
    for name, path in splits.items():
        balance = validate_balance(path)
        print(f"  {name} ({balance['total']} записей):")
        for task, info in balance["task_types"].items():
            print(f"    {task:30s}: {info['count']:4d} ({info['pct']:5.1f}%)")
        if balance["warnings"]:
            for w in balance["warnings"]:
                print(f"    ⚠️  {w}")
        report[f"{name}_balance"] = balance

    # 8.1.5: Статистический анализ
    print("\n8.1.5: Статистический анализ")
    print("-" * 60)
    stats_all = {}
    for name, path in splits.items():
        stats = compute_statistics(path)
        stats_all[name] = stats
        print(f"  {name}: {stats['records']} записей, {stats['unique_topics']} тем")
        ts = stats['total_tokens']
        print(f"    tokens: avg={ts['avg']}, min={ts['min']}, max={ts['max']}, median={ts['median']}")
    report["statistics"] = stats_all

    # 8.1.6: Итоговый статус
    print("\n" + "=" * 60)
    print("8.1.6: Итоговая валидация")
    print("=" * 60)
    if all_passed:
        print("✅ Все проверки пройдены. Датасет готов к обучению.")
        report["status"] = "PASSED"
    else:
        print("❌ Обнаружены ошибки. Исправьте перед обучением.")
        report["status"] = "FAILED"

    # Сохранение отчёта
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\nОтчёт сохранён: {args.output}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
