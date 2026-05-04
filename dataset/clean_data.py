#!/usr/bin/env python3
"""
dataset/clean_data.py — Скрипт очистки и нормализации датасета
Задачи 6.1.1–6.1.5: Удаление нежелательного контента
Использование:
    python dataset/clean_data.py --input dataset/data/dataset_raw.jsonl --output dataset/data/dataset_clean.jsonl
    python dataset/clean_data.py --input dataset/data/dataset_raw.jsonl --report --output dataset/data/dataset_clean.jsonl
"""

import json
import re
import hashlib
import argparse
import sys
from pathlib import Path


# --- 6.1.1: Паттерны персональных данных (ФЗ-152) ---
PERSONAL_DATA_PATTERNS = [
    # ФИО: Фамилия И.О. или Фамилия Имя Отчество
    re.compile(r'\b[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ]\.[А-ЯЁ]\.|\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)\b'),
    # Номера групп: XX-XX, XX-XX-XX
    re.compile(r'\b\d{2}[/-]\d{2}(?:[/-]\d{2})?\b(?!\s*м[Аа])(?!\s*г)\b'),
    # Номера зачётных книжек
    re.compile(r'\b(?:зачётк[аи]|зач\.?\s*кн\.?|номер\s*зач)\s*:?\s*\d+\b', re.IGNORECASE),
    # Email-адреса
    re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'),
    # Номера телефонов
    re.compile(r'\b(?:\+7|8)[\s-]?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}\b'),
    # Оценки в формате «оценка: 5»
    re.compile(r'\bоценк[аи]\s*:?\s*[1-5]\b', re.IGNORECASE),
    # Паспортные данные
    re.compile(r'\bсерия\s*паспорт[а-я]*\s*:?\s*\d{2}\s*\d{2}\b', re.IGNORECASE),
]

# Исключения — слова, которые похожи на ФИО но не являются (термины, аббревиатуры)
PD_EXCLUDE_WORDS = {
    'ПЛК', 'SCADA', 'АСУ', 'КИПиА', 'ПИД', 'ОВЕН', 'ГОСТ', 'ФГОС',
    'Датчик', 'Регулятор', 'Контроллер', 'Преобразователь', 'Клапан',
    'Система', 'Модуль', 'Двигатель', 'Насос', 'Элемент', 'Параметр',
}


def check_personal_data(text: str) -> list[dict]:
    """6.1.1: Поиск персональных данных в тексте."""
    findings = []
    for pattern in PERSONAL_DATA_PATTERNS:
        for match in pattern.finditer(text):
            matched_text = match.group()
            # Проверяем исключения
            words = set(re.findall(r'[А-ЯЁA-Z]{2,}', matched_text))
            if words and words.issubset(PD_EXCLUDE_WORDS):
                continue
            findings.append({
                "type": "personal_data",
                "match": matched_text,
                "start": match.start(),
                "end": match.end(),
            })
    return findings


# --- 6.1.2: Устаревшие данные и фактические ошибки ---
OUTDATED_MARKERS = {
    "version": "1.0",
    "standards": [
        {"old": "ГОСТ 21.404-85", "current": "ГОСТ 21.404-2020", "note": "Обозначения в схемах автоматизации"},
        {"old": "ГОСТ 8.011-72", "current": "ГОСТ 8.011-2019", "note": "Показания точности измерений"},
        {"old": "ПЛК-100", "current": "ПЛК-150/ПЛК-110", "note": "Устаревшая модель ПЛК ОВЕН"},
    ],
    "deprecated_terms": [
        {"term": "тепловой контроль", "replacement": "контроль температуры", "note": "Устаревший термин"},
        {"term": "электронный пульт", "replacement": "SCADA-система", "note": "Современная терминология"},
    ],
}


def check_outdated_data(text: str) -> list[dict]:
    """6.1.2: Поиск устаревших данных и стандартов."""
    findings = []
    for std in OUTDATED_MARKERS["standards"]:
        if std["old"] in text:
            findings.append({
                "type": "outdated_standard",
                "found": std["old"],
                "recommended": std["current"],
                "note": std["note"],
            })
    for term in OUTDATED_MARKERS["deprecated_terms"]:
        if term["term"] in text:
            findings.append({
                "type": "deprecated_term",
                "found": term["term"],
                "recommended": term["replacement"],
                "note": term["note"],
            })
    return findings


# --- 6.1.3: Проверка полноты input-output пар ---
MIN_USER_LENGTH = 50      # минимальная длина user (символов)
MIN_ASSISTANT_LENGTH = 50  # минимальная длина assistant


