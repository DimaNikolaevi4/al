#!/usr/bin/env python3
"""
dataset/normalize.py — Скрипт нормализации текстов в датасете
Задачи 6.2.1–6.2.3: Нормализация стиля, форматирования и терминологии
Использование:
    python dataset/normalize.py --input dataset/data/dataset_clean.jsonl --output dataset/data/dataset_normalized.jsonl
    python dataset/normalize.py --input dataset/data/dataset_clean.jsonl --report --output dataset/data/dataset_normalized.jsonl
"""

import json
import re
import argparse
import sys
from pathlib import Path


# --- 6.2.1: Нормализация стиля изложения ---
STYLE_REPLACEMENTS = {
    # Канцеляриты → разговорно-академический стиль
    r'\bосуществлять\b': 'выполнять',
    r'\bосуществление\b': 'выполнение',
    r'\bосуществил\b': 'выполнил',
    r'\bреализовать\b': 'сделать',
    r'\bреализуется\b': 'делается',
    r'\bреализация\b': 'выполнение',
    r'\bввиду того что\b': 'потому что',
    r'\bв связи с тем что\b': 'потому что',
    r'\bв соответствии с\b': 'по',
    r'\bна основании\b': 'на основе',
    r'\bследующим образом\b': 'так',
    r'\bцелесообразно\b': 'лучше',
    r'\bнеобходимо отметить\b': 'важно',
    r'\bиметь место\b': 'быть',
    r'\bпредставляет собой\b': 'это',
    r'\bявляется\b': '— это',
    r'\bв настоящее время\b': 'сейчас',
    r'\bна данный момент\b': 'сейчас',
    r'\bтаким образом\b': 'итог',
    r'\bнаряду с\b': 'вместе с',
    r'\bза счёт\b': 'за счёт',
    r'\bв частности\b': 'в том числе',
}

# Слишком длинные предложения (более 40 слов) → разбивать (флагирование)
MAX_SENTENCE_WORDS = 40


def normalize_style(text: str) -> tuple[str, list[dict]]:
    """6.2.1: Нормализация стиля изложения (академический, понятный для СПО)."""
    changes = []
    result = text

    for pattern, replacement in STYLE_REPLACEMENTS.items():
        matches = re.findall(pattern, result, re.IGNORECASE)
        if matches:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
            changes.append({
                "type": "style",
                "original": matches[0],
                "replacement": replacement,
                "count": len(matches),
            })

    # Флагирование длинных предложений
    sentences = re.split(r'(?<=[.!?])\s+', result)
    long_sentences = []
    for i, sent in enumerate(sentences):
        words = sent.split()
        if len(words) > MAX_SENTENCE_WORDS:
            long_sentences.append({
                "sentence_index": i,
                "word_count": len(words),
                "preview": sent[:100] + "..." if len(sent) > 100 else sent,
            })

    if long_sentences:
        changes.append({
            "type": "long_sentence",
            "count": len(long_sentences),
            "details": long_sentences[:3],  # Максимум 3 примера
        })

    return result, changes


# --- 6.2.2: Единообразие форматирования ---
FORMAT_RULES = [
    # Заголовки: ## → ## (без пробелов вокруг)
    (re.compile(r'\n#{1,3}\s+'), '\n## '),
    # Маркированные списки: * или • → -
    (re.compile(r'^[\*\•]\s', re.MULTILINE), '- '),
    # Нумерованные списки: с ) после цифры
    (re.compile(r'^(\d+)[.)]\s', re.MULTILINE), r'\1. '),
    # Двойные пробелы → один
    (re.compile(r' {2,}'), ' '),
    # Тройные и более переносы → двойные
    (re.compile(r'\n{3,}'), '\n\n'),
    # Кавычки "..." → «...»
    (re.compile(r'"([^"]+)"'), r'«\1»'),
    # Дефис вместо тире (между словами): " - " → " — "
    (re.compile(r'\s+-\s+'), ' — '),
    # Пустые строки с пробелами
    (re.compile(r'\n\s+\n'), '\n\n'),
    # Пробел перед запятой/точкой
    (re.compile(r'\s+([,.:;!?)])'), r'\1'),
    # Нет пробела после запятой/точки
    (re.compile(r'([,.:;!?])\s{0,1}([А-ЯЁA-Z"«(])'), r'\1 \2'),
]


def normalize_formatting(text: str) -> tuple[str, list[dict]]:
    """6.2.2: Единообразие форматирования (Markdown)."""
    changes = []
    result = text

    for pattern, replacement in FORMAT_RULES:
        before = result
        result = pattern.sub(replacement, result)
        if before != result:
            changes.append({
                "type": "formatting",
                "rule": pattern.pattern[:50],
                "fixes": sum(1 for a, b in zip(before, result) if a != b),
            })

    return result, changes


