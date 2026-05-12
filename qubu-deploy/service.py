"""
BentoML 1.2+ inference service for AI Tutor on Qubu platform (GGUF variant).

Uses llama-cpp-python with pre-built CUDA 12.1 wheel.
No compilation needed — fast deployment within Qubu's 50-min timeout.

Qubu launch command:  bentoml serve service:Service

Endpoints:
  /health           — health check
  /predict          — Qubu Builder endpoint (inputs.message -> result.answer)
  /generate_summary — structured lecture summary
  /generate_quiz    — self-check quiz questions
  /chat             — dialog with the tutor

Author: Komanda II SIT (Bardakov D.N., Myshanskaya N.G.)
License: Apache 2.0
"""

import os
import glob
import logging
from typing import Any, Dict

import bentoml

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=os.sys.stdout,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config (override via environment variables)
# ---------------------------------------------------------------------------

MODEL_PATH = os.environ.get("MODEL_PATH", "/workspace/model")
N_CTX = int(os.environ.get("N_CTX", "2048"))
N_GPU_LAYERS = int(os.environ.get("N_GPU_LAYERS", "-1"))  # -1 = all on GPU
MAX_NEW_TOKENS_SUMMARY = int(os.environ.get("MAX_NEW_TOKENS_SUMMARY", "512"))
MAX_NEW_TOKENS_QUIZ = int(os.environ.get("MAX_NEW_TOKENS_QUIZ", "1024"))
MAX_NEW_TOKENS_CHAT = int(os.environ.get("MAX_NEW_TOKENS_CHAT", "256"))

# ---------------------------------------------------------------------------
# Service (BentoML 1.2+ class-based style)
# ---------------------------------------------------------------------------