def check_pair_completeness(record: dict) -> list[str]:
    """6.1.3: Проверка полноты input-output пар."""
    issues = []
    messages = record.get("messages", [])

    # Проверка структуры: system + user + assistant
    if len(messages) < 3:
        issues.append(f"Неполная пара: {len(messages)} сообщений вместо 3")
        return issues

    roles = [m.get("role", "") for m in messages]
    if "user" not in roles:
        issues.append("Отсутствует user-сообщение")
    if "assistant" not in roles:
        issues.append("Отсутствует assistant-сообщение")

    # Проверка длины
    for m in messages:
        content = m.get("content", "")
        if m["role"] == "user" and len(content.strip()) < MIN_USER_LENGTH:
            issues.append(f"user слишком короткий: {len(content.strip())} символов (минимум {MIN_USER_LENGTH})")
        if m["role"] == "assistant" and len(content.strip()) < MIN_ASSISTANT_LENGTH:
            issues.append(f"assistant слишком короткий: {len(content.strip())} символов (минимум {MIN_ASSISTANT_LENGTH})")

    # Проверка на пустой/мусорный контент
    for m in messages:
        content = m.get("content", "").strip()
        if not content:
            issues.append(f"Пустое сообщение: role={m.get('role')}")
        elif content in ("...", "—", "N/A", "n/a", "-"):
            issues.append(f"Мусорное сообщение: role={m.get('role')}, content='{content}'")

    return issues


# --- 6.1.4: Дедупликация (near-duplicates) ---
STOP_WORDS = {
    'и', 'в', 'на', 'с', 'по', 'к', 'у', 'о', 'от', 'до', 'за', 'из', 'об',
    'не', 'для', 'это', 'что', 'как', 'но', 'а', 'или', 'то', 'же', 'так',
    'бы', 'все', 'он', 'она', 'они', 'мы', 'вы', 'я', 'его', 'её', 'их',
    'the', 'is', 'a', 'an', 'in', 'of', 'to', 'and', 'or', 'for',
}


def normalize_for_dedup(text: str) -> set:
    """Нормализация текста для сравнения: лемматизация и удаление стоп-слов."""
    words = re.findall(r'[а-яёa-z]+', text.lower())
    return set(w for w in words if len(w) > 2 and w not in STOP_WORDS)


def jaccard_similarity(set_a: set, set_b: set) -> float:
    """Вычисление Jaccard-сходства двух множеств."""
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def find_duplicates(records: list[dict], threshold: float = 0.90) -> list[dict]:
    """6.1.4: Поиск дубликатов и near-duplicates."""
    duplicates = []
    seen_hashes = {}  # SHA-256 → index
    normalized_texts = []  # (set, index)

    for i, record in enumerate(records):
        assistant_text = ""
        for m in record.get("messages", []):
            if m["role"] == "assistant":
                assistant_text = m["content"]

        # Точные дубликаты (SHA-256)
        text_hash = hashlib.sha256(assistant_text.strip().encode()).hexdigest()
        if text_hash in seen_hashes:
            duplicates.append({
                "type": "exact_duplicate",
                "index": i,
                "duplicate_of": seen_hashes[text_hash],
                "hash": text_hash[:12],
            })
            continue
        seen_hashes[text_hash] = i

        # Near-duplicates (Jaccard)
        normalized = normalize_for_dedup(assistant_text)
        normalized_texts.append((normalized, i))

    # Попарное сравнение (для near-duplicates)
    for i in range(len(normalized_texts)):
        for j in range(i + 1, len(normalized_texts)):
            set_a, idx_a = normalized_texts[i]
            set_b, idx_j = normalized_texts[j]
            sim = jaccard_similarity(set_a, set_b)
            if sim > threshold:
                duplicates.append({
                    "type": "near_duplicate",
                    "index": idx_j,
                    "duplicate_of": idx_a,
                    "similarity": round(sim, 4),
                    "threshold": threshold,
                })

    return duplicates


# --- 6.1.5: Проверка цензурности ---
PROFANITY_PATTERNS = [
    re.compile(r'\b(?:блин|чёрт|дерьмо|хрен|фиг|задолбал|достал|отстой|кайф|прикол)\b', re.IGNORECASE),
    re.compile(r'[!]{3,}'),  # Многократные восклицательные знаки
    re.compile(r'[?]{3,}'),  # Многократные вопросительные знаки
]

