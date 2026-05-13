# Лог деплоя на Qubu.ai

---

## ✅ Успешный пуш кода: 2026-05-13

### Контекст
- Конкурс: Gravitation 2026, Команда СИТ
- Модель: Qwen2.5-7B-Instruct-Q5_K_M (~5.44 ГБ)
- Платформа: Qubu.ai
- Специальность СПО: 15.02.14 «Оснащение средств автоматизации»

### Рабочий Git URL (slug-based, с токеном)
```
https://REDACTED_USERNAME:REDACTED_TOKEN@git.qubu.ai/REDACTED_USERNAME/ml_model-intellektualniy-tyutor-na-osnove-otkrytykh-bolshikh-yazykovykh-modelei-dlya-spo.git
```

### Ключевые файлы
- service.py: 18895 байт, 415 строк
- requirements.txt: 1027 байт, 20 строк — pre-built wheel llama-cpp-python CUDA 12.1
- bentofile.yaml: 842 байт, 23 строки — include *.py, *.yaml, *.txt, *.sh

### Что сработало
1. ✅ Git через slug-based URL + токен в URL (UUID-based URL не работает — редирект на /maintenance)
2. ✅ Pre-built wheel llama-cpp-python v0.2.91 (экономия 20-30 мин компиляции на сервере)
3. ✅ Загрузка модели с resume через requests + HTTP Range (chunk_size=8192, max_attempts=3)
4. ✅ Параметры: n_gpu_layers=-1 (все слои на GPU), n_ctx=2048, temperature=0.3
5. ✅ Base image nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04 в bentofile.yaml
6. ✅ System prompt по ФГОС СПО 15.02.14 (ПЛК, КИПиА, SCADA, ПИД-регулирование)

### Что НЕ сработало (избегать в будущем)
- ❌ UUID-based Git URL (`/c9827a6f-...git`) → редирект на /maintenance
- ❌ wget без resume → таймаут при загрузке модели >5 ГБ
- ❌ Модель >6 ГБ → риск не уложиться в 50 мин таймаут сборки Qubu
- ❌ URL-embedded credentials в формате `user:token@` для UUID-based путей
- ❌ Bearer token API для записи deployment-config → HTTP 401 (read-only)

### Архитектура решения
- **Инференс**: BentoML 1.2+ с `@bentoml.service(gpu=1)`, `@bentoml.api`
- **Модель**: llama-cpp-python с GGUF Q5_K_M квантизацией
- **API endpoints**: `/health` (GET), `/predict` (POST, формат ChatML)
- **Формат ответа**: `{"result": {"answer": "..."}}`
- **Plan B** (закомментирован в service.py): Qwen2.5-1.5B-Instruct-Q6_K (~1 ГБ)

### Каналы обновления кода на Qubu (исследовано)
| Канал | Статус | Для деплоя? |
|-------|--------|-------------|
| Git (slug + token) | ✅ Работает | Основной метод |
| Веб-редактор (CM6) | ✅ Работает | Запасной (PUT/POST API) |
| API (Bearer token) | ⚠️ Read-only | Нет |

### Веб-редактор API (запасной канал)
- **Save (без рестарта)**: `PUT /api/models/{id}/inference/deployment-config` — plain text
- **Update + Restart**: `POST /api/models/{id}/inference/proxy/__admin/service/update` — base64
- **Deploy**: `POST /api/models/{id}/inference/deploy`

### Следующий шаг после пуша
1. Пользователь вручную нажимает «Обновить код и перезапустить инференс» на странице редактирования модели
2. Агент мониторит статус деплоя через API (каждые 3 мин)
3. После RUNNING — проверка /health и /predict

### Коммит на Qubu
- Хэш: 6076478
- Дата: 2026-05-13
- Сообщение: «feat: Qwen2.5-7B Q5_K_M с надёжной загрузкой и промптом СПО 15.02.14 [ТЗ 2.0]»
- Изменения: 3 файла, +458 строк, -9 строк
