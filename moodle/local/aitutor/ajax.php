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
 * AJAX endpoint for the AI Tutor plugin.
 *
 * Handles incoming requests from the block UI, proxies them to the
 * FastAPI backend, and returns JSON responses.
 *
 * @package    local_aitutor
 * @copyright  2026 AI Tutor Project
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

define('NOAJAX', false);
define('AJAX_SCRIPT', true);
define('REQUIRE_LOGIN', false); // We check login manually below.

require_once(__DIR__ . '/../../config.php');
require_once($CFG->libdir . '/filelib.php');

// Require login and validate session.
require_login(null, false, null, false, true);

$action = required_param('action', PARAM_ALPHAEXT);
$sesskey = required_param('sesskey', PARAM_RAW);

if (!confirm_sesskey($sesskey)) {
    header('HTTP/1.1 403 Forbidden');
    echo json_encode(['success' => false, 'error' => 'Invalid session key']);
    exit;
}

$courseid = optional_param('courseid', 0, PARAM_INT);
$context = $courseid ? \context_course::instance($courseid) : \context_system::instance();

if (!has_capability('local/aitutor:use', $context)) {
    header('HTTP/1.1 403 Forbidden');
    echo json_encode(['success' => false, 'error' => get_string('error_no_permission', 'local_aitutor')]);
    exit;
}

// Header for JSON responses.
header('Content-Type: application/json; charset=utf-8');

$service = new \local_aitutor\ai_tutor_service();

switch ($action) {
    case 'summary':
    case 'quiz':
        handle_async_request($action, $service, $courseid);
        break;

    case 'chat':
        handle_chat_request($service, $courseid);
        break;

    case 'status':
        handle_status_request($service);
        break;

    default:
        echo json_encode(['success' => false, 'error' => 'Unknown action']);
        break;
}
exit;

// -----------------------------------------------------------------------
// Action handlers.
// -----------------------------------------------------------------------

/**
 * Handle summary or quiz generation (async).
 *
 * @param string $action  'summary' or 'quiz'.
 * @param \local_aitutor\ai_tutor_service $service
 * @param int $courseid
 */
function handle_async_request(string $action, \local_aitutor\ai_tutor_service $service, int $courseid): void {
    global $USER, $DB;

    $text = required_param('text', PARAM_TEXT);
    $text = trim($text);

    if (empty($text)) {
        echo json_encode(['success' => false, 'error' => get_string('error_empty_text', 'local_aitutor')]);
        return;
    }

    // Check feature is enabled.
    $configkey = "enable_{$action}";
    if (!(bool) get_config('local_aitutor', $configkey)) {
        echo json_encode(['success' => false, 'error' => get_string('error_feature_disabled', 'local_aitutor')]);
        return;
    }

    // Check text length.
    $maxlength = (int) get_config('local_aitutor', 'max_lecture_length') ?: 50000;
    if (mb_strlen($text) > $maxlength) {
        echo json_encode([
            'success' => false,
            'error'   => get_string('error_text_too_long', 'local_aitutor', $maxlength),
        ]);
        return;
    }

    // Build params.
    $params = [];
    if ($action === 'quiz') {
        $difficulty = optional_param('difficulty', '', PARAM_ALPHA);
        if (!empty($difficulty)) {
            $params['difficulty'] = $difficulty;
        }
    }

    // Call API.
    if ($action === 'summary') {
        $result = $service->generate_summary($text, $params);
    } else {
        $result = $service->generate_quiz($text, $params);
    }

    if ($result->success && $result->data) {
        $taskid = is_object($result->data) ? ($result->data->task_id ?? null) :
            (is_array($result->data) ? ($result->data['task_id'] ?? null) : null);

        // Store request in database.
        $record = new \stdClass();
        $record->userid        = $USER->id;
        $record->courseid      = $courseid;
        $record->request_type  = $action;
        $record->input_text    = $text;
        $record->task_id       = $taskid ?: '';
        $record->status        = 'pending';
        $record->result_text   = null;
        $record->error_message = null;
        $record->timecreated   = time();
        $record->timemodified  = time();
        $DB->insert_record('local_aitutor_requests', $record);

        echo json_encode([
            'success' => true,
            'task_id' => $taskid,
        ]);
    } else {
        echo json_encode([
            'success' => false,
            'error'   => $result->error,
        ]);
    }
}

