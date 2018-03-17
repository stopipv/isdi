function updateProgress(percentage) {
    $('#scan-prog').css("width", percentage + "%");
    // $('#pbar_innertext').text(percentage + "%");
}

var start = null;
var maxTime = 30000;  // 30 sec
var timeoutVal = Math.floor(maxTime/50);
var perc = 0;
function startProgressbar() {
    start = new Date();
    perc = 0;
    animateUpdate();
}
function max(a, b) {
    if (a>b)
        return a;
    else
        return b;
}

function animateUpdate() {
    var now = new Date();
    var timeDiff = now.getTime() - start.getTime();
    perc = max(perc, Math.round((timeDiff/maxTime)*100));

    if (perc <= 100) {
        updateProgress(perc);
        setTimeout(animateUpdate, timeoutVal);
    }
}

function create_tab(data, device, ser) {
    var s = '';
    var i = 0;
    d = $.parseJSON(data)
    for (k in d) {
        i += 1;
        s += '<tr id="'+k+'">';
        s += "<td>" + i + "</td>";
        s += "<td><a href='/details/app/" + device + "?id=" + k + "&ser=" + ser;
        s += "' target='_blank'>" + d[k] + "</td>";
        s += "<td><code>" + k + "</code></td>";
        s += "<td>" + get_actions(k);
        s += '</tr>';
    }
    if (i <= 0) {
        s = "<tr><td colspan='4' class='alert-success'>No spyware found! ";
        s += "<sup>1</sup></td></tr>";
    }
    return s;
}

function fetch(url, device) {
    startProgressbar();
    $.get(url, function(data) {
        perc = 100;
        updateProgress(100);
        var d = $.parseJSON(data);
        var ser = d['serial'];
        var s = "<tr><td colspan='4'><h5 style='color: red'>Off-store spyware apps</h5></td></tr> ";
        s += create_tab(d['offstore'], device, ser);

        s += "<tr><td colspan='4'><h5 style='color: magenta'>On-store spyware apps</h5></td></tr> ";
        s += create_tab(d['onstore'], device, ser);

        s += '<input type="hidden" name="url" value="';
        s += url.replace('/scan/', '') + '"></input>';
        $('#applist').html(s);
        $('input[value=ignore]').prop('checked', 'checked');
        $('#btn-submit').prop('disabled', false);
    });
}
