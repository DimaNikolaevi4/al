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
 * Edit form for the AI Tutor block instance configuration.
 *
 * Allows course editors to choose which features (summary, quiz, chat)
 * are displayed in this particular block instance.
 *
 * @package    block_aitutor
 * @copyright  2026 AI Tutor Project
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

defined('MOODLE_INTERNAL') || die();

class block_aitutor_edit_form extends block_edit_form {

    /**
     * Define the custom configuration fields for this block instance.
     *
     * @param MoodleQuickForm $mform
     */
    protected function specific_definition($mform): void {
        $mform->addElement('header', 'configheader', get_string('blocksettings', 'block'));

        // Show summary button.
        $mform->addElement(
            'advcheckbox',
            'config_show_summary',
            get_string('config_show_summary', 'block_aitutor'),
            null,
            null,
            [0, 1]
        );
        $mform->setDefault('config_show_summary', 1);
        $mform->addHelpButton('config_show_summary', 'config_show_summary', 'block_aitutor');

        // Show quiz button.
        $mform->addElement(
            'advcheckbox',
            'config_show_quiz',
            get_string('config_show_quiz', 'block_aitutor'),
            null,
            null,
            [0, 1]
        );
        $mform->setDefault('config_show_quiz', 1);
        $mform->addHelpButton('config_show_quiz', 'config_show_quiz', 'block_aitutor');

        // Show chat button.
        $mform->addElement(
            'advcheckbox',
            'config_show_chat',
            get_string('config_show_chat', 'block_aitutor'),
            null,
            null,
            [0, 1]
        );
        $mform->setDefault('config_show_chat', 1);
        $mform->addHelpButton('config_show_chat', 'config_show_chat', 'block_aitutor');
    }
}
