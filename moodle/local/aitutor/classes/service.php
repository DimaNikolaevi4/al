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

namespace local_aitutor;

/**
 * AI Tutor API service class.
 *
 * Handles all communication between Moodle and the FastAPI backend.
 * Uses Moodle's curl class for HTTP requests.
 *
 * @package    local_aitutor
 * @copyright  2026 AI Tutor Project
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class ai_tutor_service {

    /** @var string Base URL for the API server. */
    private string $apiurl;

    /** @var string|null API key for authentication. */
    private ?string $apikey;

    /** @var int Request timeout in seconds. */
    private int $timeout;

    /** @var bool Debug mode flag. */
    private bool $debug;

    /**
     * Constructor — reads plugin settings from Moodle config.
     */
    public function __construct() {
        $this->apiurl  = get_config('local_aitutor', 'api_url') ?: 'http://localhost:8000';
        $this->apikey  = get_config('local_aitutor', 'api_key') ?: null;
        $this->timeout = (int) get_config('local_aitutor', 'timeout') ?: 120;
        $this->debug   = debugging('', DEBUG_DEVELOPER);
    }

    /**
     * Send an async request to generate a summary for the given lecture text.
     *
     * @param string $lecture_text The full lecture text.
     * @param array  $params       Optional extra parameters (e.g. format, detail_level).
     * @return \stdClass Result object with properties: success, data, error.
     */
    public function generate_summary(string $lecture_text, array $params = []): \stdClass {
        $payload = array_merge([
            'text' => $lecture_text,
        ], $params);

        return $this->post('/api/v1/async/generate-summary', $payload);
    }

    /**
     * Send an async request to generate a quiz for the given lecture text.
     *
     * @param string $lecture_text The full lecture text.
     * @param array  $params       Optional extra parameters (e.g. difficulty, num_questions).
     * @return \stdClass Result object with properties: success, data, error.
     */
    public function generate_quiz(string $lecture_text, array $params = []): \stdClass {
        // Apply default difficulty from plugin settings if not specified.
        if (!isset($params['difficulty'])) {
            $params['difficulty'] = get_config('local_aitutor', 'default_difficulty') ?: 'medium';
        }

        $payload = array_merge([
            'text' => $lecture_text,
        ], $params);

        return $this->post('/api/v1/async/generate-test', $payload);
    }

    /**
     * Send an async chat message to the AI tutor.
     *
     * @param string $message User message.
     * @param array  $history Conversation history [{role, content}, ...].
     * @return \stdClass Result object with properties: success, data, error.
     */
    public function chat(string $message, array $history = []): \stdClass {
        $messages = $history;
        $messages[] = ['role' => 'user', 'content' => $message];

        $payload = [
            'messages' => $messages,
        ];

        return $this->post('/api/v1/async/chat', $payload);
    }

    /**
     * Poll the status of an async task by its task ID.
     *
     * @param string $task_id The unique task identifier returned by the async endpoint.
     * @return \stdClass Result object with properties: success, data, error.
     */
    public function get_task_status(string $task_id): \stdClass {
        return $this->get("/api/v1/async/status/{$task_id}");
    }

    /**
     * Check if the API server is reachable and healthy.
     *
     * @return \stdClass Result object with success=true if server is healthy.
     */
    public function check_health(): \stdClass {
        return $this->get('/api/v1/health');
    }

    // -----------------------------------------------------------------------
    // Internal helpers.
    // -----------------------------------------------------------------------

    /**
     * Perform a GET request to the API server.
     *
     * @param string $endpoint API endpoint path (relative to base URL).
     * @return \stdClass
     */
    private function get(string $endpoint): \stdClass {
        $url = rtrim($this->apiurl, '/') . $endpoint;

        $curl = new \curl();
        $curl->setHeader('Accept: application/json');

        $this->apply_auth_header($curl);

        try {
            $response = $curl->get($url);
            $httpcode = $curl->get_info()['http_code'] ?? 0;
        } catch (\Exception $e) {
            return $this->error_result(
                get_string('error_api_unreachable', 'local_aitutor'),
                $e->getMessage()
            );
        }

        return $this->parse_response($response, $httpcode);
    }

    /**
     * Perform a POST request to the API server.
     *
     * @param string $endpoint API endpoint path.
     * @param array  $payload  Request body (will be JSON-encoded).
     * @return \stdClass
     */
    private function post(string $endpoint, array $payload): \stdClass {
        $url = rtrim($this->apiurl, '/') . $endpoint;
        $json = json_encode($payload, JSON_UNESCAPED_UNICODE);

        if ($json === false) {
            return $this->error_result(
                get_string('error_invalid_response', 'local_aitutor'),
                'JSON encode failed for payload.'
            );
        }

        $curl = new \curl();
        $curl->setHeader('Content-Type: application/json');
        $curl->setHeader('Accept: application/json');

        $this->apply_auth_header($curl);

        try {
            $response = $curl->post($url, $json);
            $httpcode = $curl->get_info()['http_code'] ?? 0;
        } catch (\Exception $e) {
            return $this->error_result(
                get_string('error_api_unreachable', 'local_aitutor'),
                $e->getMessage()
            );
        }

        return $this->parse_response($response, $httpcode);
    }

    /**
     * Apply Authorization header if an API key is configured.
     *
     * @param \curl $curl
     */
    private function apply_auth_header(\curl $curl): void {
        if (!empty($this->apikey)) {
            $curl->setHeader('Authorization: Bearer ' . $this->apikey);
        }
    }

    /**
     * Parse the raw response body and return a standardised result object.
     *
     * Expected API response format:
     *   {"success": bool, "data": {...}, "error": str|null, "meta": {...}}
     *
     * @param string $raw       Raw response body.
     * @param int    $httpcode  HTTP status code.
     * @return \stdClass
     */
    private function parse_response(string $raw, int $httpcode): \stdClass {
        $this->log_debug("API response (HTTP {$httpcode}): {$raw}");

        $decoded = json_decode($raw, true);

        if (json_last_error() !== JSON_ERROR_NONE) {
            return $this->error_result(
                get_string('error_invalid_response', 'local_aitutor'),
                'JSON decode error: ' . json_last_error_msg()
            );
        }

        // API signals failure at the HTTP level.
        if ($httpcode >= 500) {
            $apidetail = $decoded['detail'] ?? ($decoded['error'] ?? 'Unknown server error');
            return $this->error_result(
                get_string('error_api_error', 'local_aitutor', $apidetail),
                $apidetail
            );
        }

        if ($httpcode >= 400) {
            $apidetail = $decoded['detail'] ?? ($decoded['error'] ?? "HTTP {$httpcode}");
            return $this->error_result(
                get_string('error_api_error', 'local_aitutor', $apidetail),
                $apidetail
            );
        }

        // API-level success flag.
        $success = (bool) ($decoded['success'] ?? true);
        $data    = $decoded['data']    ?? null;
        $error   = $decoded['error']   ?? null;
        $meta    = $decoded['meta']    ?? null;

        if (!$success) {
            return $this->error_result(
                get_string('error_api_error', 'local_aitutor', $error ?? 'Unknown error'),
                $error
            );
        }

        return (object) [
            'success' => true,
            'data'    => $data,
            'error'   => null,
            'meta'    => $meta,
        ];
    }

    /**
     * Build a standardised error result object.
     *
     * @param string $message  Human-readable error message (for the UI).
     * @param string|null $detail  Technical detail (for logging).
     * @return \stdClass
     */
    private function error_result(string $message, ?string $detail = null): \stdClass {
        // Log the full detail for administrators.
        if ($detail) {
            $this->log_debug("AI Tutor API error: {$detail}");
        }

        return (object) [
            'success' => false,
            'data'    => null,
            'error'   => $message,
            'meta'    => null,
        ];
    }

    /**
     * Write a debug message to the Moodle logging system.
     *
     * @param string $message
     */
    private function log_debug(string $message): void {
        if ($this->debug) {
            debugging($message, DEBUG_DEVELOPER);
        }
        // Always write to the Moodle error log so admins can review.
        \core\session\manager::write_close(); // Avoid session locks during logging.
        error_log("[local_aitutor] {$message}");
    }
}
