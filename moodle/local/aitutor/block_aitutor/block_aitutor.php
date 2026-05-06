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
 * AI Tutor Block — provides quick-access buttons to AI tutor features
 * in the course sidebar.
 *
 * @package    block_aitutor
 * @copyright  2026 AI Tutor Project
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

defined('MOODLE_INTERNAL') || die();

class block_aitutor extends block_base {

    /**
     * Initialise the block.
     */
    public function init(): void {
        $this->title = get_string('pluginname', 'block_aitutor');
    }

    /**
     * Only allow this block on course pages.
     *
     * @return array
     */
    public function applicable_formats(): array {
        return [
            'course-view'    => true,
            'course-view-*'  => true,
            'mod'            => false,
            'site'           => false,
            'my'             => false,
        ];
    }

    /**
     * The block has global configuration settings.
     *
     * @return bool
     */
    public function has_config(): bool {
        return true;
    }

    /**
     * Generate the HTML content for the block.
     *
     * @return stdClass|string
     */
    public function get_content() {
        global $USER, $COURSE, $PAGE;

        if ($this->content !== null) {
            return $this->content;
        }

        // Check capability.
        $context = context_course::instance($COURSE->id);
        if (!has_capability('local/aitutor:use', $context)) {
            return $this->content = '';
        }

        $this->content = new stdClass();
        $this->content->text   = '';
        $this->content->footer = '';

        // Read which features this block instance should display.
        $showsummary = !isset($this->config->show_summary) || (bool) $this->config->show_summary;
        $showquiz    = !isset($this->config->show_quiz)    || (bool) $this->config->show_quiz;
        $showchat    = !isset($this->config->show_chat)    || (bool) $this->config->show_chat;

        // Check global feature toggles.
        $summaryenabled = (bool) get_config('local_aitutor', 'enable_summary');
        $quizenabled    = (bool) get_config('local_aitutor', 'enable_quiz');
        $chatenabled    = (bool) get_config('local_aitutor', 'enable_chat');

        // AJAX URL and course ID for JS.
        $ajaxurl  = new \moodle_url('/local/aitutor/ajax.php');
        $courseid = $COURSE->id;

        // Initialise JS module.
        $PAGE->requires->js_call_amd('local_aitutor/aitutor_block', 'init', [
            'ajaxUrl'    => $ajaxurl->out(false),
            'courseId'   => $courseid,
            'sessKey'    => sesskey(),
            'showSummary' => ($showsummary && $summaryenabled),
            'showQuiz'   => ($showquiz && $quizenabled),
            'showChat'   => ($showchat && $chatenabled),
        ]);

        $this->content->text = html_writer::div('', 'aitutor-block-container', [
            'id' => 'aitutor-block-' . $this->instance->id,
        ]);

        return $this->content;
    }
}
