"""
Unit-тесты для модуля интеллектуального тьютора.

Этот модуль содержит комплексные тесты для проекта ИИ-тьютор для СПО,
следующие лучшим практикам Test-Driven Development (TDD).

Запуск тестов: pytest test_tutor.py -v
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Импорт тестируемого модуля
# Примечание: фактические импорты будут работать после корректной установки модуля
try:
    from tutor import (
        IntelligentTutor,
        ModelLoadError,
        InferenceError,
        setup_logging,
    )
except ImportError:
    # Для тестирования в изоляции без зависимостей модели
    pytest.skip("модуль tutor недоступен", allow_module_level=True)


class TestIntelligentTutorInit:
    """Тесты инициализации IntelligentTutor."""

    @patch('tutor.AutoTokenizer.from_pretrained')
    @patch('tutor.AutoModelForCausalLM.from_pretrained')
    def test_init_with_valid_model_id(
        self,
        mock_model_load: Mock,
        mock_tokenizer_load: Mock
    ) -> None:
        """Тест успешной инициализации с корректным ID модели."""
        # Подготовка
        mock_tokenizer = MagicMock()
        mock_tokenizer.pad_token = None
        mock_tokenizer.eos_token = "</s>"
        mock_tokenizer_load.return_value = mock_tokenizer

        mock_model = MagicMock()
        mock_model.parameters.return_value = [MagicMock(numel=lambda: 24000000000)]
        mock_model_load.return_value = mock_model

        # Действие
        tutor = IntelligentTutor("test-model")

        # Проверка
        assert tutor.model_id == "test-model"
        assert tutor.adapter_path is None
        mock_tokenizer_load.assert_called_once_with("test-model")
        mock_model_load.assert_called_once()

    @patch('tutor.AutoTokenizer.from_pretrained')
    def test_init_with_invalid_model_id_raises_error(
        self,
        mock_tokenizer_load: Mock
    ) -> None:
        """Тест: некорректный ID модели вызывает ModelLoadError."""
        # Подготовка
        mock_tokenizer_load.side_effect = FileNotFoundError("Модель не найдена")

        # Действие и проверка
        with pytest.raises(ModelLoadError) as exc_info:
            IntelligentTutor("invalid-model-path")

        assert "Не удалось инициализировать IntelligentTutor" in str(exc_info.value)

    @patch('tutor.AutoTokenizer.from_pretrained')
    @patch('tutor.AutoModelForCausalLM.from_pretrained')
    @patch('tutor.PeftModel.from_pretrained')
    def test_init_with_adapter(
        self,
        mock_peft_load: Mock,
        mock_model_load: Mock,
        mock_tokenizer_load: Mock
    ) -> None:
        """Тест инициализации с загрузкой LoRA-адаптера."""
        # Подготовка
        mock_tokenizer = MagicMock()
        mock_tokenizer.pad_token = None
        mock_tokenizer_load.return_value = mock_tokenizer

        mock_model = MagicMock()
        mock_model.parameters.return_value = [MagicMock(numel=lambda: 24000000000)]
        mock_model_load.return_value = mock_model

        mock_peft_model = MagicMock()
        mock_peft_load.return_value = mock_peft_model

        # Действие
        tutor = IntelligentTutor("test-model", adapter_path="./lora-adapter")

        # Проверка
        assert tutor.adapter_path == "./lora-adapter"
        mock_peft_load.assert_called_once()


class TestIntelligentTutorGeneration:
    """Тесты методов генерации текста."""

    @pytest.fixture
    def mock_tutor(self) -> IntelligentTutor:
        """Создание замоканного экземпляра IntelligentTutor."""
        with patch('tutor.AutoTokenizer.from_pretrained') as mock_tokenizer, \
             patch('tutor.AutoModelForCausalLM.from_pretrained') as mock_model:

            mock_tok = MagicMock()
            mock_tok.pad_token = None
            mock_tok.eos_token = "</s>"
            mock_tok.return_value = {"input_ids": MagicMock(shape=(1, 10))}
            mock_tokenizer.return_value = mock_tok

            mock_mod = MagicMock()
            mock_mod.parameters.return_value = [MagicMock(numel=lambda: 24000000000)]
            mock_mod.device = "cuda:0"
            mock_model.return_value = mock_mod

            tutor = IntelligentTutor("test-model")
            tutor._tokenizer = mock_tok
            tutor._model = mock_mod

            return tutor

    def test_generate_summary_with_empty_text_raises_error(
        self,
        mock_tutor: IntelligentTutor
    ) -> None:
        """Тест: пустой текст лекции вызывает ValueError."""
        # Действие и проверка
        with pytest.raises(ValueError, match="не может быть пустым"):
            mock_tutor.generate_lecture_summary("")

        with pytest.raises(ValueError, match="не может быть пустым"):
            mock_tutor.generate_lecture_summary("   ")

    def test_generate_summary_with_valid_text(
        self,
        mock_tutor: IntelligentTutor
    ) -> None:
        """Тест успешной генерации конспекта."""
        # Подготовка
        mock_tutor.tokenizer.decode.return_value = "Тестовый конспект"
        mock_tutor.model.generate.return_value = [MagicMock()]

        # Действие
        result = mock_tutor.generate_lecture_summary("Текст тестовой лекции")

        # Проверка
        assert isinstance(result, str)
        assert len(result) > 0


class TestErrorHandling:
    """Тесты кастомных классов исключений."""

    def test_model_load_error_with_original_error(self) -> None:
        """Тест: ModelLoadError сохраняет исходное исключение."""
        # Подготовка
        original = FileNotFoundError("Файл не найден")

        # Действие
        error = ModelLoadError("Ошибка загрузки", original_error=original)

        # Проверка
        assert error.original_error == original
        assert str(error) == "Ошибка загрузки"

    def test_inference_error_with_original_error(self) -> None:
        """Тест: InferenceError сохраняет исходное исключение."""
        # Подготовка
        original = RuntimeError("Ошибка CUDA")

        # Действие
        error = InferenceError("Ошибка генерации", original_error=original)

        # Проверка
        assert error.original_error == original


class TestLogging:
    """Тесты конфигурации логирования."""

    @patch('tutor.logging.basicConfig')
    def test_setup_logging_default_level(self, mock_config: Mock) -> None:
        """Тест настройки логирования с уровнем INFO по умолчанию."""
        # Действие
        setup_logging()

        # Проверка
        mock_config.assert_called_once()
        call_kwargs = mock_config.call_args[1]
        assert call_kwargs['level'] == 20  # Уровень INFO

    @patch('tutor.logging.basicConfig')
    def test_setup_logging_custom_level(self, mock_config: Mock) -> None:
        """Тест настройки логирования с кастомным уровнем DEBUG."""
        # Действие
        setup_logging("DEBUG")

        # Проверка
        call_kwargs = mock_config.call_args[1]
        assert call_kwargs['level'] == 10  # Уровень DEBUG


class TestImports:
    """Базовые тесты импортов для проверки структуры модуля."""

    def test_module_importable(self) -> None:
        """Тест: модуль tutor может быть импортирован."""
        # Тест считается пройденным, если мы дошли сюда без ImportError
        import tutor
        assert hasattr(tutor, 'IntelligentTutor')

    def test_exception_classes_exist(self) -> None:
        """Тест: кастомные классы исключений определены."""
        from tutor import ModelLoadError, InferenceError

        assert issubclass(ModelLoadError, Exception)
        assert issubclass(InferenceError, Exception)


# =============================================================================
# Интеграционные тесты (требуют реальной модели — пропускаются в CI)
# =============================================================================

@pytest.mark.integration
class TestIntegration:
    """Интеграционные тесты, требующие реальной загрузки модели.

    Эти тесты помечены @pytest.mark.integration и будут пропущены по умолчанию.
    Запуск: pytest -m integration
    """

    @pytest.mark.skip(reason="Требует реальной модели и GPU")
    def test_real_model_loading(self) -> None:
        """Тест загрузки реальной модели из Hugging Face."""
        # Этот тест загрузил бы реальную модель
        # Запускать вручную только с правильной настройкой GPU
        pass

    @pytest.mark.skip(reason="Требует реальной модели и GPU")
    def test_real_inference(self) -> None:
        """Тест реального инференса с реальной моделью."""
        pass


# =============================================================================
# Фикстуры и конфигурация
# =============================================================================

def pytest_configure(config: pytest.Config) -> None:
    """Конфигурация кастомных маркеров pytest."""
    config.addinivalue_line(
        "markers", "integration: помечает тесты как интеграционные"
    )


if __name__ == "__main__":
    # Запуск тестов при прямом выполнении
    pytest.main([__file__, "-v", "--tb=short"])
