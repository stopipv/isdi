// CSRF token for state-changing requests (checked by the server on POST).
function csrf_token() {
    return $('meta[name="csrf-token"]').attr('content') || '';
}

$.ajaxSetup({
    beforeSend: function (xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS)$/i.test(settings.type)) {
            xhr.setRequestHeader('X-CSRFToken', csrf_token());
        }
    }
});

$(document).on('click', '.js-delete-app', function () {
    delete_app($(this).attr('data-appid'), this);
});

function updateProgress(percentage, message) {
    var $progress = $('#scan-prog');
    var $wrap = $('#scan-progress-wrap');
    if (!$wrap.length) {
        $wrap = $progress.closest('.progress');
    }
    var $text = $('#scan-progress-text');

    if (!$progress.length) {
        return;
    }

    if ($wrap.length) {
        $wrap.show();
    }
    if (percentage >= 100) {
        percentage = 100;
    }

    $progress.css("width", percentage + "%");
    $progress.attr('aria-valuenow', percentage);
    $progress.text(percentage + "%");

    if ($text.length) {
        if (message) {
            $text.text(message).show();
        } else {
            $text.hide().text('');
        }
    }
}

function resetScanProgress(message) {
    updateProgress(0, message || 'Preparing scan...');
}

function finishScanProgress(message) {
    updateProgress(100, message || 'Scan complete');
}

function pollScanStatus(statusUrl, resultUrl, $button) {
    var pollDelay = 1000;
    var timer = window.setInterval(function () {
        $.getJSON(statusUrl)
            .done(function (state) {
                if (!state) {
                    return;
                }
                updateProgress(state.percent || 0, state.message || state.step || 'Scanning...');

                if (state.status === 'done') {
                    window.clearInterval(timer);
                    finishScanProgress(state.message || 'Scan complete');
                    window.location.href = resultUrl;
                } else if (state.status === 'error') {
                    window.clearInterval(timer);
                    if ($button && $button.length) {
                        $button.prop('disabled', false).text($button.data('original-text') || 'Scan now');
                    }
                    updateProgress(0, state.error || state.message || 'Scan failed');
                    report_failure(state.error || state.message || 'Scan failed');
                }
            })
            .fail(function () {
                window.clearInterval(timer);
                if ($button && $button.length) {
                    $button.prop('disabled', false).text($button.data('original-text') || 'Scan now');
                }
                updateProgress(0, 'Could not read scan status.');
                report_failure('Could not read scan status.');
            });
    }, pollDelay);
}

function startScan(form) {
    var $form = $(form);
    var $button = $form.find('button[type=submit]').first();

    if (!$form.length) {
        return true;
    }

    if ($button.length) {
        $button.data('original-text', $button.text());
        $button.prop('disabled', true).text('Scanning...');
    }

    resetScanProgress('Starting scan...');
    $.post('/scan/start', $form.serialize())
        .done(function (resp) {
            if (!resp || !resp.status_url || !resp.result_url) {
                if ($button.length) {
                    $button.prop('disabled', false).text($button.data('original-text') || 'Scan now');
                }
                report_failure('Could not start the scan.');
                updateProgress(0, 'Could not start the scan.');
                return;
            }

            updateProgress(5, 'Scan started.');
            pollScanStatus(resp.status_url, resp.result_url, $button);
        })
        .fail(function (xhr) {
            if ($button.length) {
                $button.prop('disabled', false).text($button.data('original-text') || 'Scan now');
            }

            var message = 'Could not start the scan.';
            if (xhr.responseJSON && xhr.responseJSON.error) {
                message = xhr.responseJSON.error;
            }
            updateProgress(0, message);
            report_failure(message);
        });

    return false;
}

function delete_app(appid, e) {
    if (!confirm("Are you sure you want to delete the app '" + appid + "'?")) {
        return;
    }
    $.post('/delete/app/' + scanid, {'appid': appid}).done(function (r) {
        $('tr').filter(function () { return $(this).attr('data-appid') === appid; })
            .addClass('text-muted');
        $(e).removeClass('text-warning js-delete-app')
            .addClass('text-success')
            .html('&#10003;');
        report_success($('<div>').text(r).html());
    }).fail(function (xhr) {
        report_failure("Could not delete the app '" + appid + "': " + (xhr.responseText || ''));
    });
}

function kill_app() {
    $.post('/kill').always(function () {
        window.open('', '_self').close();
    });
    return false;
}
