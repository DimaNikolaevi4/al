"""
BentoML inference service для Qwen2.5-7B-Instruct с 4-bit квантизацией.
Размещается в редакторе кода на Qubu.ai (вкладка «Инференс» → «Код»).

Модель загружается с Hugging Face при старте контейнера.
BitsAndBytesConfig обеспечивает 4-bit квантизацию (NF4) для экономии VRAM.
"""

import bentoml
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig


@bentoml.service(resources={"gpu": 1}, traffic={"timeout": 300})
class Service:
    def __init__(self):
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16
        )
        model_name = "Qwen/Qwen2.5-7B-Instruct"
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=bnb_config,
            device_map="auto",
            torch_dtype=torch.float16,
            trust_remote_code=True
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.system_prompt = (
            "Ты — AI-тьютор для студентов СПО по специальности 15.02.14. "
            "Отвечай на русском языке, подробно, дружелюбно."
        )

    @bentoml.api
    def predict(self, inp: dict) -> dict:
        message = inp.get("message", "").strip()
        if not message:
            return {"result": {"answer": "Задайте вопрос."}}
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": message}
        ]
        inputs = self.tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            return_tensors="pt"
        ).to(self.model.device)
        outputs = self.model.generate(
            inputs,
            max_new_tokens=512,
            temperature=0.7,
            do_sample=True,
            pad_token_id=self.tokenizer.pad_token_id
        )
        answer = self.tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)
        return {"result": {"answer": answer}}