@bentoml.service(name="ai_tutor_gguf")
class Service:
    """AI Tutor for SPO (15.02.14) based on GGUF model via llama-cpp-python."""

    def __init__(self) -> None:
        gguf_files = glob.glob(os.path.join(MODEL_PATH, "*.gguf"))
        if not gguf_files:
            raise FileNotFoundError(
                f"No GGUF file found in {MODEL_PATH}. "
                f"Make sure the model is downloaded or uploaded via Git LFS."
            )
        model_file = gguf_files[0]
        logger.info("Loading GGUF model: %s", model_file)
        logger.info("Config: n_ctx=%d, n_gpu_layers=%d", N_CTX, N_GPU_LAYERS)

        from llama_cpp import Llama

        self.model = Llama(
            model_path=model_file,
            n_ctx=N_CTX,
            n_gpu_layers=N_GPU_LAYERS,
            verbose=False,
        )
        logger.info("Model loaded successfully")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        """Run generation and return the generated text."""
        response = self.model.create(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=50,
            repeat_penalty=1.1,
        )
        return response["choices"][0]["text"].strip()

    @staticmethod
    def _build_prompt(system_msg: str, user_msg: str) -> str:
        """Build Mistral-style prompt with system and user messages."""
        return f"<s>[INST] {system_msg}\n\n{user_msg} [/INST]"

    # ------------------------------------------------------------------
    # Endpoint 1: Health check
    # ------------------------------------------------------------------

    @bentoml.api(route="/health")
    def health(self) -> Dict[str, Any]:
        """Health check endpoint."""
        return {
            "status": "ok",
            "model_loaded": self.model is not None,
            "model_path": MODEL_PATH,
            "n_ctx": N_CTX,
            "n_gpu_layers": N_GPU_LAYERS,
        }

    # ------------------------------------------------------------------
    # Endpoint 2: Qubu Builder predict
    # ------------------------------------------------------------------

    @bentoml.api(route="/predict")
    def predict(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Predict endpoint for Qubu Builder (inputs.message -> result.answer)."""
        message = inputs.get("message", "")
        if not message or not message.strip():
            return {"result": {"answer": "Пожалуйста, введите сообщение."}}

        system_msg = (
            "Ты — интеллектуальный тьютор СПО "
            "(спец. 15.02.14). Отвечай подробно."
        )
        prompt = self._build_prompt(system_msg, message)
        answer = self._generate(prompt, max_tokens=MAX_NEW_TOKENS_CHAT, temperature=0.7)

        return {"result": {"answer": answer}}

    # ------------------------------------------------------------------
    # Endpoint 3: Generate Lecture Summary
    # ------------------------------------------------------------------

    @bentoml.api
    def generate_summary(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a structured lecture summary."""
        lecture_text = inputs.get("lecture_text", "")
        if not lecture_text or not lecture_text.strip():
            return {"success": False, "error": "lecture_text is empty"}

        system_msg = (
            "Ты — интеллектуальный тьютор для студентов "
            "СПО (спец. 15.02.14 «Оснащение средств "
            "автоматизации технологических процессов и производств»). "
            "Сделай краткий структурированный конспект лекции с "
            "ключевыми тезисами и терминами."
        )
        prompt = self._build_prompt(system_msg, f"Лекция:\n{lecture_text}\n\nКонспект:")

        logger.info("Generating summary (input: %d chars)", len(lecture_text))
        summary = self._generate(prompt, max_tokens=MAX_NEW_TOKENS_SUMMARY, temperature=0.7)
        logger.info("Summary generated (%d chars)", len(summary))

        return {
            "success": True,
            "summary": summary,
            "lecture_length_chars": len(lecture_text),
            "summary_length_chars": len(summary),
        }

    # ------------------------------------------------------------------
    # Endpoint 4: Generate Quiz
    # ------------------------------------------------------------------

    @bentoml.api
    def generate_quiz(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Generate quiz questions for self-check."""
        lecture_text = inputs.get("lecture_text", "")
        if not lecture_text or not lecture_text.strip():
            return {"success": False, "error": "lecture_text is empty"}

        num_questions = inputs.get("num_questions", 5)
        difficulty = inputs.get("difficulty", "medium")
        if difficulty not in ("easy", "medium", "hard"):
            difficulty = "medium"

        system_msg = (
            "Ты — преподаватель СПО (спец. 15.02.14). "
            f"Создай тест из {num_questions} вопросов "
            f"(сложность: {difficulty}). "
            "Каждый вопрос с 4 вариантами (A,B,C,D) "
            "и правильным ответом."
        )
        prompt = self._build_prompt(system_msg, f"Лекция:\n{lecture_text}\n\nТест:")

        logger.info("Generating quiz: %d questions, difficulty=%s", num_questions, difficulty)
        quiz = self._generate(prompt, max_tokens=MAX_NEW_TOKENS_QUIZ, temperature=0.8)
        logger.info("Quiz generated (%d chars)", len(quiz))

        return {
            "success": True,
            "quiz": quiz,
            "num_questions": num_questions,
            "difficulty": difficulty,
        }

    # ------------------------------------------------------------------
    # Endpoint 5: Chat
    # ------------------------------------------------------------------

    @bentoml.api
    def chat(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Conversational dialog with the AI tutor."""
        message = inputs.get("message", "")
        if not message or not message.strip():
            return {"success": False, "error": "message is empty"}

        history = inputs.get("history", [])

        system_msg = (
            "Ты — интеллектуальный тьютор СПО "
            "(спец. 15.02.14 «Оснащение средств "
            "автоматизации технологических процессов и производств»). "
            "Отвечай подробно, используя профессиональную терминологию."
        )

        # Build conversation from history
        prompt = f"<s>[INST] {system_msg} [/INST]"
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                prompt += f"<s>[INST] {content} [/INST]"
            else:
                prompt += f" {content}</s>"
        prompt += f"<s>[INST] {message} [/INST]"

        logger.info("Chat request: %s...", message[:80])
        answer = self._generate(prompt, max_tokens=MAX_NEW_TOKENS_CHAT, temperature=0.7)
        logger.info("Chat answer generated (%d chars)", len(answer))

        return {
            "success": True,
            "answer": answer,
            "history_length": len(history),
        }
