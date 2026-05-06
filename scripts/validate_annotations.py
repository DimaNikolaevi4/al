#!/usr/bin/env python3
"""
Скрипт валидации разметки датасета (Task 4.2.4).

Проверяет качество ручной и LLM-сгенерированной разметки:
- Формат JSONL (каждая строка — валидный JSON)
- Обязательные поля: messages (system/user/assistant), metadata
- Качество контента: длина, язык, дубликаты, пустые ответы
- Баланс по предметам, сложности, типам задач
- Противоречия в метаданных
- Перекос subject в train/val/test сплитах
- Отчёт в CSV и консоль

Использование:
    python scripts/validate_annotations.py --data-dir dataset/data/
    python scripts/validate_annotations.py --data-dir dataset/data/ --report-dir reports/
    python scripts/validate_annotations.py --data-dir dataset/data/ --strict
"""

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# --- Конфигурация ---

REQUIRED_TOP_KEYS = {"messages", "metadata"}

REQUIRED_METADATA_KEYS = {
    "task_type",    # summary / quiz / chat / explanation
    "subject",      # industrial_auto / measurement_systems
    "difficulty",   # easy / medium / hard
    "topic",        # строка — тема лекции
    "source",       # manual / llm_generated / template
    "source_file",  # имя исходного файла
}

VALID_TASK_TYPES = {"summary", "quiz", "chat", "explanation"}
VALID_SUBJECTS = {"industrial_auto", "measurement_systems"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_SOURCES = {"manual", "llm_generated", "template"}

REQUIRED_MSG_ROLES = {"system", "user", "assistant"}

# Пороги качества
MIN_ASSISTANT_LENGTH = 50       # минимальная длина ответа ассистента (символы)
MAX_ASSISTANT_LENGTH = 8000     # максимальная длина (защита от мусора)
MIN_USER_LENGTH = 20            # минимальная длина запроса пользователя
MIN_SYSTEM_LENGTH = 30          # минимальная длина системного промпта
DUPLICATE_SIMILARITY = 0.95     # порог для детекта почти-дубликатов (Jaccard)


@dataclass
class Issue:
    """Описание одной проблемы в записи."""
    file: str
    line: int
    severity: str           # error / warning / info
    category: str           # duplicate / format / content / metadata / balance
    message: str
    field: Optional[str] = None


@dataclass
class ValidationReport:
    """Полный отчёт о валидации."""
    total_files: int = 0
    total_records: int = 0
    issues: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def errors(self):
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self):
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def infos(self):
        return [i for i in self.issues if i.severity == "info"]

    @property
    def passed(self):
        return len(self.errors) == 0


