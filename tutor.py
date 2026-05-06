"""
Модуль интеллектуального тьютора для среднего профессионального образования (СПО).

Этот модуль предоставляет систему ИИ-тьютора на базе больших языковых моделей (LLM).
Поддерживает загрузку базовых моделей и LoRA-адаптеров для генерации специализированного
образовательного контента в российских учебных заведениях СПО.

Автор: Команда ИИ СИТ (Бардаков Д.Н., Мышанская Н.Г.)
Лицензия: Apache 2.0
Версия: 0.2.0
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# Настройка логгера на уровне модуля
logger = logging.getLogger(__name__)


class ModelLoadError(Exception):
    """Исключение, возникающее при ошибке загрузки модели.

    Вызывается, когда базовую модель или LoRA-адаптеры не удалось
    загрузить из указанного пути.
    """

    def __init__(self, message: str, original_error: Optional[Exception] = None) -> None:
        """Инициализация ModelLoadError с контекстом ошибки.

        Аргументы:
            message: Человекочитаемое описание ошибки.
            original_error: Исходное исключение, вызвавшее эту ошибку.
        """
        super().__init__(message)
        self.original_error = original_error


class InferenceError(Exception):
    """Исключение, возникающее при ошибках инференса.

    Вызывается, когда генерация текста не удалась из-за
    нехватки памяти, некорректных входных данных или ошибок модели.
    """

    def __init__(self, message: str, original_error: Optional[Exception] = None) -> None:
        """Инициализация InferenceError с контекстом ошибки.

        Аргументы:
            message: Человекочитаемое описание ошибки.
            original_error: Исходное исключение, вызвавшее эту ошибку.
        """
        super().__init__(message)
        self.original_error = original_error


class IntelligentTutor:
    """ИИ-тьютор для среднего профессионального образования (СПО).

    Предоставляет интерфейс к большой языковой модели, специализированной
    для генерации образовательного контента. Поддерживает загрузку моделей
    семейства Mistral с опциональными LoRA-адаптерами, дообученными на
    учебных материалах СПО.

    Тьютор может генерировать структурированные конспекты лекций, тесты и
    персонализированные учебные материалы для студентов техникумов.

    Атрибуты:
        model: Загруженная языковая модель (базовая или с LoRA-адаптерами).
        tokenizer: Токенизатор, соответствующий загруженной модели.
        model_id: Идентификатор загруженной базовой модели.
        adapter_path: Путь к LoRA-адаптерам (если загружены), иначе None.

    Пример использования:
        >>> tutor = IntelligentTutor(
        ...     base_model_id="mistralai/Mistral-Small-24B-Instruct-2501"
        ... )
        >>> summary = tutor.generate_lecture_summary(lecture_text)
    """

    # TODO: Добавить кэширование ответов для снижения количества инференсов
    # TODO: Оптимизировать квантование для экономии видеопамяти (4-bit/8-bit)
    # TODO: Реализовать потоковый вывод для лучшего UX в веб-интерфейсе

    def __init__(
        self,
        base_model_id: str | Path,
        adapter_path: str | Path | None = None,
        *,
        torch_dtype: torch.dtype = torch.float16,
        device_map: str = "auto",
        trust_remote_code: bool = True,
        max_memory: Optional[dict[str, str]] = None,
    ) -> None:
        """Инициализация интеллектуального тьютора с базовой моделью и опциональными адаптерами.

        Загружает указанную языковую модель из Hugging Face Hub или локального пути.
        Если указан путь к адаптерам, загружает LoRA-адаптеры поверх базовой модели.

        Аргументы:
            base_model_id: ID модели Hugging Face или локальный путь к базовой модели.
                Пример: "mistralai/Mistral-Small-24B-Instruct-2501" или "/mnt/models/mistral".
            adapter_path: Путь к весам LoRA-адаптеров. Если None, загружается только базовая модель.
            torch_dtype: Тип данных для весов модели. По умолчанию: torch.float16 для экономии памяти.
            device_map: Стратегия размещения устройств. По умолчанию: "auto" для автоматического распределения GPU.
            trust_remote_code: Доверять ли удалённый код из репозитория модели.
            max_memory: Максимальная память на GPU. Пример: {"0": "20GB", "1": "20GB"}.

        Исключения:
            ModelLoadError: Если модель или адаптеры не удалось загрузить.

        Примечание:
            Загрузка модели с 24B параметров требует примерно 48GB VRAM в float16.
            Рассмотрите использование квантования для систем с меньшим объёмом памяти.
        """
        logger.info("Инициализация системы IntelligentTutor")
        logger.info(f"ID базовой модели: {base_model_id}")
        logger.debug(f"Путь к адаптерам: {adapter_path}")
        logger.debug(f"Torch dtype: {torch_dtype}, Device map: {device_map}")

        self.model_id = str(base_model_id)
        self.adapter_path = str(adapter_path) if adapter_path else None
        self._tokenizer: Optional[AutoTokenizer] = None
        self._model: Optional[AutoModelForCausalLM] = None

        try:
            self._load_tokenizer()
            self._load_model(
                torch_dtype=torch_dtype,
                device_map=device_map,
                trust_remote_code=trust_remote_code,
                max_memory=max_memory,
            )
            if adapter_path:
                self._load_adapters(adapter_path)
        except Exception as e:
            logger.error(f"Ошибка инициализации тьютора: {e}")
            raise ModelLoadError(
                f"Не удалось инициализировать IntelligentTutor с моделью {base_model_id}",
                original_error=e
            ) from e

        logger.info("IntelligentTutor успешно инициализирован")

    def _load_tokenizer(self) -> None:
        """Загрузка токенизатора для базовой модели.

        Исключения:
            ModelLoadError: Если токенизатор не удалось загрузить.
        """
        logger.info(f"Загрузка токенизатора из: {self.model_id}")
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            # Убедимся, что pad_token установлен для генерации
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token
                logger.debug("pad_token установлен в eos_token")
        except Exception as e:
            logger.error(f"Ошибка загрузки токенизатора: {e}")
            raise ModelLoadError(
                f"Не удалось загрузить токенизатор из {self.model_id}",
                original_error=e
            ) from e
        logger.info("Токенизатор успешно загружен")

    def _load_model(
        self,
        torch_dtype: torch.dtype,
        device_map: str,
        trust_remote_code: bool,
        max_memory: Optional[dict[str, str]],
    ) -> None:
        """Загрузка базовой языковой модели.

        Аргументы:
            torch_dtype: Тип данных для весов модели.
            device_map: Стратегия размещения устройств.
            trust_remote_code: Доверять ли удалённый код.
            max_memory: Максимальная память на GPU.

        Исключения:
            ModelLoadError: Если модель не удалось загрузить.
        """
        logger.info(f"Загрузка базовой модели из: {self.model_id}")
        logger.debug(f"Конфигурация модели - dtype: {torch_dtype}, device_map: {device_map}")

        try:
            kwargs = {
                "torch_dtype": torch_dtype,
                "device_map": device_map,
                "trust_remote_code": trust_remote_code,
            }
            if max_memory:
                kwargs["max_memory"] = max_memory
                logger.debug(f"Конфигурация памяти: {max_memory}")

            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                **kwargs
            )
        except torch.cuda.OutOfMemoryError as e:
            logger.critical(f"CUDA out of memory при загрузке модели: {e}")
            raise ModelLoadError(
                "Недостаточно памяти CUDA. Рассмотрите использование квантования или меньшей модели.",
                original_error=e
            ) from e
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            raise ModelLoadError(
                f"Не удалось загрузить модель из {self.model_id}",
                original_error=e
            ) from e

        logger.info("Базовая модель успешно загружена")

        # Логирование размера модели и использования памяти
        param_count = sum(p.numel() for p in self._model.parameters())
        logger.info(f"Параметры модели: {param_count / 1e9:.2f}B")

    def _load_adapters(self, adapter_path: str | Path) -> None:
        """Загрузка LoRA-адаптеров поверх базовой модели.

        Аргументы:
            adapter_path: Путь к весам LoRA-адаптеров.

        Исключения:
            ModelLoadError: Если адаптеры не удалось загрузить.
        """
        adapter_path = str(adapter_path)
        logger.info(f"Загрузка LoRA-адаптеров из: {adapter_path}")

        if not os.path.exists(adapter_path):
            logger.error(f"Путь к адаптерам не существует: {adapter_path}")
            raise ModelLoadError(
                f"Путь к адаптерам не существует: {adapter_path}"
            )

        try:
            self._model = PeftModel.from_pretrained(self._model, adapter_path)
            logger.info("LoRA-адаптеры успешно загружены")
        except Exception as e:
            logger.error(f"Ошибка загрузки адаптеров: {e}")
            raise ModelLoadError(
                f"Не удалось загрузить LoRA-адаптеры из {adapter_path}",
                original_error=e
            ) from e

    @property
    def model(self) -> AutoModelForCausalLM:
        """Получение загруженной модели.

        Возвращает:
            Загруженную языковую модель.

        Исключения:
            RuntimeError: Если модель не инициализирована.
        """
        if self._model is None:
            raise RuntimeError("Модель не инициализирована")
        return self._model

    @property
    def tokenizer(self) -> AutoTokenizer:
        """Получение загруженного токенизатора.

        Возвращает:
            Загруженный токенизатор.

        Исключения:
            RuntimeError: Если токенизатор не инициализирован.
        """
        if self._tokenizer is None:
            raise RuntimeError("Токенизатор не инициализирован")
        return self._tokenizer

    @property
    def device(self) -> torch.device:
        """Получение устройства, на котором загружена модель.

        Возвращает:
            Устройство torch модели.
        """
        return next(self.model.parameters()).device

    def generate_lecture_summary(
        self,
        lecture_text: str,
        *,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        do_sample: bool = True,
    ) -> str:
        """Генерация структурированного конспекта лекции для студентов СПО.

        Создаёт лаконичный, хорошо организованный конспект предоставленного
        текста лекции, выделяя ключевые концепции и основные положения,
        подходящие для студентов профессионального образования.

        Аргументы:
            lecture_text: Полный текст лекции для конспектирования.
            max_new_tokens: Максимальное количество токенов для генерации. По умолчанию: 512.
            temperature: Температура сэмплирования для генерации. Более высокие значения
                производят более творческие результаты. По умолчанию: 0.7.
            top_p: Порог вероятности nucleus sampling. По умолчанию: 0.9.
            top_k: Количество токенов с наивысшей вероятностью для рассмотрения. По умолчанию: 50.
            do_sample: Использовать ли сэмплирование для генерации. По умолчанию: True.

        Возвращает:
            Структурированный конспект лекции на русском языке.

        Исключения:
            InferenceError: Если генерация не удалась из-за ошибок модели или памяти.
            ValueError: Если lecture_text пустой.

        Пример использования:
            >>> lecture = "Тема: Основы промышленной автоматизации..."
            >>> summary = tutor.generate_lecture_summary(lecture)
            >>> print(summary)
        """
        # TODO: Добавить поддержку многоуровневых конспектов (базовый/углублённый)
        # TODO: Реализовать автоматическую сегментацию лекций для длинных текстов

        if not lecture_text or not lecture_text.strip():
            logger.warning("Передан пустой текст лекции")
            raise ValueError("Текст лекции не может быть пустым")

        logger.info(f"Генерация конспекта лекции (длина входа: {len(lecture_text)} символов)")
        logger.debug(f"Параметры генерации: max_tokens={max_new_tokens}, temp={temperature}")

        # Формирование промпта для модели
        prompt = self._build_summary_prompt(lecture_text)

        try:
            # Токенизация входных данных
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=4096  # Предотвращение чрезмерной длины входа
            ).to(self.device)

            input_length = inputs["input_ids"].shape[1]
            logger.debug(f"Количество входных токенов: {input_length}")

            # Генерация с torch.no_grad() для экономии памяти
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    do_sample=do_sample,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                )

            # Декодирование и извлечение только сгенерированной части
            full_output = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Извлечение только конспекта (удаление промпта)
            summary = self._extract_summary(full_output, prompt)

            logger.info(f"Конспект успешно сгенерирован (длина: {len(summary)} символов)")
            return summary

        except torch.cuda.OutOfMemoryError as e:
            logger.critical(f"CUDA OOM при генерации: {e}")
            torch.cuda.empty_cache()
            raise InferenceError(
                "Недостаточно памяти при генерации. Попробуйте уменьшить max_new_tokens.",
                original_error=e
            ) from e
        except Exception as e:
            logger.error(f"Ошибка генерации: {e}")
            raise InferenceError(
                f"Не удалось сгенерировать конспект: {str(e)}",
                original_error=e
            ) from e

    def _build_summary_prompt(self, lecture_text: str) -> str:
        """Формирование промпта для генерации конспекта.

        Аргументы:
            lecture_text: Текст лекции для конспектирования.

        Возвращает:
            Отформатированную строку промпта для модели.
        """
        return (
            "Сделай краткий структурированный конспект лекции для студента техникума. "
            "Выдели основные тезисы, используй маркированные списки.\n\n"
            f"Лекция:\n{lecture_text}\n\n"
            "Конспект:"
        )

    def _extract_summary(self, full_output: str, prompt: str) -> str:
        """Извлечение сгенерированного конспекта из полного вывода модели.

        Аргументы:
            full_output: Полный вывод модели, включая промпт.
            prompt: Исходная строка промпта.

        Возвращает:
            Извлечённый конспект без промпта.
        """
        # Простое извлечение: удаление части с промптом
        if prompt in full_output:
            return full_output.replace(prompt, "").strip()
        return full_output.strip()

    def generate_quiz(
        self,
        lecture_text: str,
        num_questions: int = 5,
        *,
        difficulty: str = "medium",
    ) -> str:
        """Генерация теста для самопроверки по содержанию лекции.

        Создаёт вопросы с выбором ответа для помощи студентам в проверке
        понимания материала лекции.

        Аргументы:
            lecture_text: Текст лекции для генерации вопросов.
            num_questions: Количество вопросов для генерации. По умолчанию: 5.
            difficulty: Уровень сложности - "easy", "medium" или "hard". По умолчанию: "medium".

        Возвращает:
            Отформатированный тест с вопросами и вариантами ответов.

        Исключения:
            InferenceError: Если генерация не удалась.
            ValueError: Если параметры некорректны.

        Примечание:
            Метод находится в разработке. Качество тестов может варьироваться.
        """
        # TODO: Реализовать генерацию тестов с ключами ответов
        # TODO: Добавить поддержку разных типов вопросов (открытые, на соответствие)
        logger.warning("Генерация тестов в разработке - результаты могут быть неоптимальными")

        if difficulty not in ("easy", "medium", "hard"):
            raise ValueError(f"Некорректный уровень сложности: {difficulty}. Допустимо: 'easy', 'medium' или 'hard'")

        if num_questions < 1 or num_questions > 20:
            raise ValueError("Количество вопросов должно быть от 1 до 20")

        logger.info(f"Генерация теста: {num_questions} вопросов, сложность: {difficulty}")

        prompt = (
            f"Создай тест из {num_questions} вопросов (сложность: {difficulty}) "
            f"по следующей лекции:\n\n{lecture_text}\n\n"
            "Тест:"
        )

        try:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=1024,
                    temperature=0.8,
                    top_p=0.9,
                )

            quiz = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            logger.info("Тест успешно сгенерирован")
            return quiz.replace(prompt, "").strip()

        except Exception as e:
            logger.error(f"Ошибка генерации теста: {e}")
            raise InferenceError(f"Не удалось сгенерировать тест: {e}", original_error=e) from e

    def chat(
        self,
        user_message: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> str:
        """Ведение диалога с тьютором.

        Позволяет студентам задавать уточняющие вопросы по материалу лекции
        в естественном разговорном формате.

        Аргументы:
            user_message: Вопрос или сообщение студента.
            conversation_history: Список предыдущих сообщений в формате
                [{"role": "user/assistant", "content": "..."}].

        Возвращает:
            Ответ тьютора на сообщение студента.

        Примечание:
            Контекст разговора ограничен контекстным окном модели.
        """
        # TODO: Реализовать правильную память диалога с суммаризацией
        # TODO: Добавить сохранение диалогов для управления сессиями

        if not user_message.strip():
            raise ValueError("Сообщение пользователя не может быть пустым")

        logger.debug(f"Обработка сообщения чата: {user_message[:50]}...")

        # Формирование контекста диалога
        if conversation_history is None:
            conversation_history = []

        messages = conversation_history + [
            {"role": "user", "content": user_message}
        ]

        # Форматирование в шаблон чата (формат Mistral)
        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        try:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=256,
                    temperature=0.7,
                    top_p=0.9,
                )

            # Извлечение только новых токенов (ответ ассистента)
            input_len = inputs["input_ids"].shape[1]
            new_tokens = outputs[0][input_len:]
            response = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

            logger.debug(f"Ответ чата сгенерирован: {len(response)} символов")
            return response

        except Exception as e:
            logger.error(f"Ошибка генерации ответа чата: {e}")
            raise InferenceError(f"Не удалось сгенерировать ответ: {e}", original_error=e) from e


def setup_logging(level: str = "INFO") -> None:
    """Настройка логирования для модуля тьютора.

    Устанавливает структурированную конфигурацию логирования с временной меткой,
    уровнем и информацией о модуле.

    Аргументы:
        level: Уровень логирования - "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL".
            По умолчанию: "INFO".
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("tutor.log", encoding="utf-8"),
        ]
    )
    logger.info(f"Логирование настроено на уровень {level}")


