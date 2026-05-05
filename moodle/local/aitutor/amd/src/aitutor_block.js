/**
 * JavaScript AMD module for the AI Tutor block.
 *
 * Handles modal dialogs, AJAX calls to the backend, and polling
 * for async task results.
 *
 * @module     local_aitutor/aitutor_block
 * @copyright  2026 AI Tutor Project
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
define(['core/ajax', 'core/str', 'core/notification', 'core/modal_factory', 'core/modal_events'],
    function(Ajax, Str, Notification, ModalFactory, ModalEvents) {

        /**
         * @param {Object} config Configuration passed from PHP.
         */
        function init(config) {
            var ajaxUrl    = config.ajaxUrl;
            var courseId   = config.courseId;
            var sessKey    = config.sessKey;
            var container  = document.getElementById('aitutor-block-' +
                document.querySelector('.block_aitutor .aitutor-block-container')
                    ?.id.replace('aitutor-block-', '') || 0);

            // Find or use the first block container.
            container = document.querySelector('.block_aitutor .aitutor-block-container');
            if (!container) {
                return;
            }

            // Build buttons.
            var buttons = [];

            if (config.showSummary) {
                Str.get_string('btn_create_summary', 'local_aitutor').done(function(label) {
                    buttons.push({type: 'summary', label: label});
                });
            }
            if (config.showQuiz) {
                Str.get_string('btn_generate_test', 'local_aitutor').done(function(label) {
                    buttons.push({type: 'quiz', label: label});
                });
            }
            if (config.showChat) {
                Str.get_string('btn_ask_ai', 'local_aitutor').done(function(label) {
                    buttons.push({type: 'chat', label: label});
                });
            }

            // We need to wait for strings to load, use a small delay pattern.
            // Since Str.get_string is async, build buttons after all resolve.
            var promises = [];
            if (config.showSummary) {
                promises.push(Str.get_string('btn_create_summary', 'local_aitutor'));
            }
            if (config.showQuiz) {
                promises.push(Str.get_string('btn_generate_test', 'local_aitutor'));
            }
            if (config.showChat) {
                promises.push(Str.get_string('btn_ask_ai', 'local_aitutor'));
            }
            promises.push(Str.get_string('label_lecture_text', 'local_aitutor'));
            promises.push(Str.get_string('placeholder_lecture_text', 'local_aitutor'));
            promises.push(Str.get_string('placeholder_chat_message', 'local_aitutor'));
            promises.push(Str.get_string('btn_send', 'local_aitutor'));
            promises.push(Str.get_string('btn_cancel', 'local_aitutor'));
            promises.push(Str.get_string('btn_retry', 'local_aitutor'));
            promises.push(Str.get_string('btn_close', 'local_aitutor'));
            promises.push(Str.get_string('status_processing', 'local_aitutor'));
            promises.push(Str.get_string('status_failed', 'local_aitutor'));
            promises.push(Str.get_string('label_difficulty', 'local_aitutor'));
            promises.push(Str.get_string('settings_difficulty_easy', 'local_aitutor'));
            promises.push(Str.get_string('settings_difficulty_medium', 'local_aitutor'));
            promises.push(Str.get_string('settings_difficulty_hard', 'local_aitutor'));
            promises.push(Str.get_string('modal_title_summary', 'local_aitutor'));
            promises.push(Str.get_string('modal_title_quiz', 'local_aitutor'));
            promises.push(Str.get_string('modal_title_chat', 'local_aitutor'));
            promises.push(Str.get_string('error_empty_text', 'local_aitutor'));
            promises.push(Str.get_string('error_empty_message', 'local_aitutor'));
            promises.push(Str.get_string('error_feature_disabled', 'local_aitutor'));
            promises.push(Str.get_string('status_complete', 'local_aitutor'));
            promises.push(Str.get_string('label_chat_message', 'local_aitutor'));

            $.when.apply($, promises).then(function() {
                // Build button array from resolved strings.
                var idx = 0;
                var labels = {};
                labels.btn_create_summary = arguments[idx++];
                labels.btn_generate_test = arguments[idx++];
                labels.btn_ask_ai = arguments[idx++];
                labels.label_lecture_text = arguments[idx++];
                labels.placeholder_lecture_text = arguments[idx++];
                labels.placeholder_chat_message = arguments[idx++];
                labels.btn_send = arguments[idx++];
                labels.btn_cancel = arguments[idx++];
                labels.btn_retry = arguments[idx++];
                labels.btn_close = arguments[idx++];
                labels.status_processing = arguments[idx++];
                labels.status_failed = arguments[idx++];
                labels.label_difficulty = arguments[idx++];
                labels.settings_difficulty_easy = arguments[idx++];
                labels.settings_difficulty_medium = arguments[idx++];
                labels.settings_difficulty_hard = arguments[idx++];
                labels.modal_title_summary = arguments[idx++];
                labels.modal_title_quiz = arguments[idx++];
                labels.modal_title_chat = arguments[idx++];
                labels.error_empty_text = arguments[idx++];
                labels.error_empty_message = arguments[idx++];
                labels.error_feature_disabled = arguments[idx++];
                labels.status_complete = arguments[idx++];
                labels.label_chat_message = arguments[idx++];

                var btnList = [];
                if (config.showSummary) {
                    btnList.push({type: 'summary', label: labels.btn_create_summary});
                }
                if (config.showQuiz) {
                    btnList.push({type: 'quiz', label: labels.btn_generate_test});
                }
                if (config.showChat) {
                    btnList.push({type: 'chat', label: labels.btn_ask_ai});
                }

                renderButtons(container, btnList, labels);
            });

            /**
             * Render action buttons inside the block container.
             */
            function renderButtons(el, btns, labels) {
                el.innerHTML = '';
                var wrapper = document.createElement('div');
                wrapper.className = 'aitutor-buttons';

                btns.forEach(function(btn) {
                    var button = document.createElement('button');
                    button.type = 'button';
                    button.className = 'btn aitutor-btn aitutor-btn-' + btn.type;
                    button.textContent = btn.label;
                    button.setAttribute('data-type', btn.type);
                    button.addEventListener('click', function() {
                        openModal(btn.type, labels);
                    });
                    wrapper.appendChild(button);
                });

                el.appendChild(wrapper);
            }

            /**
             * Open a modal dialog for the selected feature.
             */
            function openModal(type, labels) {
                var titles = {
                    summary: labels.modal_title_summary,
                    quiz:    labels.modal_title_quiz,
                    chat:    labels.modal_title_chat
                };

                var bodyHTML = '';

                if (type === 'summary' || type === 'quiz') {
                    bodyHTML = '<label class="aitutor-label">' + labels.label_lecture_text +
                        '</label><textarea class="aitutor-textarea form-control" ' +
                        'id="aitutor-input-text" rows="6" placeholder="' +
                        labels.placeholder_lecture_text + '"></textarea>';

                    if (type === 'quiz') {
                        bodyHTML += '<div class="aitutor-difficulty-row">' +
                            '<label class="aitutor-label">' + labels.label_difficulty + '</label>' +
                            '<select id="aitutor-difficulty" class="form-control">' +
                            '<option value="easy">' + labels.settings_difficulty_easy + '</option>' +
                            '<option value="medium" selected>' + labels.settings_difficulty_medium + '</option>' +
                            '<option value="hard">' + labels.settings_difficulty_hard + '</option>' +
                            '</select></div>';
                    }
                } else if (type === 'chat') {
                    bodyHTML = '<div id="aitutor-chat-history" class="aitutor-chat-history"></div>' +
                        '<label class="aitutor-label">' + labels.label_chat_message + '</label>' +
                        '<textarea class="aitutor-textarea form-control" ' +
                        'id="aitutor-input-text" rows="3" placeholder="' +
                        labels.placeholder_chat_message + '"></textarea>';
                }

                bodyHTML += '<div class="aitutor-status" id="aitutor-status"></div>';
                bodyHTML += '<div class="aitutor-result" id="aitutor-result"></div>';

                ModalFactory.create({
                    type: ModalFactory.types.DEFAULT,
                    title: titles[type] || 'AI Tutor',
                    body: bodyHTML,
                    large: true
                }).then(function(modal) {
                    modal.setLarge(true);

                    // Bind send button.
                    modal.getRoot().on(ModalEvents.created, function() {
                        var sendBtn = document.createElement('button');
                        sendBtn.type = 'button';
                        sendBtn.className = 'btn btn-primary aitutor-send-btn';
                        sendBtn.textContent = labels.btn_send;
                        sendBtn.addEventListener('click', function() {
                            handleSend(type, labels);
                        });
                        modal.getRoot().find('.modal-footer').prepend(sendBtn);
                    });

                    modal.show();
                });
            }

            /**
             * Handle the send action.
             */
            function handleSend(type, labels) {
                var inputEl = document.getElementById('aitutor-input-text');
                var statusEl = document.getElementById('aitutor-status');
                var resultEl = document.getElementById('aitutor-result');

                if (!inputEl) return;

                var text = inputEl.value.trim();

                if (type !== 'chat' && !text) {
                    statusEl.textContent = labels.error_empty_text;
                    statusEl.className = 'aitutor-status aitutor-status-error';
                    return;
                }
                if (type === 'chat' && !text) {
                    statusEl.textContent = labels.error_empty_message;
                    statusEl.className = 'aitutor-status aitutor-status-error';
                    return;
                }

                // Show processing.
                statusEl.innerHTML = '<span class="aitutor-spinner"></span> ' + labels.status_processing;
                statusEl.className = 'aitutor-status aitutor-status-processing';
                resultEl.innerHTML = '';

                var difficulty = '';
                if (type === 'quiz') {
                    var diffEl = document.getElementById('aitutor-difficulty');
                    difficulty = diffEl ? diffEl.value : 'medium';
                }

                // Send AJAX request.
                var fd = new FormData();
                fd.append('action', type);
                fd.append('courseid', courseId);
                fd.append('sesskey', sessKey);
                fd.append('text', text);
                if (difficulty) {
                    fd.append('difficulty', difficulty);
                }

                fetch(ajaxUrl, {
                    method: 'POST',
                    body: fd
                })
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    if (data.success && data.task_id) {
                        pollForResult(data.task_id, type, labels);
                    } else {
                        statusEl.textContent = data.error || labels.status_failed;
                        statusEl.className = 'aitutor-status aitutor-status-error';
                    }
                })
                .catch(function(err) {
                    statusEl.textContent = labels.status_failed + ': ' + (err.message || '');
                    statusEl.className = 'aitutor-status aitutor-status-error';
                });
            }

            /**
             * Poll the async task status until completion.
             */
            function pollForResult(taskId, type, labels) {
                var statusEl = document.getElementById('aitutor-status');
                var resultEl = document.getElementById('aitutor-result');
                var pollInterval = 3000; // 3 seconds.
                var maxAttempts = 60;    // 3 minutes max.
                var attempts = 0;

                function poll() {
                    var fd = new FormData();
                    fd.append('action', 'status');
                    fd.append('task_id', taskId);
                    fd.append('sesskey', sessKey);

                    fetch(ajaxUrl, {method: 'POST', body: fd})
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        attempts++;

                        if (data.success && data.result) {
                            var result = data.result;

                            if (result.status === 'complete' && result.result_text) {
                                statusEl.textContent = labels.status_complete;
                                statusEl.className = 'aitutor-status aitutor-status-complete';
                                renderResult(resultEl, result.result_text, type);
                            } else if (result.status === 'failed') {
                                statusEl.textContent = labels.status_failed +
                                    (result.error_message ? ': ' + result.error_message : '');
                                statusEl.className = 'aitutor-status aitutor-status-error';
                            } else {
                                // Still processing — poll again.
                                if (attempts < maxAttempts) {
                                    setTimeout(poll, pollInterval);
                                } else {
                                    statusEl.textContent = labels.status_failed;
                                    statusEl.className = 'aitutor-status aitutor-status-error';
                                }
                            }
                        } else if (attempts < maxAttempts) {
                            setTimeout(poll, pollInterval);
                        } else {
                            statusEl.textContent = labels.status_failed;
                            statusEl.className = 'aitutor-status aitutor-status-error';
                        }
                    })
                    .catch(function() {
                        if (attempts < maxAttempts) {
                            setTimeout(poll, pollInterval);
                        } else {
                            statusEl.textContent = labels.status_failed;
                            statusEl.className = 'aitutor-status aitutor-status-error';
                        }
                    });
                }

                poll();
            }

            /**
             * Render the result data.
             */
            function renderResult(el, resultText, type) {
                try {
                    var parsed = JSON.parse(resultText);
                    // Format based on type.
                    if (type === 'quiz' && parsed.questions) {
                        var html = '<div class="aitutor-quiz-result">';
                        parsed.questions.forEach(function(q, i) {
                            html += '<div class="aitutor-question">';
                            html += '<p><strong>' + (i + 1) + '. ' + q.question + '</strong></p>';
                            if (q.options) {
                                q.options.forEach(function(opt) {
                                    var marker = (opt === q.answer) ? ' ✓' : '';
                                    html += '<p class="aitutor-option">' + opt + marker + '</p>';
                                });
                            }
                            if (q.answer) {
                                html += '<p class="aitutor-answer">Ответ: ' + q.answer + '</p>';
                            }
                            html += '</div>';
                        });
                        html += '</div>';
                        el.innerHTML = html;
                    } else {
                        // Summary or generic JSON — render as formatted text.
                        var display = (typeof parsed === 'string') ? parsed :
                            (parsed.summary || parsed.text || parsed.answer || JSON.stringify(parsed, null, 2));
                        el.innerHTML = '<div class="aitutor-result-text">' +
                            display.replace(/\n/g, '<br>') + '</div>';
                    }
                } catch (e) {
                    // Plain text fallback.
                    el.innerHTML = '<div class="aitutor-result-text">' +
                        resultText.replace(/\n/g, '<br>') + '</div>';
                }
            }
        }

        return {init: init};
    }
);
