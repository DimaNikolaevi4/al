"""
BentoML inference service for AI Tutor on Qubu platform (GGUF variant).

Uses llama-cpp-python with pre-built CUDA 12.1 wheel for inference.
No compilation needed — fast deployment within Qubu's 50-min timeout.

Model: Mistral Small 24B-Instruct-2501 Q4_K_M (~15 GB)
GPU: RTX 4000 Ada (20 GB VRAM)

Provides endpoints:
  - /health           — health check
  - /generate_summary — structured lecture summary
  - /generate_quiz    — self-check quiz questions
  - /chat             — dialog with the tutor

Author: Komanda II SIT (Bardakov D.N., Myshanskaya N.G.)
License: Apache 2.0
"""

import os
import glob
import logging
from typing import Any, Dict, List, Optional

from llama_cpp import Llama
from bentoml import Service

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

MODEL_PATH = os.environ.get("MODEL_PATH", "/workspace/model")
N_CTX = int(os.environ.get("N_CTX", "2048"))
N_GPU_LAYERS = int(os.environ.get("N_GPU_LAYERS", "-1"))  # -1 = all layers on GPU
MAX_NEW_TOKENS_SUMMARY = int(os.environ.get("MAX_NEW_TOKENS_SUMMARY", "512"))
MAX_NEW_TOKENS_QUIZ = int(os.environ.get("MAX_NEW_TOKENS_QUIZ", "1024"))
MAX_NEW_TOKENS_CHAT = int(os.environ.get("MAX_NEW_TOKENS_CHAT", "256"))

# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

service = Service("ai_tutor_gguf")


@service.on_startup
def load_model():
    """Load GGUF model on startup. Finds *.gguf in MODEL_PATH directory."""
    gguf_files = glob.glob(os.path.join(MODEL_PATH, "*.gguf"))
    if not gguf_files:
        raise FileNotFoundError(
            f"No GGUF file found in {MODEL_PATH}. "
            f"Make sure the model is downloaded or uploaded via Git LFS."
        )

    model_file = gguf_files[0]
    logger.info("Loading GGUF model: %s", model_file)
    logger.info("Config: n_ctx=%d, n_gpu_layers=%d", N_CTX, N_GPU_LAYERS)

    service.model = Llama(
        model_path=model_file,
        n_ctx=N_CTX,
        n_gpu_layers=N_GPU_LAYERS,
        verbose=False,
    )

    param_count = service.model.n_ctx
    logger.info("Model loaded successfully (n_ctx=%d)", param_count)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_prompt(system_msg: str, user_msg: str) -> str:
    """Build Mistral-style prompt with system and user messages."""
    return f"<s>[INST] {system_msg}\n\n{user_msg} [/INST]"


def _generate(prompt: str, max_tokens: int = 512, temperature: float = 0.7,
              top_p: float = 0.9) -> str:
    """Run generation and return the generated text."""
    response = service.model.create(
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        top_k=50,
        repeat_penalty=1.1,
    )
    return response["choices"][0]["text"].strip()


# ---------------------------------------------------------------------------
# Endpoint 1: Health check
# ---------------------------------------------------------------------------

@service.api(route="/health")
def health() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "ok",
        "model_loaded": service.model is not None,
        "model_path": MODEL_PATH,
        "n_ctx": N_CTX,
        "n_gpu_layers": N_GPU_LAYERS,
    }


# ---------------------------------------------------------------------------
# Endpoint 2: Generate Lecture Summary
# ---------------------------------------------------------------------------

@service.api
def generate_summary(inputs: Dict[str, Any]) -> Dict[str, Any]:
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

    system_msg = (
        "Ты — интеллектуальный тьютор для студентов среднего профессионального "
        "образования (специальность 15.02.14 «Оснащение средств автоматизации "
        "технологических процессов и производств»). "
        "Сделай краткий структурированный конспект лекции. "
        "Выдели основные тезисы, ключевые термины и определения. "
        "Используй маркированные списки."
    )

    prompt = _build_prompt(system_msg, f"Лекция:\n{lecture_text}\n\nКонспект:")

    logger.info("Generating summary (input: %d chars)", len(lecture_text))
    summary = _generate(prompt, max_new_tokens=max_tokens, temperature=temp)
    logger.info("Summary generated (%d chars)", len(summary))

    return {
        "success": True,
        "summary": summary,
        "lecture_length_chars": len(lecture_text),
        "summary_length_chars": len(summary),
    }


# ---------------------------------------------------------------------------
# Endpoint 3: Generate Quiz
# ---------------------------------------------------------------------------

@service.api
def generate_quiz(inputs: Dict[str, Any]) -> Dict[str, Any]:
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

    system_msg = (
        "Ты — преподаватель среднего профессионального образования "
        "(специальность 15.02.14 «Оснащение средств автоматизации "
        "технологических процессов и производств»). "
        "Создай тест из {n} вопросов (сложность: {d}). "
        "Каждый вопрос должен иметь 4 варианта ответа (A, B, C, D) "
        "и указание правильного ответа. Формат:\n"
        "Вопрос N: <текст>\n"
        "A) <вариант>\nB) <вариант>\nC) <вариант>\nD) <вариант>\n"
        "Ответ: <буква>"
    ).format(n=num_questions, d=difficulty)

    prompt = _build_prompt(system_msg, f"Лекция:\n{lecture_text}\n\nТест:")

    logger.info("Generating quiz: %d questions, difficulty=%s", num_questions, difficulty)
    quiz = _generate(prompt, max_new_tokens=MAX_NEW_TOKENS_QUIZ, temperature=0.8)
    logger.info("Quiz generated (%d chars)", len(quiz))

    return {
        "success": True,
        "quiz": quiz,
        "num_questions": num_questions,
        "difficulty": difficulty,
    }


# ---------------------------------------------------------------------------
# Endpoint 4: Chat
# ---------------------------------------------------------------------------

@service.api
def chat(inputs: Dict[str, Any]) -> Dict[str, Any]:
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

    history = inputs.get("history", [])

    system_msg = (
        "Ты — интеллектуальный тьютор для студентов среднего профессионального "
        "образования (специальность 15.02.14 «Оснащение средств автоматизации "
        "технологических процессов и производств»). "
        "Отвечай на вопросы студентов понятно и подробно, "
        "используя профессиональную терминологию."
    )

    # Build conversation prompt from history
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
    answer = _generate(prompt, max_new_tokens=MAX_NEW_TOKENS_CHAT, temperature=0.7)
    logger.info("Chat answer generated (%d chars)", len(answer))

    return {
        "success": True,
        "answer": answer,
        "history_length": len(history),
    }
