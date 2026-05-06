<?php
// This file is part of Moodle - http://moodle.org/
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Moodle is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Moodle.  If not, see <http://www.gnu.org/licenses/>.

/**
 * Russian language strings for the AI Tutor plugin.
 *
 * @package    local_aitutor
 * @copyright  2026 AI Tutor Project
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

$string['pluginname'] = 'ИИ-Тьютор СПО';

// Settings page.
$string['settings_heading'] = 'Настройки ИИ-Тьютора';
$string['settings_api_url'] = 'URL сервера API';
$string['settings_api_url_desc'] = 'Базовый URL сервера ИИ-Тьютора (например, http://localhost:8000)';
$string['settings_api_key'] = 'API-ключ';
$string['settings_api_key_desc'] = 'Ключ авторизации для доступа к серверу API (необязательно)';
$string['settings_timeout'] = 'Таймаут запросов (секунды)';
$string['settings_timeout_desc'] = 'Максимальное время ожидания ответа от сервера API';
$string['settings_enable_summary'] = 'Включить генерацию конспекта';
$string['settings_enable_summary_desc'] = 'Разрешить пользователям создавать конспекты лекций с помощью ИИ';
$string['settings_enable_quiz'] = 'Включить генерацию тестов';
$string['settings_enable_quiz_desc'] = 'Разрешить пользователям генерировать тесты по материалам лекций';
$string['settings_enable_chat'] = 'Включить чат с ИИ';
$string['settings_enable_chat_desc'] = 'Разрешить пользователям задавать вопросы ИИ-тьютору';
$string['settings_max_lecture_length'] = 'Максимальная длина лекции (символов)';
$string['settings_max_lecture_length_desc'] = 'Максимальное количество символов в тексте лекции для отправки на сервер';
$string['settings_default_difficulty'] = 'Сложность тестов по умолчанию';
$string['settings_default_difficulty_desc'] = 'Уровень сложности по умолчанию для генерируемых тестов';
$string['settings_difficulty_easy'] = 'Лёгкий';
$string['settings_difficulty_medium'] = 'Средний';
$string['settings_difficulty_hard'] = 'Сложный';

// Button labels.
$string['btn_create_summary'] = 'Создать конспект';
$string['btn_generate_test'] = 'Сгенерировать тест';
$string['btn_ask_ai'] = 'Спросить ИИ';
$string['btn_send'] = 'Отправить';
$string['btn_cancel'] = 'Отмена';
$string['btn_close'] = 'Закрыть';
$string['btn_retry'] = 'Повторить';

// Modal / UI labels.
$string['modal_title_summary'] = 'Генерация конспекта';
$string['modal_title_quiz'] = 'Генерация теста';
$string['modal_title_chat'] = 'Чат с ИИ-тьютором';
$string['label_lecture_text'] = 'Текст лекции';
$string['label_lecture_text_help'] = 'Вставьте текст лекции для обработки ИИ-тьютором';
$string['label_chat_message'] = 'Ваш вопрос';
$string['label_chat_message_help'] = 'Задайте вопрос по теме лекции или учебному материалу';
$string['label_difficulty'] = 'Сложность';
$string['placeholder_lecture_text'] = 'Вставьте текст лекции здесь...';
$string['placeholder_chat_message'] = 'Введите ваш вопрос...';

// Status messages.
$string['status_pending'] = 'Ожидание обработки...';
$string['status_processing'] = 'ИИ обрабатывает ваш запрос...';
$string['status_complete'] = 'Готово!';
$string['status_failed'] = 'Произошла ошибка';
$string['status_timeout'] = 'Превышено время ожидания ответа сервера';

// Error messages.
$string['error_api_unreachable'] = 'Сервер ИИ-тьютора недоступен. Пожалуйста, обратитесь к администратору.';
$string['error_api_error'] = 'Ошибка сервера: {$a}';
$string['error_empty_text'] = 'Текст лекции не может быть пустым';
$string['error_text_too_long'] = 'Текст лекции превышает максимально допустимую длину ({$a} символов)';
$string['error_empty_message'] = 'Сообщение не может быть пустым';
$string['error_feature_disabled'] = 'Эта функция отключена администратором';
$string['error_no_permission'] = 'У вас нет доступа к этой функции';
$string['error_invalid_response'] = 'Получен некорректный ответ от сервера';
$string['error_task_not_found'] = 'Задача не найдена';

// Success messages.
$string['success_summary'] = 'Конспект успешно создан';
$string['success_quiz'] = 'Тест успешно сгенерирован';
$string['success_chat'] = 'Ответ получен';

// Privacy / capability labels.
$string['privacy:metadata'] = 'Плагин ИИ-Тьютор хранит историю запросов пользователей для обеспечения работоспособности сервиса.';
$string['capability_use'] = 'Использование ИИ-Тьютора';
$string['capability_manage'] = 'Управление настройками ИИ-Тьютора';
