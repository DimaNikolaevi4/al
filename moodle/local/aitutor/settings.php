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
 * Plugin settings for the AI Tutor plugin.
 *
 * @package    local_aitutor
 * @copyright  2026 AI Tutor Project
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

defined('MOODLE_INTERNAL') || die();

if ($hassiteconfig) {
    $settings = new admin_settingpage('local_aitutor', get_string('pluginname', 'local_aitutor'));
    $ADMIN->add('localplugins', $settings);

    // Section heading.
    $settings->add(new admin_setting_heading(
        'local_aitutor/settings_heading',
        '',
        get_string('settings_heading', 'local_aitutor')
    ));

    // API endpoint URL.
    $settings->add(new admin_setting_configtext(
        'local_aitutor/api_url',
        get_string('settings_api_url', 'local_aitutor'),
        get_string('settings_api_url_desc', 'local_aitutor'),
        'http://localhost:8000',
        PARAM_URL
    ));

    // API key (optional).
    $settings->add(new admin_setting_configpassword(
        'local_aitutor/api_key',
        get_string('settings_api_key', 'local_aitutor'),
        get_string('settings_api_key_desc', 'local_aitutor'),
        '',
        PARAM_ALPHANUMEXT
    ));

    // Request timeout.
    $settings->add(new admin_setting_configtext(
        'local_aitutor/timeout',
        get_string('settings_timeout', 'local_aitutor'),
        get_string('settings_timeout_desc', 'local_aitutor'),
        120,
        PARAM_INT
    ));

    // Feature toggles — Summary.
    $settings->add(new admin_setting_configcheckbox(
        'local_aitutor/enable_summary',
        get_string('settings_enable_summary', 'local_aitutor'),
        get_string('settings_enable_summary_desc', 'local_aitutor'),
        1
    ));

    // Feature toggles — Quiz.
    $settings->add(new admin_setting_configcheckbox(
        'local_aitutor/enable_quiz',
        get_string('settings_enable_quiz', 'local_aitutor'),
        get_string('settings_enable_quiz_desc', 'local_aitutor'),
        1
    ));

    // Feature toggles — Chat.
    $settings->add(new admin_setting_configcheckbox(
        'local_aitutor/enable_chat',
        get_string('settings_enable_chat', 'local_aitutor'),
        get_string('settings_enable_chat_desc', 'local_aitutor'),
        1
    ));

    // Maximum lecture length.
    $settings->add(new admin_setting_configtext(
        'local_aitutor/max_lecture_length',
        get_string('settings_max_lecture_length', 'local_aitutor'),
        get_string('settings_max_lecture_length_desc', 'local_aitutor'),
        50000,
        PARAM_INT
    ));

    // Default quiz difficulty.
    $settings->add(new admin_setting_configselect(
        'local_aitutor/default_difficulty',
        get_string('settings_default_difficulty', 'local_aitutor'),
        get_string('settings_default_difficulty_desc', 'local_aitutor'),
        'medium',
        [
            'easy'   => get_string('settings_difficulty_easy', 'local_aitutor'),
            'medium' => get_string('settings_difficulty_medium', 'local_aitutor'),
            'hard'   => get_string('settings_difficulty_hard', 'local_aitutor'),
        ]
    ));
}
