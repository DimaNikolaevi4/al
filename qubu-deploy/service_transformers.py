"""
BentoML inference service for AI Tutor on Qubu platform.

Provides three endpoints:
  - /generate_summary  — structured lecture summary
  - /generate_quiz     — self-check quiz questions
  - /chat              — dialog with the tutor

Author: Komanda II SIT (Bardakov D.N., Myshanskaya N.G.)
License: Apache 2.0
"""

import os
import logging
from typing import Any, Dict, List, Optional

import bentoml
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

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
# Config
# ---------------------------------------------------------------------------

MODEL_PATH = os.getenv("MODEL_PATH", "/workspace/model")
ADAPTER_PATH = os.getenv("ADAPTER_PATH", None)
MAX_NEW_TOKENS_SUMMARY = int(os.getenv("MAX_NEW_TOKENS_SUMMARY", "512"))
MAX_NEW_TOKENS_QUIZ = int(os.getenv("MAX_NEW_TOKENS_QUIZ", "1024"))
MAX_NEW_TOKENS_CHAT = int(os.getenv("MAX_NEW_TOKENS_CHAT", "256"))


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

@bentoml.service(name="ai_tutor_inference")
class Service:
    """AI Tutor inference service for vocational education (SPO).

    Loads Mistral Small 24B-Instruct with optional QLoRA adapter and
    provides three endpoints: summary generation, quiz generation,
    and conversational chat.
    """

    def __init__(self) -> None:
        logger.info("Loading AI Tutor model from: %s", MODEL_PATH)
        if ADAPTER_PATH:
            logger.info("LoRA adapter path: %s", ADAPTER_PATH)

        # --- Tokenizer ---
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # --- Model (4-bit quantization for GPU efficiency) ---
        from transformers import BitsAndBytesConfig

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )

        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            torch_dtype=torch.float16,
        )

        # --- Optional LoRA adapter ---
        if ADAPTER_PATH and os.path.exists(ADAPTER_PATH):
            from peft import PeftModel
            self.model = PeftModel.from_pretrained(self.model, ADAPTER_PATH)
            logger.info("LoRA adapter loaded successfully")
            self.model.eval()
        else:
            self.model.eval()

        param_count = sum(p.numel() for p in self.model.parameters())
        logger.info("Model loaded successfully (%.2fB parameters)", param_count / 1e9)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate(self, prompt: str, max_new_tokens: int = 512, temperature: float = 0.7) -> str:
        """Run generation and return decoded text (assistant part only)."""
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=8192,
        ).to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=0.9,
                top_k=50,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        # Extract only the new tokens (assistant response)
        input_len = inputs["input_ids"].shape[1]
        new_tokens = outputs[0][input_len:]
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    def _build_chat_prompt(self, user_message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """Build chat prompt using Mistral chat template."""
        messages = (history or []) + [{"role": "user", "content": user_message}]
        return self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

    # ------------------------------------------------------------------
    # Endpoint 1: Generate Lecture Summary
    # ------------------------------------------------------------------

    @bentoml.api
    def generate_summary(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a structured lecture summary.

        Args (in inputs):
            lecture_text (str): Full text of the lecture.
            max_new_tokens (int, optional): Max tokens to generate. Default 512.
            temperature (float, optional): Sampling temperature. Default 0.7.

        Returns:
            dict with 'summary' key.
        """
        lecture_text = inputs.get("lecture_text", "")
        if not lecture_text or not lecture_text.strip():
            return {"success": False, "error": "lecture_text is empty"}

        max_tokens = inputs.get("max_new_tokens", MAX_NEW_TOKENS_SUMMARY)
        temp = inputs.get("temperature", 0.7)

        prompt = (
            "Ты — интеллектуальный тьютор для студентов среднего профессионального "
            "образования (специальность 15.02.14). Сделай краткий структурированный "
            "конспект лекции. Выдели основные тезисы, ключевые термины и определения. "
            "Используй маркированные списки.\n\n"
            f"Лекция:\n{lecture_text}\n\n"
            "Конспект:"
        )

        logger.info("Generating summary (input: %d chars)", len(lecture_text))
        summary = self._generate(prompt, max_new_tokens=max_tokens, temperature=temp)
        logger.info("Summary generated (%d chars)", len(summary))

        return {
            "success": True,
            "summary": summary,
            "lecture_length_chars": len(lecture_text),
            "summary_length_chars": len(summary),
        }

    # ------------------------------------------------------------------
    # Endpoint 2: Generate Quiz
    # ------------------------------------------------------------------

    @bentoml.api
    def generate_quiz(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Generate quiz questions for self-check.

        Args (in inputs):
            lecture_text (str): Full text of the lecture.
            num_questions (int, optional): Number of questions. Default 5.
            difficulty (str, optional): 'easy', 'medium', or 'hard'. Default 'medium'.

        Returns:
            dict with 'quiz' key containing generated questions.
        """
        lecture_text = inputs.get("lecture_text", "")
        if not lecture_text or not lecture_text.strip():
            return {"success": False, "error": "lecture_text is empty"}

        num_questions = inputs.get("num_questions", 5)
        difficulty = inputs.get("difficulty", "medium")

        if difficulty not in ("easy", "medium", "hard"):
            difficulty = "medium"

        prompt = (
            "Ты — преподаватель среднего профессионального образования "
            "(специальность 15.02.14 «Оснащение средств автоматизации»). "
            f"Создай тест из {num_questions} вопросов (сложность: {difficulty}) "
            "по следующей лекции. Каждый вопрос должен иметь 4 варианта ответа "
            "(A, B, C, D) и указание правильного ответа.\n\n"
            f"Лекция:\n{lecture_text}\n\n"
            "Тест:"
        )

        logger.info("Generating quiz: %d questions, difficulty=%s", num_questions, difficulty)
        quiz = self._generate(prompt, max_new_tokens=MAX_NEW_TOKENS_QUIZ, temperature=0.8)
        logger.info("Quiz generated (%d chars)", len(quiz))

        return {
            "success": True,
            "quiz": quiz,
            "num_questions": num_questions,
            "difficulty": difficulty,
        }

    # ------------------------------------------------------------------
    # Endpoint 3: Chat
    # ------------------------------------------------------------------

    @bentoml.api
    def chat(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Conversational dialog with the AI tutor.

        Args (in inputs):
            message (str): User message/question.
            history (list of dict, optional): Previous messages
                [{"role": "user/assistant", "content": "..."}].

        Returns:
            dict with 'answer' key.
        """
        message = inputs.get("message", "")
        if not message or not message.strip():
            return {"success": False, "error": "message is empty"}

        history = inputs.get("history", None)

        prompt = self._build_chat_prompt(message, history)

        logger.info("Chat request: %s...", message[:80])
        answer = self._generate(prompt, max_new_tokens=MAX_NEW_TOKENS_CHAT, temperature=0.7)
        logger.info("Chat answer generated (%d chars)", len(answer))

        return {
            "success": True,
            "answer": answer,
            "history_length": len(history) if history else 0,
        }

    # ------------------------------------------------------------------
    # Endpoint 4: Health check
    # ------------------------------------------------------------------

    @bentoml.api(route="/health")
    def health(self) -> Dict[str, Any]:
        """Health check endpoint."""
        return {"status": "ok", "model_loaded": self.model is not None}
