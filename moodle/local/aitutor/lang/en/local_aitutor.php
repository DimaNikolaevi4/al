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
 * English language strings for the AI Tutor plugin.
 *
 * @package    local_aitutor
 * @copyright  2026 AI Tutor Project
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

$string['pluginname'] = 'AI Tutor SPO';

// Settings page.
$string['settings_heading'] = 'AI Tutor Settings';
$string['settings_api_url'] = 'API Server URL';
$string['settings_api_url_desc'] = 'Base URL of the AI Tutor server (e.g., http://localhost:8000)';
$string['settings_api_key'] = 'API Key';
$string['settings_api_key_desc'] = 'Authorization key for accessing the API server (optional)';
$string['settings_timeout'] = 'Request Timeout (seconds)';
$string['settings_timeout_desc'] = 'Maximum time to wait for an API server response';
$string['settings_enable_summary'] = 'Enable Summary Generation';
$string['settings_enable_summary_desc'] = 'Allow users to generate lecture summaries with AI';
$string['settings_enable_quiz'] = 'Enable Quiz Generation';
$string['settings_enable_quiz_desc'] = 'Allow users to generate quizzes from lecture materials';
$string['settings_enable_chat'] = 'Enable AI Chat';
$string['settings_enable_chat_desc'] = 'Allow users to ask questions to the AI tutor';
$string['settings_max_lecture_length'] = 'Maximum Lecture Length (characters)';
$string['settings_max_lecture_length_desc'] = 'Maximum number of characters in lecture text sent to the server';
$string['settings_default_difficulty'] = 'Default Quiz Difficulty';
$string['settings_default_difficulty_desc'] = 'Default difficulty level for generated quizzes';
$string['settings_difficulty_easy'] = 'Easy';
$string['settings_difficulty_medium'] = 'Medium';
$string['settings_difficulty_hard'] = 'Hard';

// Button labels.
$string['btn_create_summary'] = 'Create Summary';
$string['btn_generate_test'] = 'Generate Test';
$string['btn_ask_ai'] = 'Ask AI';
$string['btn_send'] = 'Send';
$string['btn_cancel'] = 'Cancel';
$string['btn_close'] = 'Close';
$string['btn_retry'] = 'Retry';

// Modal / UI labels.
$string['modal_title_summary'] = 'Summary Generation';
$string['modal_title_quiz'] = 'Quiz Generation';
$string['modal_title_chat'] = 'Chat with AI Tutor';
$string['label_lecture_text'] = 'Lecture Text';
$string['label_lecture_text_help'] = 'Paste the lecture text for AI tutor processing';
$string['label_chat_message'] = 'Your Question';
$string['label_chat_message_help'] = 'Ask a question about the lecture topic or study material';
$string['label_difficulty'] = 'Difficulty';
$string['placeholder_lecture_text'] = 'Paste the lecture text here...';
$string['placeholder_chat_message'] = 'Enter your question...';

// Status messages.
$string['status_pending'] = 'Waiting for processing...';
$string['status_processing'] = 'AI is processing your request...';
$string['status_complete'] = 'Done!';
$string['status_failed'] = 'An error occurred';
$string['status_timeout'] = 'Server response timeout exceeded';

// Error messages.
$string['error_api_unreachable'] = 'AI Tutor server is unreachable. Please contact your administrator.';
$string['error_api_error'] = 'Server error: {$a}';
$string['error_empty_text'] = 'Lecture text cannot be empty';
$string['error_text_too_long'] = 'Lecture text exceeds the maximum allowed length ({$a} characters)';
$string['error_empty_message'] = 'Message cannot be empty';
$string['error_feature_disabled'] = 'This feature has been disabled by the administrator';
$string['error_no_permission'] = 'You do not have permission to access this feature';
$string['error_invalid_response'] = 'Invalid response received from server';
$string['error_task_not_found'] = 'Task not found';

// Success messages.
$string['success_summary'] = 'Summary created successfully';
$string['success_quiz'] = 'Quiz generated successfully';
$string['success_chat'] = 'Response received';

// Privacy / capability labels.
$string['privacy:metadata'] = 'The AI Tutor plugin stores user request history for service functionality.';
$string['capability_use'] = 'Use AI Tutor';
$string['capability_manage'] = 'Manage AI Tutor Settings';