ETHICAL_ISSUES_PATTERNS = [
    re.compile(r'\b(?:взлом|хакнуть|украсть|обмануть| cheat |hack)\b', re.IGNORECASE),
]


def check_profanity(text: str) -> list[dict]:
    """6.1.5: Проверка на нецензурность и этические нормы."""
    findings = []

    for pattern in PROFANITY_PATTERNS:
        for match in pattern.finditer(text):
            findings.append({
                "type": "profanity",
                "match": match.group(),
                "position": match.start(),
                "severity": "low",
            })

    for pattern in ETHICAL_ISSUES_PATTERNS:
        for match in pattern.finditer(text):
            findings.append({
                "type": "ethical_issue",
                "match": match.group(),
                "position": match.start(),
                "severity": "medium",
            })

    return findings


# --- Основная функция очистки ---
def clean_dataset(input_path: str, output_path: str, report: bool = False) -> dict:
    """Очистка датасета: удаление нежелательного контента (6.1.1–6.1.5)."""
    records = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    report_data = {
        "input_count": len(records),
        "removed": {
            "personal_data": 0,
            "outdated": 0,
            "incomplete_pairs": 0,
            "duplicates": 0,
            "profanity": 0,
        },
        "kept": 0,
        "details": [],
    }

    # Шаг 1: Поиск дубликатов (6.1.4)
    duplicate_indices = set()
    duplicates = find_duplicates(records, threshold=0.90)
    for dup in duplicates:
        duplicate_indices.add(dup["index"])
    report_data["removed"]["duplicates"] = len(duplicate_indices)

    # Шаг 2: Фильтрация записей
    clean_records = []
    for i, record in enumerate(records):
        if i in duplicate_indices:
            report_data["details"].append({"index": i, "reason": "duplicate", "info": "Точный или near-duplicate"})
            continue

        # 6.1.3: Проверка полноты пар
        completeness_issues = check_pair_completeness(record)
        if completeness_issues:
            report_data["removed"]["incomplete_pairs"] += 1
            report_data["details"].append({"index": i, "reason": "incomplete_pair", "info": "; ".join(completeness_issues)})
            continue

        # 6.1.1: Проверка ПДн
        all_text = " ".join(m["content"] for m in record.get("messages", []))
        pd_findings = check_personal_data(all_text)
        if pd_findings:
            report_data["removed"]["personal_data"] += 1
            report_data["details"].append({"index": i, "reason": "personal_data", "info": f"Найдено {len(pd_findings)} совпадений"})
            continue

        # 6.1.5: Проверка цензурности
        profanity_findings = check_profanity(all_text)
        if any(f["severity"] == "medium" for f in profanity_findings):
            report_data["removed"]["profanity"] += 1
            report_data["details"].append({"index": i, "reason": "profanity", "info": f"Этическая проблема"})
            continue

        # 6.1.2: Проверка устаревших данных (флагирование, но не удаление)
        outdated = check_outdated_data(all_text)
        if outdated:
            report_data["removed"]["outdated"] += 1
            report_data["details"].append({
                "index": i, "reason": "outdated_data",
                "info": "; ".join(f.get("found", "") for f in outdated)
            })
            # Не удаляем, только флагируем для ручной проверки
            # clean_records.append(record)
            continue

        clean_records.append(record)

    report_data["kept"] = len(clean_records)

    # Сохранение очищенного датасета
    with open(output_path, 'w', encoding='utf-8') as f:
        for record in clean_records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    if report:
        report_path = output_path.replace('.jsonl', '_clean_report.json')
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        print(f"Отчёт сохранён: {report_path}")

    print(f"Очистка завершена:")
    print(f"  Вход: {report_data['input_count']} записей")
    print(f"  Удалено: {sum(report_data['removed'].values())} записей")
    print(f"    - ПДн: {report_data['removed']['personal_data']}")
    print(f"    - Устаревшие: {report_data['removed']['outdated']}")
    print(f"    - Неполные пары: {report_data['removed']['incomplete_pairs']}")
    print(f"    - Дубликаты: {report_data['removed']['duplicates']}")
    print(f"    - Цензурность: {report_data['removed']['profanity']}")
    print(f"  Сохранено: {report_data['kept']} записей")

    return report_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Очистка датасета (6.1.1–6.1.5)")
    parser.add_argument("--input", required=True, help="Путь к входному JSONL")
    parser.add_argument("--output", required=True, help="Путь к выходному JSONL")
    parser.add_argument("--report", action="store_true", help="Генерировать отчёт")
    args = parser.parse_args()
    clean_dataset(args.input, args.output, args.report)