# --- 6.2.3: Нормализация терминологии по глоссарию ---
GLOSSARY_PATHS = [
    "dataset/glossary.json",
    "glossary.json",
]


def load_glossary(glossary_path: str = None) -> list[dict]:
    """Загрузка глоссария терминов."""
    if glossary_path is None:
        for path in GLOSSARY_PATHS:
            if Path(path).exists():
                glossary_path = path
                break

    if glossary_path and Path(glossary_path).exists():
        with open(glossary_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("terms", [])
    return []


def normalize_terminology(text: str, glossary: list[dict]) -> tuple[str, list[dict]]:
    """6.2.3: Нормализация терминологии по глоссарию."""
    changes = []
    result = text

    for term_entry in glossary:
        canonical = term_entry["term"]
        aliases = term_entry.get("aliases", [])

        # Замена алиасов на канонический термин
        for alias in aliases:
            if alias.lower() == canonical.lower():
                continue  # Пропускаем само собой
            # Ищем алиас как отдельное слово (с учётом падежных форм)
            pattern = re.compile(r'\b' + re.escape(alias) + r'\b', re.IGNORECASE)
            matches = list(pattern.finditer(result))
            if matches:
                # Сохраняем регистр первого символа канонического термина
                for match in matches:
                    matched = match.group()
                    if matched[0].isupper():
                        replacement = canonical
                    else:
                        replacement = canonical[0].lower() + canonical[1:]
                    result = result[:match.start()] + replacement + result[match.end():]
                    changes.append({
                        "type": "terminology",
                        "original": matched,
                        "replacement": replacement,
                        "canonical": canonical,
                    })

    return result, changes


# --- Основная функция нормализации ---
def normalize_dataset(
    input_path: str,
    output_path: str,
    glossary_path: str = None,
    report: bool = False,
) -> dict:
    """Нормализация датасета: стиль, форматирование, терминология (6.2.1–6.2.3)."""
    glossary = load_glossary(glossary_path)
    print(f"Глоссарий: загружено {len(glossary)} терминов")

    records = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    report_data = {
        "input_count": len(records),
        "total_changes": 0,
        "by_type": {"style": 0, "formatting": 0, "terminology": 0},
        "per_record": [],
    }

    normalized_records = []
    for i, record in enumerate(records):
        messages = record.get("messages", [])
        record_changes = {"index": i, "changes": []}

        for m in messages:
            if m["role"] not in ("user", "assistant"):
                continue

            original_text = m["content"]
            text = original_text

            # 6.2.1: Нормализация стиля
            text, style_changes = normalize_style(text)
            for c in style_changes:
                record_changes["changes"].append(c)
                report_data["by_type"]["style"] += 1

            # 6.2.2: Нормализация форматирования
            text, format_changes = normalize_formatting(text)
            for c in format_changes:
                record_changes["changes"].append(c)
                report_data["by_type"]["formatting"] += 1

            # 6.2.3: Нормализация терминологии
            text, term_changes = normalize_terminology(text, glossary)
            for c in term_changes:
                record_changes["changes"].append(c)
                report_data["by_type"]["terminology"] += 1

            m["content"] = text

        report_data["total_changes"] += len(record_changes["changes"])
        report_data["per_record"].append(record_changes)
        normalized_records.append(record)

    # Сохранение нормализованного датасета
    with open(output_path, 'w', encoding='utf-8') as f:
        for record in normalized_records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    if report:
        report_path = output_path.replace('.jsonl', '_norm_report.json')
        # Сокращаем отчёт (не включаем полный per_record)
        summary_report = {
            "input_count": report_data["input_count"],
            "total_changes": report_data["total_changes"],
            "by_type": report_data["by_type"],
            "records_with_changes": sum(1 for r in report_data["per_record"] if r["changes"]),
            "records_without_changes": sum(1 for r in report_data["per_record"] if not r["changes"]),
        }
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(summary_report, f, ensure_ascii=False, indent=2)
        print(f"Отчёт сохранён: {report_path}")

    print(f"Нормализация завершена:")
    print(f"  Обработано: {report_data['input_count']} записей")
    print(f"  Всего изменений: {report_data['total_changes']}")
    print(f"    - Стиль: {report_data['by_type']['style']}")
    print(f"    - Форматирование: {report_data['by_type']['formatting']}")
    print(f"    - Терминология: {report_data['by_type']['terminology']}")

    return report_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Нормализация датасета (6.2.1–6.2.3)")
    parser.add_argument("--input", required=True, help="Путь к входному JSONL")
    parser.add_argument("--output", required=True, help="Путь к выходному JSONL")
    parser.add_argument("--glossary", default=None, help="Путь к глоссарию glossary.json")
    parser.add_argument("--report", action="store_true", help="Генерировать отчёт")
    args = parser.parse_args()
    normalize_dataset(args.input, args.output, args.glossary, args.report)
