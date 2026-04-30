"""
Intelligent Tutor Module for Vocational Education (SPO).

This module provides an AI-powered tutoring system based on Large Language Models (LLM).
It supports loading base models and LoRA adapters for specialized educational content
generation in Russian vocational education institutions.

Author: SIT College AI Team (Bardakov D.N., Myshanskaya N.G.)
License: Apache 2.0
Version: 0.2.0
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

# Configure module-level logger
logger = logging.getLogger(__name__)


class ModelLoadError(Exception):
    """Custom exception raised when model loading fails.

    This exception is raised when the base model or LoRA adapters
    cannot be loaded from the specified path.
    """

    def __init__(self, message: str, original_error: Optional[Exception] = None) -> None:
        """Initialize ModelLoadError with context.

        Args:
            message: Human-readable error description.
            original_error: The original exception that caused this error.
        """
        super().__init__(message)
        self.original_error = original_error


class InferenceError(Exception):
    """Custom exception raised during inference failures.

    This exception is raised when text generation fails due to
    memory constraints, invalid inputs, or model errors.
    """

    def __init__(self, message: str, original_error: Optional[Exception] = None) -> None:
        """Initialize InferenceError with context.

        Args:
            message: Human-readable error description.
            original_error: The original exception that caused this error.
        """
        super().__init__(message)
        self.original_error = original_error


class IntelligentTutor:
    """AI-powered intelligent tutor for vocational education (SPO).

    This class provides an interface to a Large Language Model specialized
    for educational content generation. It supports loading Mistral-family
    models with optional LoRA adapters fine-tuned on SPO curriculum materials.

    The tutor can generate structured lecture summaries, quizzes, and
    personalized learning materials for students in technical colleges.

    Attributes:
        model: The loaded language model (base or with LoRA adapters).
        tokenizer: The tokenizer corresponding to the loaded model.
        model_id: Identifier of the loaded base model.
        adapter_path: Path to LoRA adapters if loaded, None otherwise.

    Example:
        >>> tutor = IntelligentTutor(
        ...     base_model_id="mistralai/Mistral-Small-24B-Instruct-2501"
        ... )
        >>> summary = tutor.generate_lecture_summary(lecture_text)
    """

    # TODO: Add response caching to reduce redundant inference calls
    # TODO: Optimize quantization for lower VRAM usage (4-bit/8-bit)
    # TODO: Implement streaming output for better UX in web interface

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
        """Initialize the Intelligent Tutor with a base model and optional adapters.

        Loads the specified language model from Hugging Face Hub or local path.
        If an adapter path is provided, loads LoRA adapters on top of the base model.

        Args:
            base_model_id: Hugging Face model ID or local path to the base model.
                Example: "mistralai/Mistral-Small-24B-Instruct-2501" or "/mnt/models/mistral".
            adapter_path: Path to LoRA adapter weights. If None, only base model is loaded.
            torch_dtype: Data type for model weights. Default: torch.float16 for memory efficiency.
            device_map: Strategy for device placement. Default: "auto" for automatic GPU allocation.
            trust_remote_code: Whether to trust remote code from model repository.
            max_memory: Maximum memory per GPU. Example: {"0": "20GB", "1": "20GB"}.

        Raises:
            ModelLoadError: If the model or adapters cannot be loaded.

        Note:
            Loading a 24B parameter model requires approximately 48GB VRAM in float16.
            Consider using quantization for lower-memory setups.
        """
        logger.info("Initializing IntelligentTutor system")
        logger.info(f"Base model ID: {base_model_id}")
        logger.debug(f"Adapter path: {adapter_path}")
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
            logger.error(f"Failed to initialize tutor: {e}")
            raise ModelLoadError(
                f"Failed to initialize IntelligentTutor with model {base_model_id}",
                original_error=e
            ) from e

        logger.info("IntelligentTutor initialized successfully")

    def _load_tokenizer(self) -> None:
        """Load the tokenizer for the base model.

        Raises:
            ModelLoadError: If tokenizer cannot be loaded.
        """
        logger.info(f"Loading tokenizer from: {self.model_id}")
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            # Ensure pad token is set for generation
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token
                logger.debug("Set pad_token to eos_token")
        except Exception as e:
            logger.error(f"Failed to load tokenizer: {e}")
            raise ModelLoadError(
                f"Failed to load tokenizer from {self.model_id}",
                original_error=e
            ) from e
        logger.info("Tokenizer loaded successfully")

    def _load_model(
        self,
        torch_dtype: torch.dtype,
        device_map: str,
        trust_remote_code: bool,
        max_memory: Optional[dict[str, str]],
    ) -> None:
        """Load the base language model.

        Args:
            torch_dtype: Data type for model weights.
            device_map: Strategy for device placement.
            trust_remote_code: Whether to trust remote code.
            max_memory: Maximum memory per GPU.

        Raises:
            ModelLoadError: If model cannot be loaded.
        """
        logger.info(f"Loading base model from: {self.model_id}")
        logger.debug(f"Model config - dtype: {torch_dtype}, device_map: {device_map}")

        try:
            kwargs = {
                "torch_dtype": torch_dtype,
                "device_map": device_map,
                "trust_remote_code": trust_remote_code,
            }
            if max_memory:
                kwargs["max_memory"] = max_memory
                logger.debug(f"Max memory config: {max_memory}")

            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                **kwargs
            )
        except torch.cuda.OutOfMemoryError as e:
            logger.critical(f"CUDA out of memory while loading model: {e}")
            raise ModelLoadError(
                "CUDA out of memory. Consider using quantization or smaller model.",
                original_error=e
            ) from e
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise ModelLoadError(
                f"Failed to load model from {self.model_id}",
                original_error=e
            ) from e

        logger.info("Base model loaded successfully")

        # Log model size and memory usage
        param_count = sum(p.numel() for p in self._model.parameters())
        logger.info(f"Model parameters: {param_count / 1e9:.2f}B")

    def _load_adapters(self, adapter_path: str | Path) -> None:
        """Load LoRA adapters on top of the base model.

        Args:
            adapter_path: Path to the LoRA adapter weights.

        Raises:
            ModelLoadError: If adapters cannot be loaded.
        """
        adapter_path = str(adapter_path)
        logger.info(f"Loading LoRA adapters from: {adapter_path}")

        if not os.path.exists(adapter_path):
            logger.error(f"Adapter path does not exist: {adapter_path}")
            raise ModelLoadError(
                f"Adapter path does not exist: {adapter_path}"
            )

        try:
            self._model = PeftModel.from_pretrained(self._model, adapter_path)
            logger.info("LoRA adapters loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load adapters: {e}")
            raise ModelLoadError(
                f"Failed to load LoRA adapters from {adapter_path}",
                original_error=e
            ) from e

    @property
    def model(self) -> AutoModelForCausalLM:
        """Get the loaded model instance.

        Returns:
            The loaded language model.

        Raises:
            RuntimeError: If model is not initialized.
        """
        if self._model is None:
            raise RuntimeError("Model not initialized")
        return self._model

    @property
    def tokenizer(self) -> AutoTokenizer:
        """Get the loaded tokenizer instance.

        Returns:
            The loaded tokenizer.

        Raises:
            RuntimeError: If tokenizer is not initialized.
        """
        if self._tokenizer is None:
            raise RuntimeError("Tokenizer not initialized")
        return self._tokenizer

    @property
    def device(self) -> torch.device:
        """Get the device where the model is loaded.

        Returns:
            The torch device of the model.
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
        """Generate a structured summary of a lecture for SPO students.

        Creates a concise, well-organized summary of the provided lecture text,
        highlighting key concepts and main points suitable for vocational
        education students.

        Args:
            lecture_text: The full text of the lecture to summarize.
            max_new_tokens: Maximum number of tokens to generate. Default: 512.
            temperature: Sampling temperature for generation. Higher values produce
                more creative outputs. Default: 0.7.
            top_p: Nucleus sampling probability threshold. Default: 0.9.
            top_k: Number of highest probability tokens to consider. Default: 50.
            do_sample: Whether to use sampling for generation. Default: True.

        Returns:
            A structured summary of the lecture in Russian.

        Raises:
            InferenceError: If generation fails due to model or memory errors.
            ValueError: If lecture_text is empty.

        Example:
            >>> lecture = "Тема: Основы промышленной автоматизации..."
            >>> summary = tutor.generate_lecture_summary(lecture)
            >>> print(summary)
        """
        # TODO: Add support for multi-level summaries (basic/advanced)
        # TODO: Implement automatic lecture segmentation for long texts

        if not lecture_text or not lecture_text.strip():
            logger.warning("Empty lecture text provided")
            raise ValueError("Lecture text cannot be empty")

        logger.info(f"Generating lecture summary (input length: {len(lecture_text)} chars)")
        logger.debug(f"Generation params: max_tokens={max_new_tokens}, temp={temperature}")

        # Construct prompt for the model
        prompt = self._build_summary_prompt(lecture_text)

        try:
            # Tokenize input
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=4096  # Prevent excessive input length
            ).to(self.device)

            input_length = inputs["input_ids"].shape[1]
            logger.debug(f"Input token count: {input_length}")

            # Generate with torch.no_grad() to save memory
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

            # Decode and extract only the generated part
            full_output = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Extract only the summary (remove the prompt)
            summary = self._extract_summary(full_output, prompt)

            logger.info(f"Summary generated successfully (length: {len(summary)} chars)")
            return summary

        except torch.cuda.OutOfMemoryError as e:
            logger.critical(f"CUDA OOM during generation: {e}")
            torch.cuda.empty_cache()
            raise InferenceError(
                "Out of memory during generation. Try reducing max_new_tokens.",
                original_error=e
            ) from e
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise InferenceError(
                f"Failed to generate summary: {str(e)}",
                original_error=e
            ) from e

    def _build_summary_prompt(self, lecture_text: str) -> str:
        """Build the prompt for summary generation.

        Args:
            lecture_text: The lecture text to summarize.

        Returns:
            Formatted prompt string for the model.
        """
        return (
            "Сделай краткий структурированный конспект лекции для студента техникума. "
            "Выдели основные тезисы, используй маркированные списки.\n\n"
            f"Лекция:\n{lecture_text}\n\n"
            "Конспект:"
        )

    def _extract_summary(self, full_output: str, prompt: str) -> str:
        """Extract the generated summary from the full model output.

        Args:
            full_output: The complete model output including prompt.
            prompt: The original prompt string.

        Returns:
            The extracted summary without the prompt.
        """
        # Simple extraction: remove the prompt part
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
        """Generate a self-assessment quiz based on lecture content.

        Creates multiple-choice questions to help students test their
        understanding of the lecture material.

        Args:
            lecture_text: The lecture text to generate questions from.
            num_questions: Number of questions to generate. Default: 5.
            difficulty: Difficulty level - "easy", "medium", or "hard". Default: "medium".

        Returns:
            A formatted quiz with questions and answer options.

        Raises:
            InferenceError: If generation fails.
            ValueError: If parameters are invalid.

        Note:
            This method is currently in development. Quiz quality may vary.
        """
        # TODO: Implement quiz generation with answer key
        # TODO: Add support for different question types (open-ended, matching)
        logger.warning("Quiz generation is in development - results may be suboptimal")

        if difficulty not in ("easy", "medium", "hard"):
            raise ValueError(f"Invalid difficulty: {difficulty}. Must be 'easy', 'medium', or 'hard'")

        if num_questions < 1 or num_questions > 20:
            raise ValueError("num_questions must be between 1 and 20")

        logger.info(f"Generating quiz: {num_questions} questions, difficulty: {difficulty}")

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
            logger.info("Quiz generated successfully")
            return quiz.replace(prompt, "").strip()

        except Exception as e:
            logger.error(f"Quiz generation failed: {e}")
            raise InferenceError(f"Failed to generate quiz: {e}", original_error=e) from e

    def chat(
        self,
        user_message: str,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> str:
        """Engage in a conversational dialogue with the tutor.

        Allows students to ask follow-up questions about lecture material
        in a natural conversational format.

        Args:
            user_message: The student's question or message.
            conversation_history: List of previous messages in the format
                [{"role": "user/assistant", "content": "..."}].

        Returns:
            The tutor's response to the student's message.

        Note:
            Conversation context is limited by the model's context window.
        """
        # TODO: Implement proper conversation memory with summarization
        # TODO: Add conversation persistence for session management

        if not user_message.strip():
            raise ValueError("User message cannot be empty")

        logger.debug(f"Processing chat message: {user_message[:50]}...")

        # Build conversation context
        if conversation_history is None:
            conversation_history = []

        messages = conversation_history + [
            {"role": "user", "content": user_message}
        ]

        # Format as chat template (Mistral format)
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

            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Extract only the assistant's response
            if "[/INST]" in response:
                response = response.split("[/INST]")[-1].strip()

            logger.debug(f"Chat response generated: {len(response)} chars")
            return response

        except Exception as e:
            logger.error(f"Chat generation failed: {e}")
            raise InferenceError(f"Failed to generate response: {e}", original_error=e) from e


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the tutor module.

    Sets up a structured logging configuration with timestamp, level,
    and module information.

    Args:
        level: Logging level - "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL".
            Default: "INFO".
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
    logger.info(f"Logging configured at {level} level")


def main() -> None:
    """Main entry point for running the tutor from command line.

    Demonstrates basic usage of the IntelligentTutor class with
    a sample lecture text.
    """
    # Load configuration from environment
    log_level = os.getenv("LOG_LEVEL", "INFO")
    setup_logging(log_level)

    logger.info("=" * 60)
    logger.info("Starting Intelligent Tutor System")
    logger.info("=" * 60)

    # Model configuration
    # For prototype (Hugging Face):
    model_path = os.getenv(
        "MODEL_PATH",
        "mistralai/Mistral-Small-24B-Instruct-2501"
    )
    # For local deployment:
    # model_path = os.getenv("MODEL_PATH", "/mnt/models/mistral-small-24b")

    adapter_path = os.getenv("ADAPTER_PATH", None)
    # adapter_path = os.getenv("ADAPTER_PATH", "./lora-tutors-adapter")

    try:
        # Initialize tutor
        tutor = IntelligentTutor(
            base_model_id=model_path,
            adapter_path=adapter_path,
        )

        # Sample lecture for demonstration
        test_lecture = (
            "Тема: Основы промышленной автоматизации. "
            "Промышленная автоматизация — это применение систем управления "
            "и информационных технологий для управления промышленными процессами. "
            "Основные компоненты: ПЛК (программируемые логические контроллеры), "
            "датчики, исполнительные механизмы, SCADA-системы."
        )

        logger.info("Generating demonstration summary...")
        print("\n" + "=" * 60)
        print("ДЕМОНСТРАЦИЯ: Генерация конспекта лекции")
        print("=" * 60 + "\n")

        result = tutor.generate_lecture_summary(test_lecture)
        print(result)

        print("\n" + "=" * 60)
        logger.info("Demonstration completed successfully")

    except ModelLoadError as e:
        logger.critical(f"Failed to load model: {e}")
        if e.original_error:
            logger.debug(f"Original error: {e.original_error}")
        sys.exit(1)
    except InferenceError as e:
        logger.error(f"Inference failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
