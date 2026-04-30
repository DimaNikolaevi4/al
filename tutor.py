import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

class IntelligentTutor:
    """
    Класс интеллектуального тьютора на базе LLM.
    Поддерживает загрузку базовой модели и дообученных адаптеров (LoRA).
    """
    def __init__(self, base_model_id, adapter_path=None):
        print(f"🚀 Запуск системы...")
        print(f"⚙️ Загрузка базовой модели: {base_model_id}...")
        
        # Загрузка токенизатора
        self.tokenizer = AutoTokenizer.from_pretrained(base_model_id)
        
        # Загрузка модели в формате float16 для экономии памяти
        self.model = AutoModelForCausalLM.from_pretrained(
            base_model_id, 
            torch_dtype=torch.float16, 
            device_map="auto",
            trust_remote_code=True
        )
        
        # Если указан путь, подгружаем дообученные адаптеры (LoRA)
        if adapter_path:
            print(f"🔌 Подключение адаптеров: {adapter_path}...")
            self.model = PeftModel.from_pretrained(self.model, adapter_path)
        
        print("✅ Тьютор инициализирован и готов к работе.")

    def generate_lecture_summary(self, lecture_text):
        """
        Генерирует краткий конспект лекции.
        """
        # Формирование промпта для модели
        prompt = f"Сделай краткий структурированный конспект лекции для студента техникума. Выдели основные тезисы.\n\nЛекция:\n{lecture_text}"
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs, 
                max_new_tokens=512,
                temperature=0.7,
                top_p=0.9
            )
        
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

# Точка входа для запуска на сервере техникума
if __name__ == "__main__":
    # Настройки путей (адаптируйте под вашу файловую систему)
    # Для прототипа Mistral:
    MODEL_PATH = "mistralai/Mistral-Small-24B-Instruct-2501" 
    # Для локального запуска скачанной модели:
    # MODEL_PATH = "/mnt/models/mistral-small-24b"
    
    # Путь к адаптерам (создадим после дообучения)
    ADAPTER_PATH = None # "./lora-tutors-adapter"
    
    # Инициализация
    tutor = IntelligentTutor(MODEL_PATH, ADAPTER_PATH)
    
    # Пример запроса
    test_lecture = "Тема: Основы промышленной автоматизации. Промышленная автоматизация — это применение систем управления..."
    print("\n--- Результат генерации ---")
    result = tutor.generate_lecture_summary(test_lecture)
    print(result)