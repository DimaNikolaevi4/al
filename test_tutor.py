"""
Unit tests for the Intelligent Tutor module.

This module contains comprehensive tests for the AI Tutor SPO project,
following Test-Driven Development (TDD) best practices.

Run tests with: pytest test_tutor.py -v
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import the module under test
# Note: Actual imports will work once the module is properly installed
try:
    from tutor import (
        IntelligentTutor,
        ModelLoadError,
        InferenceError,
        setup_logging,
    )
except ImportError:
    # For testing in isolation without model dependencies
    pytest.skip("tutor module not available", allow_module_level=True)


class TestIntelligentTutorInit:
    """Tests for IntelligentTutor initialization."""

    @patch('tutor.AutoTokenizer.from_pretrained')
    @patch('tutor.AutoModelForCausalLM.from_pretrained')
    def test_init_with_valid_model_id(
        self,
        mock_model_load: Mock,
        mock_tokenizer_load: Mock
    ) -> None:
        """Test successful initialization with a valid model ID."""
        # Arrange
        mock_tokenizer = MagicMock()
        mock_tokenizer.pad_token = None
        mock_tokenizer.eos_token = "</s>"
        mock_tokenizer_load.return_value = mock_tokenizer

        mock_model = MagicMock()
        mock_model.parameters.return_value = [MagicMock(numel=lambda: 24000000000)]
        mock_model_load.return_value = mock_model

        # Act
        tutor = IntelligentTutor("test-model")

        # Assert
        assert tutor.model_id == "test-model"
        assert tutor.adapter_path is None
        mock_tokenizer_load.assert_called_once_with("test-model")
        mock_model_load.assert_called_once()

    @patch('tutor.AutoTokenizer.from_pretrained')
    def test_init_with_invalid_model_id_raises_error(
        self,
        mock_tokenizer_load: Mock
    ) -> None:
        """Test that invalid model ID raises ModelLoadError."""
        # Arrange
        mock_tokenizer_load.side_effect = FileNotFoundError("Model not found")

        # Act & Assert
        with pytest.raises(ModelLoadError) as exc_info:
            IntelligentTutor("invalid-model-path")

        assert "Failed to initialize IntelligentTutor" in str(exc_info.value)

    @patch('tutor.AutoTokenizer.from_pretrained')
    @patch('tutor.AutoModelForCausalLM.from_pretrained')
    @patch('tutor.PeftModel.from_pretrained')
    def test_init_with_adapter(
        self,
        mock_peft_load: Mock,
        mock_model_load: Mock,
        mock_tokenizer_load: Mock
    ) -> None:
        """Test initialization with LoRA adapter loading."""
        # Arrange
        mock_tokenizer = MagicMock()
        mock_tokenizer.pad_token = None
        mock_tokenizer_load.return_value = mock_tokenizer

        mock_model = MagicMock()
        mock_model.parameters.return_value = [MagicMock(numel=lambda: 24000000000)]
        mock_model_load.return_value = mock_model

        mock_peft_model = MagicMock()
        mock_peft_load.return_value = mock_peft_model

        # Act
        tutor = IntelligentTutor("test-model", adapter_path="./lora-adapter")

        # Assert
        assert tutor.adapter_path == "./lora-adapter"
        mock_peft_load.assert_called_once()


class TestIntelligentTutorGeneration:
    """Tests for text generation methods."""

    @pytest.fixture
    def mock_tutor(self) -> IntelligentTutor:
        """Create a mocked IntelligentTutor instance."""
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
        """Test that empty lecture text raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="cannot be empty"):
            mock_tutor.generate_lecture_summary("")

        with pytest.raises(ValueError, match="cannot be empty"):
            mock_tutor.generate_lecture_summary("   ")

    def test_generate_summary_with_valid_text(
        self,
        mock_tutor: IntelligentTutor
    ) -> None:
        """Test successful summary generation."""
        # Arrange
        mock_tutor.tokenizer.decode.return_value = "Test summary output"
        mock_tutor.model.generate.return_value = [MagicMock()]

        # Act
        result = mock_tutor.generate_lecture_summary("Test lecture content")

        # Assert
        assert isinstance(result, str)
        assert len(result) > 0


class TestErrorHandling:
    """Tests for custom exception classes."""

    def test_model_load_error_with_original_error(self) -> None:
        """Test ModelLoadError preserves original exception."""
        # Arrange
        original = FileNotFoundError("File not found")

        # Act
        error = ModelLoadError("Failed to load", original_error=original)

        # Assert
        assert error.original_error == original
        assert str(error) == "Failed to load"

    def test_inference_error_with_original_error(self) -> None:
        """Test InferenceError preserves original exception."""
        # Arrange
        original = RuntimeError("CUDA error")

        # Act
        error = InferenceError("Generation failed", original_error=original)

        # Assert
        assert error.original_error == original


class TestLogging:
    """Tests for logging configuration."""

    @patch('tutor.logging.basicConfig')
    def test_setup_logging_default_level(self, mock_config: Mock) -> None:
        """Test logging setup with default INFO level."""
        # Act
        setup_logging()

        # Assert
        mock_config.assert_called_once()
        call_kwargs = mock_config.call_args[1]
        assert call_kwargs['level'] == 20  # INFO level

    @patch('tutor.logging.basicConfig')
    def test_setup_logging_custom_level(self, mock_config: Mock) -> None:
        """Test logging setup with custom DEBUG level."""
        # Act
        setup_logging("DEBUG")

        # Assert
        call_kwargs = mock_config.call_args[1]
        assert call_kwargs['level'] == 10  # DEBUG level


class TestImports:
    """Basic import tests to ensure module structure."""

    def test_module_importable(self) -> None:
        """Test that the tutor module can be imported."""
        # This test passes if we got here without ImportError
        import tutor
        assert hasattr(tutor, 'IntelligentTutor')

    def test_exception_classes_exist(self) -> None:
        """Test that custom exception classes are defined."""
        from tutor import ModelLoadError, InferenceError

        assert issubclass(ModelLoadError, Exception)
        assert issubclass(InferenceError, Exception)


# =============================================================================
# Integration Tests (require actual model - skip in CI)
# =============================================================================

@pytest.mark.integration
class TestIntegration:
    """Integration tests requiring actual model loading.

    These tests are marked with @pytest.mark.integration and will be
    skipped by default. Run with: pytest -m integration
    """

    @pytest.mark.skip(reason="Requires actual model and GPU")
    def test_real_model_loading(self) -> None:
        """Test loading actual model from Hugging Face."""
        # This test would load the real model
        # Run manually only with proper GPU setup
        pass

    @pytest.mark.skip(reason="Requires actual model and GPU")
    def test_real_inference(self) -> None:
        """Test actual inference with real model."""
        pass


# =============================================================================
# Fixtures and Configuration
# =============================================================================

def pytest_configure(config: pytest.Config) -> None:
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v", "--tb=short"])