def main() -> None:
    """Главная точка входа для запуска тьютора из командной строки.

    Демонстрирует базовое использование класса IntelligentTutor с
    примером текста лекции.
    """
    # Загрузка конфигурации из переменных окружения
    log_level = os.getenv("LOG_LEVEL", "INFO")
    setup_logging(log_level)

    logger.info("=" * 60)
    logger.info("Запуск системы интеллектуального тьютора")
    logger.info("=" * 60)

    # Конфигурация модели
    # Для прототипа (Hugging Face):
    model_path = os.getenv(
        "MODEL_PATH",
        "mistralai/Mistral-Small-24B-Instruct-2501"
    )
    # Для локального развёртывания:
    # model_path = os.getenv("MODEL_PATH", "/mnt/models/mistral-small-24b")

    adapter_path = os.getenv("ADAPTER_PATH", None)
    # adapter_path = os.getenv("ADAPTER_PATH", "./lora-tutors-adapter")

    try:
        # Инициализация тьютора
        tutor = IntelligentTutor(
            base_model_id=model_path,
            adapter_path=adapter_path,
        )

        # Пример лекции для демонстрации
        test_lecture = (
            "Тема: Основы промышленной автоматизации. "
            "Промышленная автоматизация — это применение систем управления "
            "и информационных технологий для управления промышленными процессами. "
            "Основные компоненты: ПЛК (программируемые логические контроллеры), "
            "датчики, исполнительные механизмы, SCADA-системы."
        )

        logger.info("Генерация демонстрационного конспекта...")
        print("\n" + "=" * 60)
        print("ДЕМОНСТРАЦИЯ: Генерация конспекта лекции")
        print("=" * 60 + "\n")

        result = tutor.generate_lecture_summary(test_lecture)
        print(result)

        print("\n" + "=" * 60)
        logger.info("Демонстрация успешно завершена")

    except ModelLoadError as e:
        logger.critical(f"Ошибка загрузки модели: {e}")
        if e.original_error:
            logger.debug(f"Исходная ошибка: {e.original_error}")
        sys.exit(1)
    except InferenceError as e:
        logger.error(f"Ошибка инференса: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Прервано пользователем")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Непредвиденная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
