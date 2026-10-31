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

// One scan at a time: while it runs, every device's Scan button is disabled.
function setScanning($button, scanning) {
    $('#device-list button').prop('disabled', scanning);
    if (!$button || !$button.length) {
        return;
    }
    if (scanning) {
        $button.data('original-text', $button.text());
        $button.prop('disabled', true).text('Scanning...');
    } else {
        $button.prop('disabled', false).text($button.data('original-text') || 'Scan');
    }
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
                    setScanning($button, false);
                    updateProgress(0, state.error || state.message || 'Scan failed');
                    report_failure(state.error || state.message || 'Scan failed');
                }
            })
            .fail(function () {
                window.clearInterval(timer);
                setScanning($button, false);
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

    setScanning($button, true);

    resetScanProgress('Starting scan...');
    $.post('/scan/start', $form.serialize())
        .done(function (resp) {
            if (!resp || !resp.status_url || !resp.result_url) {
                setScanning($button, false);
                report_failure('Could not start the scan.');
                updateProgress(0, 'Could not start the scan.');
                return;
            }

            updateProgress(5, 'Scan started.');
            pollScanStatus(resp.status_url, resp.result_url, $button);
        })
        .fail(function (xhr) {
            setScanning($button, false);

            var message = 'Could not start the scan.';
            if (xhr.responseJSON && xhr.responseJSON.error) {
                message = xhr.responseJSON.error;
            }
            updateProgress(0, message);
            report_failure(message);
        });

    return false;
}

// Home page: poll /devices and offer a Scan button for each attached phone.
var DEVICE_KINDS = {android: 'Android', ios: 'iOS', test: 'Test'};
var DEVICE_HINTS = {
    'unauthorized': 'Unlock the phone and tap "Allow" on the USB debugging prompt.',
    'offline': 'Unplug the cable and plug it back in.',
    'no permissions': 'adb cannot access this USB device. See the setup instructions.'
};
var lastDeviceList = null;
var devicePollInFlight = false;

function renderDevices(devices) {
    var $list = $('#device-list').empty();
    if (!devices.length) {
        $list.append($('<p class="text-muted small">').html(
            'No phone detected. Connect one with a USB cable, then follow the ' +
            '<a href="/instruction" target="_blank" rel="noopener">scan instructions</a> if it does not appear.'));
        return;
    }
    devices.forEach(function (d) {
        // Labels come from the phone (e.g. its model name), so insert them as text.
        var $info = $('<div class="isdi-device-info">')
            .append($('<b>').text(d.label))
            .append(' ')
            .append($('<span class="badge badge-secondary">').text(DEVICE_KINDS[d.device] || d.device));
        if (d.last_scanned) {
            $info.append($('<div class="small text-muted">').text('(Last scanned: ' + String(d.last_scanned).slice(0, 16) + ')'));
        }
        if (d.state !== 'ready') {
            $info.append($('<div class="small text-danger">').text(DEVICE_HINTS[d.state] || ('Not ready: ' + d.state)));
        }
        var $form = $('<form method="POST" action="/scan" class="isdi-attached-device">')
            .append($('<input type="hidden" name="device">').val(d.device))
            .append($('<input type="hidden" name="devid">').val(d.devid))
            .append($info);
        if (d.state === 'ready') {
            $form.append($('<button type="submit" class="btn btn-primary btn-sm">').text('Scan'));
            $form.on('submit', function () { return startScan(this); });
        }
        $list.append($form);
    });
}

function pollDevices() {
    var scanning = $('#device-list button:disabled').length > 0;
    // Listing iOS devices can take a few seconds; never stack requests.
    if (document.hidden || scanning || devicePollInFlight) {
        return;
    }
    devicePollInFlight = true;
    $.getJSON('/devices').done(function (resp) {
        var key = JSON.stringify(resp.devices);
        if (key !== lastDeviceList) {
            lastDeviceList = key;
            renderDevices(resp.devices);
        }
    }).always(function () {
        devicePollInFlight = false;
    });
}

$(function () {
    if ($('#device-list').length) {
        pollDevices();
        setInterval(pollDevices, 3000);
    }
});

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