class DatasetValidator:
    """Валидатор датасета."""

    def __init__(self, strict: bool = False):
        self.strict = strict
        self.report = ValidationReport()
        self._seen_texts: dict[str, list[tuple[str, int]]] = defaultdict(list)

    def add_issue(self, file: str, line: int, severity: str,
                  category: str, message: str, field: str = None):
        """Зарегистрировать проблему."""
        self.report.issues.append(Issue(
            file=file, line=line, severity=severity,
            category=category, message=message, field=field
        ))

    def validate_directory(self, data_dir: str) -> ValidationReport:
        """Валидировать все JSONL файлы в директории."""
        path = Path(data_dir)
        if not path.exists():
            print(f"ОШИБКА: Директория {data_dir} не найдена")
            sys.exit(1)

        jsonl_files = sorted(path.glob("*.jsonl"))
        if not jsonl_files:
            print(f"ОШИБКА: JSONL файлы не найдены в {data_dir}")
            sys.exit(1)

        self.report.total_files = len(jsonl_files)

        # 1. Валидация каждого файла
        all_records = {}  # {filename: [records]}
        for filepath in jsonl_files:
            records = self._validate_file(filepath)
            all_records[filepath.name] = records

        # 2. Кросс-файловые проверки
        self._check_cross_file_duplicates(all_records)
        self._check_balance(all_records)
        self._compute_stats(all_records)

        return self.report

    def _validate_file(self, filepath: Path) -> list:
        """Валидировать один JSONL файл."""
        fname = filepath.name
        records = []
        print(f"  Проверяю {fname}...")

        with open(filepath, "r", encoding="utf-8") as f:
            for line_num, raw_line in enumerate(f, 1):
                line = raw_line.strip()
                if not line:
                    continue

                # Парсинг JSON
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as e:
                    self.add_issue(fname, line_num, "error", "format",
                                   f"Невалидный JSON: {e}")
                    continue

                # Проверка обязательных ключей
                missing_keys = REQUIRED_TOP_KEYS - set(record.keys())
                if missing_keys:
                    self.add_issue(fname, line_num, "error", "format",
                                   f"Отсутствуют ключи: {missing_keys}")
                    continue

                # Валидация messages
                self._validate_messages(fname, line_num, record.get("messages", []))

                # Валидация metadata
                self._validate_metadata(fname, line_num, record.get("metadata", {}))

                # Валидация контента
                self._validate_content(fname, line_num, record)

                # Детект дубликатов (по тексту assistant)
                assistant_texts = [
                    m.get("content", "") for m in record.get("messages", [])
                    if m.get("role") == "assistant"
                ]
                for text in assistant_texts:
                    normalized = self._normalize_text(text)
                    self._seen_texts[normalized].append((fname, line_num))

                records.append(record)

        print(f"    Записей: {len(records)}")
        self.report.total_records += len(records)
        return records

    def _validate_messages(self, fname: str, line: int, messages: list):
        """Проверить структуру messages."""
        if not isinstance(messages, list):
            self.add_issue(fname, line, "error", "format",
                           "messages не является списком")
            return

        if len(messages) < 2:
            self.add_issue(fname, line, "error", "format",
                           f"Слишком мало сообщений: {len(messages)} (минимум 2)")
            return

        roles_present = set()
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                self.add_issue(fname, line, "error", "format",
                               f"messages[{i}] не является объектом")
                continue

            # Проверка role
            role = msg.get("role")
            if not role:
                self.add_issue(fname, line, "error", "format",
                               f"messages[{i}] не имеет поля role")
                continue

            if role not in REQUIRED_MSG_ROLES | {"tool", "function"}:
                self.add_issue(fname, line, "warning", "format",
                               f"messages[{i}] имеет неожиданную роль: '{role}'")

            roles_present.add(role)

            # Проверка content
            content = msg.get("content", "")
            if not isinstance(content, str):
                self.add_issue(fname, line, "error", "format",
                               f"messages[{i}].content не является строкой")
                continue

            # Проверка длины
            if role == "system" and len(content) < MIN_SYSTEM_LENGTH:
                self.add_issue(fname, line, "warning", "content",
                               f"Системный промпт слишком короткий: {len(content)} символов",
                               field="messages.system.content")
            elif role == "user" and len(content) < MIN_USER_LENGTH:
                self.add_issue(fname, line, "warning", "content",
                               f"Запрос пользователя слишком короткий: {len(content)} символов",
                               field="messages.user.content")
            elif role == "assistant" and len(content) < MIN_ASSISTANT_LENGTH:
                self.add_issue(fname, line, "error", "content",
                               f"Ответ ассистента слишком короткий: {len(content)} символов (мин {MIN_ASSISTANT_LENGTH})",
                               field="messages.assistant.content")
            elif role == "assistant" and len(content) > MAX_ASSISTANT_LENGTH:
                self.add_issue(fname, line, "warning", "content",
                               f"Ответ ассистента слишком длинный: {len(content)} символов (макс {MAX_ASSISTANT_LENGTH})",
                               field="messages.assistant.content")

        # Обязательные роли
        missing_roles = REQUIRED_MSG_ROLES - roles_present
        if missing_roles:
            self.add_issue(fname, line, "error", "format",
                           f"Отсутствуют роли: {missing_roles}")

        # Порядок: system должен быть первым
        if messages and messages[0].get("role") != "system":
            self.add_issue(fname, line, "warning", "format",
                           "Первое сообщение не имеет роль 'system'")

    def _validate_metadata(self, fname: str, line: int, metadata: dict):
        """Проверить метаданные записи."""
        if not isinstance(metadata, dict):
            self.add_issue(fname, line, "error", "format",
                           "metadata не является объектом")
            return

        # Обязательные поля
        missing = REQUIRED_METADATA_KEYS - set(metadata.keys())
        if missing:
            self.add_issue(fname, line, "error", "metadata",
                           f"Отсутствуют поля метаданных: {missing}",
                           field="metadata")

        # Валидация значений
        task_type = metadata.get("task_type")
        if task_type and task_type not in VALID_TASK_TYPES:
            self.add_issue(fname, line, "error", "metadata",
                           f"Недопустимый task_type: '{task_type}' (ожидается: {VALID_TASK_TYPES})",
                           field="metadata.task_type")

        subject = metadata.get("subject")
        if subject and subject not in VALID_SUBJECTS:
            self.add_issue(fname, line, "error", "metadata",
                           f"Недопустимый subject: '{subject}' (ожидается: {VALID_SUBJECTS})",
                           field="metadata.subject")

        difficulty = metadata.get("difficulty")
        if difficulty and difficulty not in VALID_DIFFICULTIES:
            self.add_issue(fname, line, "error", "metadata",
                           f"Недопустимый difficulty: '{difficulty}' (ожидается: {VALID_DIFFICULTIES})",
                           field="metadata.difficulty")

        source = metadata.get("source")
        if source and source not in VALID_SOURCES:
            self.add_issue(fname, line, "warning", "metadata",
                           f"Недопустимый source: '{source}' (ожидается: {VALID_SOURCES})",
                           field="metadata.source")

        topic = metadata.get("topic")
        if topic and (not isinstance(topic, str) or len(topic) < 3):
            self.add_issue(fname, line, "warning", "metadata",
                           f"Подозрительно короткий topic: '{topic}'",
                           field="metadata.topic")

        # Противоречие: difficulty=hard + source=template (шаблоны обычно easy/medium)
        if difficulty == "hard" and source == "template":
            self.add_issue(fname, line, "warning", "metadata",
                           "Возможное противоречие: difficulty=hard при source=template",
                           field="metadata")

        # Противоречие: source=manual + subject из другой дисциплины
        source_file = metadata.get("source_file", "")
        if source_file and subject:
            if "industrial" in source_file.lower() and subject != "industrial_auto":
                self.add_issue(fname, line, "warning", "metadata",
                               f"subject='{subject}' не совпадает с source_file='{source_file}'",
                               field="metadata")
            elif "measurement" in source_file.lower() and subject != "measurement_systems":
                self.add_issue(fname, line, "warning", "metadata",
                               f"subject='{subject}' не совпадает с source_file='{source_file}'",
                               field="metadata")

    def _validate_content(self, fname: str, line: int, record: dict):
        """Проверить качество контента."""
        messages = record.get("messages", [])

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "assistant":
                # Проверка на пустой/мусорный контент
                if not content.strip():
                    self.add_issue(fname, line, "error", "content",
                                   "Пустой ответ ассистента",
                                   field="messages.assistant.content")

                # Проверка на повторяющиеся строки (маркер мусора)
                lines = content.split("\n")
                non_empty = [l.strip() for l in lines if l.strip()]
                if len(non_empty) > 3:
                    line_counts = Counter(non_empty)
                    most_common = line_counts.most_common(1)[0]
                    if most_common[1] > len(non_empty) * 0.3:
                        self.add_issue(fname, line, "warning", "content",
                                       f"Возможный мусор: строка повторяется {most_common[1]} раз: "
                                       f"'{most_common[0][:50]}...'",
                                       field="messages.assistant.content")

                # Проверка языка (предупреждение если слишком много латиницы в русском контексте)
                if content:
                    latin_ratio = self._latin_ratio(content)
                    if latin_ratio > 0.7:
                        self.add_issue(fname, line, "warning", "content",
                                       f"Высокая доля латиницы: {latin_ratio:.0%} — возможно не на русском",
                                       field="messages.assistant.content")

    def _check_cross_file_duplicates(self, all_records: dict):
        """Проверить дубликаты между файлами."""
        dup_count = 0
        for normalized, locations in self._seen_texts.items():
            if len(locations) > 1:
                # Отчёт только о первом дубликате
                if normalized and len(normalized) > 100:  # значимые тексты
                    dup_count += 1
                    loc_str = ", ".join(f"{f}:{l}" for f, l in locations)
                    self.add_issue("ALL", 0, "warning", "duplicate",
                                   f"Дубликат текста ассистента в {len(locations)} записях: {loc_str}")

        if dup_count:
            print(f"  Найдено потенциальных дубликатов: {dup_count}")

    def _check_balance(self, all_records: dict):
        """Проверить баланс по предметам и сложности в сплитах."""
        subject_counts = Counter()
        difficulty_counts = Counter()
        task_type_counts = Counter()
        source_counts = Counter()

        for fname, records in all_records.items():
            for rec in records:
                meta = rec.get("metadata", {})
                subject_counts[meta.get("subject", "unknown")] += 1
                difficulty_counts[meta.get("difficulty", "unknown")] += 1
                task_type_counts[meta.get("task_type", "unknown")] += 1
                source_counts[meta.get("source", "unknown")] += 1

        # Проверка баланса subjects в сплитах
        for fname, records in all_records.items():
            file_subjects = Counter(
                rec.get("metadata", {}).get("subject", "unknown") for rec in records
            )
            total = sum(file_subjects.values())
            if total > 0:
                for subj, count in file_subjects.items():
                    pct = count / total * 100
                    if pct > 85:
                        self.add_issue(fname, 0, "info", "balance",
                                       f"Доминирование {subj}: {pct:.1f}% ({count}/{total})")

        self.report.stats["subjects"] = dict(subject_counts)
        self.report.stats["difficulties"] = dict(difficulty_counts)
        self.report.stats["task_types"] = dict(task_type_counts)
        self.report.stats["sources"] = dict(source_counts)

    def _compute_stats(self, all_records: dict):
        """Вычислить общую статистику."""
        length_stats = defaultdict(list)
        total_tokens_est = 0

        for fname, records in all_records.items():
            for rec in records:
                for msg in rec.get("messages", []):
                    if msg.get("role") == "assistant":
                        content = msg.get("content", "")
                        length_stats[fname].append(len(content))
                        # Грубая оценка токенов (~4 символа = 1 токен для русского)
                        total_tokens_est += len(content) // 4

        self.report.stats["avg_assistant_length"] = {
            fname: (sum(lengths) / len(lengths)) if lengths else 0
            for fname, lengths in length_stats.items()
        }
        self.report.stats["estimated_total_tokens"] = total_tokens_est

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Нормализовать текст для сравнения."""
        text = text.lower().strip()
        # Удалить лишние пробелы
        text = re.sub(r"\s+", " ", text)
        # Удалить пунктуацию для сравнения
        text = re.sub(r"[^\w\s]", "", text)
        return text

    @staticmethod
    def _latin_ratio(text: str) -> float:
        """Доля латинских символов."""
        if not text:
            return 0.0
        latin = sum(1 for c in text if c.isalpha() and c.isascii())
        total = sum(1 for c in text if c.isalpha())
        return latin / total if total > 0 else 0.0


def print_report(report: ValidationReport):
    """Вывести отчёт в консоль."""
    print("\n" + "=" * 70)
    print("  ОТЧЁТ ВАЛИДАЦИИ ДАТАСЕТА")
    print("=" * 70)
    print(f"\n  Файлов:        {report.total_files}")
    print(f"  Записей:       {report.total_records}")
    print(f"  Ошибки:        {len(report.errors)}")
    print(f"  Предупреждения:{len(report.warnings)}")
    print(f"  Инфо:          {len(report.infos)}")

    status = "✅ PASSED" if report.passed else "❌ FAILED"
    print(f"\n  Статус:        {status}")

    # Ошибки
    if report.errors:
        print(f"\n  --- ОШИБКИ ({len(report.errors)}) ---")
        for issue in report.errors[:20]:
            print(f"  [{issue.category}] {issue.file}:{issue.line} — {issue.message}")
        if len(report.errors) > 20:
            print(f"  ... и ещё {len(report.errors) - 20} ошибок")

    # Предупреждения (по категориям)
    if report.warnings:
        print(f"\n  --- ПРЕДУПРЕЖДЕНИЯ ({len(report.warnings)}) ---")
        categories = defaultdict(list)
        for w in report.warnings:
            categories[w.category].append(w)
        for cat, items in sorted(categories.items()):
            print(f"\n  [{cat}] ({len(items)} шт.):")
            for item in items[:5]:
                print(f"    {item.file}:{item.line} — {item.message}")
            if len(items) > 5:
                print(f"    ... и ещё {len(items) - 5}")

    # Статистика
    if report.stats:
        print(f"\n  --- СТАТИСТИКА ---")
        for key, value in report.stats.items():
            if isinstance(value, dict):
                print(f"\n  {key}:")
                for k, v in sorted(value.items()):
                    print(f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")

    print("\n" + "=" * 70)


def save_csv_report(report: ValidationReport, output_path: str):
    """Сохранить отчёт в CSV."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["severity", "category", "file", "line", "message", "field"])
        for issue in report.issues:
            writer.writerow([
                issue.severity, issue.category, issue.file,
                issue.line, issue.message, issue.field or ""
            ])

    print(f"\n  CSV-отчёт сохранён: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Валидация разметки датасета ИИ-тьютора"
    )
    parser.add_argument(
        "--data-dir", type=str, default="dataset/data/",
        help="Директория с JSONL файлами (default: dataset/data/)"
    )
    parser.add_argument(
        "--report-dir", type=str, default="reports/",
        help="Директория для CSV-отчёта (default: reports/)"
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Строгий режим: предупреждения = ошибки"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("  ВАЛИДАЦИЯ ДАТАСЕТА ИИ-ТЬЮТОРА")
    print(f"  Директория: {args.data_dir}")
    print("=" * 70)

    validator = DatasetValidator(strict=args.strict)
    report = validator.validate_directory(args.data_dir)

    print_report(report)

    csv_path = os.path.join(args.report_dir, "validation_report.csv")
    save_csv_report(report, csv_path)

    # Exit code
    if args.strict and report.warnings:
        sys.exit(1)
    if not report.passed:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