/**
 * Handle chat request (async).
 *
 * @param \local_aitutor\ai_tutor_service $service
 * @param int $courseid
 */
function handle_chat_request(\local_aitutor\ai_tutor_service $service, int $courseid): void {
    global $USER, $DB;

    $text = required_param('text', PARAM_TEXT);
    $text = trim($text);

    if (empty($text)) {
        echo json_encode(['success' => false, 'error' => get_string('error_empty_message', 'local_aitutor')]);
        return;
    }

    if (!(bool) get_config('local_aitutor', 'enable_chat')) {
        echo json_encode(['success' => false, 'error' => get_string('error_feature_disabled', 'local_aitutor')]);
        return;
    }

    $result = $service->chat($text);

    if ($result->success && $result->data) {
        $taskid = is_object($result->data) ? ($result->data->task_id ?? null) :
            (is_array($result->data) ? ($result->data['task_id'] ?? null) : null);

        $record = new \stdClass();
        $record->userid        = $USER->id;
        $record->courseid      = $courseid;
        $record->request_type  = 'chat';
        $record->input_text    = $text;
        $record->task_id       = $taskid ?: '';
        $record->status        = 'pending';
        $record->result_text   = null;
        $record->error_message = null;
        $record->timecreated   = time();
        $record->timemodified  = time();
        $DB->insert_record('local_aitutor_requests', $record);

        echo json_encode([
            'success' => true,
            'task_id' => $taskid,
        ]);
    } else {
        echo json_encode([
            'success' => false,
            'error'   => $result->error,
        ]);
    }
}

/**
 * Handle task status polling.
 *
 * @param \local_aitutor\ai_tutor_service $service
 */
function handle_status_request(\local_aitutor\ai_tutor_service $service): void {
    global $USER, $DB;

    $taskid = required_param('task_id', PARAM_ALPHANUM);

    // Look up the request record.
    $record = $DB->get_record('local_aitutor_requests', ['task_id' => $taskid, 'userid' => $USER->id]);

    if (!$record) {
        echo json_encode(['success' => false, 'error' => get_string('error_task_not_found', 'local_aitutor')]);
        return;
    }

    // If already complete, return cached result.
    if ($record->status === 'complete' || $record->status === 'failed') {
        echo json_encode([
            'success' => true,
            'result'  => [
                'status'        => $record->status,
                'result_text'   => $record->result_text,
                'error_message' => $record->error_message,
            ],
        ]);
        return;
    }

    // Poll the API.
    $result = $service->get_task_status($taskid);

    if ($result->success && $result->data) {
        $apidata  = $result->data;
        $apistatus = is_object($apidata) ? ($apidata->status ?? null) :
            (is_array($apidata) ? ($apidata['status'] ?? null) : null);

        $update = new \stdClass();
        $update->id = $record->id;

        if ($apistatus === 'completed' || $apistatus === 'complete') {
            $update->status      = 'complete';
            $update->result_text = is_object($apidata) ? json_encode($apidata) : json_encode($apidata);
            $update->timemodified = time();
        } else if ($apistatus === 'failed') {
            $update->status        = 'failed';
            $error = is_object($apidata) ? ($apidata->error ?? null) :
                (is_array($apidata) ? ($apidata['error'] ?? null) : null);
            $update->error_message = $error;
            $update->timemodified  = time();
        } else {
            $update->status       = 'processing';
            $update->timemodified = time();
        }

        $DB->update_record('local_aitutor_requests', $update);

        echo json_encode([
            'success' => true,
            'result'  => [
                'status'        => $update->status,
                'result_text'   => $update->result_text,
                'error_message' => $update->error_message,
            ],
        ]);
    } else {
        echo json_encode([
            'success' => false,
            'error'   => $result->error,
        ]);
    }
}
