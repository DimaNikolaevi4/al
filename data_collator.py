"""
Кастомный коллатор данных для обучения ИИ-тьютора.

Обеспечивает корректную токенизацию датасета в формате чата (messages)
для модели Mistral Small 24B Instruct. Поддерживает динамический паддинг
и маскирование токенов для эффективного обучения.

Формат входных данных (JSONL):
    {"messages": [{"role": "system", "content": "..."},
                  {"role": "user", "content": "..."},
                  {"role": "assistant", "content": "..."}],
     "metadata": {...}}

Автор: Команда ИИ СИТ (Бардаков Д.Н.)
Лицензия: Apache 2.0
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import torch
from transformers import PreTrainedTokenizerBase

logger = logging.getLogger(__name__)


class TutorDataCollator:
    """Коллатор данных для SFT-обучения ИИ-тьютора.

    Принимает список примеров датасета (в формате messages) и формирует
    батч тензоров для обучения. Использует chat_template токенизатора
    для корректного форматирования, маскирует prompt-токены (они не
    участвуют в вычислении loss) и применяет динамический паддинг.

    Атрибуты:
        tokenizer: Токенизатор модели.
        max_seq_length: Максимальная длина последовательности в токенах.
        pad_to_multiple_of: Выравнивание длины для оптимизации на GPU.
        ignore_index: Индекс для маскирования prompt-токенов в loss.
    """

    def __init__(
        self,
        tokenizer: PreTrainedTokenizerBase,
        max_seq_length: int = 2048,
        pad_to_multiple_of: int = 8,
        ignore_index: int = -100,
    ) -> None:
        """Инициализация коллатора.

        Аргументы:
            tokenizer: Токенизатор модели HuggingFace.
            max_seq_length: Максимальная длина последовательности.
                Примеры длиннее обрезаются.
            pad_to_multiple_of: Выравнивание длины батча. Значение 8
                оптимально для GPU (особенно для tensor cores).
            ignore_index: Индекс метки, который игнорируется при вычислении
                loss. Используется для маскирования prompt-токенов, чтобы
                модель училась генерировать только assistant-ответы.
        """
        self.tokenizer = tokenizer
        self.max_seq_length = max_seq_length
        self.pad_to_multiple_of = pad_to_multiple_of
        self.ignore_index = ignore_index

        # Убеждаемся, что pad_token существует
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
            logger.debug("pad_token установлен в eos_token")

        logger.info(
            f"Коллатор инициализирован: max_seq_length={max_seq_length}, "
            f"pad_to_multiple_of={pad_to_multiple_of}"
        )

    def __call__(self, examples: list[dict[str, Any]]) -> dict[str, torch.Tensor]:
        """Формирование батча из списка примеров.

        Для каждого примера:
        1. Применяется chat_template для форматирования диалога.
        2. Токенизируется с усечением до max_seq_length.
        3. Создаются labels с замаскированными prompt-токенами.

        Аргументы:
            examples: Список словарей с ключом "messages" (формат чата).

        Возвращает:
            Словарь с ключами:
                - input_ids: тензор [batch_size, seq_len]
                - attention_mask: тензор [batch_size, seq_len]
                - labels: тензор [batch_size, seq_len] (prompt замаскирован)
        """
        # Формируем тексты диалогов через chat_template
        texts = []
        for example in examples:
            messages = example["messages"]
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=False,
            )
            texts.append(text)

        # Токенизация с паддинг до максимальной длины в батче
        tokenized = self.tokenizer(
            texts,
            truncation=True,
            max_length=self.max_seq_length,
            padding="longest",
            pad_to_multiple_of=self.pad_to_multiple_of,
            return_tensors=None,  # Возвращаем списки, потом конвертируем
        )

        # Создаём labels: копируем input_ids, маскируем non-assistant токены
        batch = {
            "input_ids": [],
            "attention_mask": [],
            "labels": [],
        }

        for i, text in enumerate(texts):
            input_ids = tokenized["input_ids"][i]
            attention_mask = tokenized["attention_mask"][i]

            # Определяем, где начинается ответ assistant
            labels = self._create_labels(text, input_ids)

            batch["input_ids"].append(input_ids)
            batch["attention_mask"].append(attention_mask)
            batch["labels"].append(labels)

        # Конвертация в тензоры
        batch = {
            key: torch.tensor(value, dtype=torch.long)
            for key, value in batch.items()
        }

        if logger.isEnabledFor(logging.DEBUG):
            seq_len = batch["input_ids"].shape[1]
            masked = (batch["labels"][0] == self.ignore_index).sum().item()
            total = batch["labels"][0].ne(self.ignore_index).sum().item() + masked
            logger.debug(
                f"Батч: {len(examples)} примеров, seq_len={seq_len}, "
                f"замаскировано токенов: {masked}/{total} ({masked/max(total,1)*100:.1f}%)"
            )

        return batch

    def _create_labels(
        self,
        text: str,
        input_ids: list[int],
    ) -> list[int]:
        """Создание labels с замаскированными prompt-токенами.

        Стратегия: находим последнее вхождение маркера начала ответа
        ассистента в токенизированной последовательности. Все токены
        до него (system + user) заменяются на ignore_index.

        Для Mistral-формата ответ ассистента начинается после
        последнего "[/INST]" или после "assistant\n" / "<|assistant| >".

        Аргументы:
            text: Исходный текст диалога (для поиска маркеров).
            input_ids: Список токенов.

        Возвращает:
            Список labels с замаскированными prompt-токенами.
        """
        labels = list(input_ids)

        # Стратегия: замаскировать все токены, кроме последнего assistant-ответа
        # Ищем позицию начала ответа assistant в тексте
        assistant_start = self._find_assistant_start(text)

        if assistant_start is not None:
            # Токенизируем prompt-часть (до assistant-ответа)
            prompt_text = text[:assistant_start]
            prompt_tokens = self.tokenizer(
                prompt_text,
                add_special_tokens=False,
                truncation=False,
            )["input_ids"]

            # Маскируем все prompt-токены
            mask_len = len(prompt_tokens)
            labels[:mask_len] = [self.ignore_index] * mask_len
        else:
            # Fallback: если не нашли маркер, маскируем до последней трети
            # (грубая эвристика — лучше переобучиться на всем, чем ни на чём)
            logger.warning(
                "Не удалось найти маркер начала assistant-ответа. "
                "Используется fallback: маскирование до последней трети."
            )
            mask_len = len(labels) * 2 // 3
            labels[:mask_len] = [self.ignore_index] * mask_len

        return labels

    def _find_assistant_start(self, text: str) -> Optional[int]:
        """Поиск позиции начала ответа assistant в тексте.

        Поддерживаемые форматы ( Mistral):
            - "<|assistant| >"
            - "[/INST]" (для старых Mistral-7B)
            - "assistant\n" (ChatML)

        Аргументы:
            text: Текст диалога.

        Возвращает:
            Индекс начала ответа assistant или None.
        """
        # Приоритет: самые специфичные маркеры сначала
        markers = [
            "<|assistant| >",
            "<|assistant|",
            "[/INST]",
            "assistant\n",
        ]

        for marker in markers:
            last_pos = text.rfind(marker)
            if last_pos != -1:
                # Позиция — после маркера
                return last_pos + len(marker)

        return None
