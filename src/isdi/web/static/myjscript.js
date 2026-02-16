function updateProgress(percentage) {
    if (percentage >= 99) {
        $('#scan-prog').animate({
            // width: "100%"
        }, 1000, function() {
            $(this).closest('.progress').fadeOut();
        });
    } else {
        $('#scan-prog').css("width", percentage + "%");
    }
    $('#scan-prog').text(percentage + "%");
}

function delete_app(appid, e) {
    y = confirm(`Are you sure you want to delete the app  '${appid}'?"`);
    if (!y){return;}
    data = {'appid': appid, 'serial': serial, 'device': device};
    $.post('/delete/app/' + scanid, data=data).done(function (r){
        $('tr#' + appid).addClass('text-muted');
        $(e).removeClass('text-warning');
        $(e).addClass('text-success');
        $(e).html('&#10003;');
        $(e).prop('onclick', null).off('click');
        report_success(r);
    }).fail(function(){
        report_failure("Could not delete the app '" + appid + "'")
    })
}


var start = null;
var maxTime = 5000;  // 30 sec
var timeoutVal = Math.floor(maxTime/50);
var perc = 0;
function startProgressbar() {
    start = new Date();
    perc = 0;
    $('#applist').html('')
    $('#scan-prog').animate({
    }, 100, function() {
        $(this).closest('.progress').fadeIn('fast');
    });
    animateUpdate();
}
function killProgressbar() {
    start = new Date(0);
}

function max(a, b) {
    if (a>b)
        return a;
    else
        return b;
}

function animateUpdate() {
    var now = new Date();
    var timeDiff = now.getTime() - start.getTime() - 1000;
    perc = max(perc, Math.round((timeDiff/maxTime)*100));

    if (perc <= 100) {
        updateProgress(perc);
        setTimeout(animateUpdate, timeoutVal);
    }
}


/* Unused functions */

 function get_actions(k) {
     var s = '<div class="btn-group" data-toggle="buttons">';
     $.each(['delete', 'ignore'], function(i, b) {
         s += '<label class="btn btn-danger">'
         s += '<input type="radio" name="actions-' + k +'" value="' + b + '"> </input>';
         s += b + '</label>';
     });
     s += '</div>';
     return s;
 }

 function create_tab(data, device, ser) {
     var s = '';
     var i = 0;
     d = $.parseJSON(data)
     console.log(data)
     for (k in d) {
         i += 1;
         s += '<tr id="'+k+'">';
         s += "<td><a class=\"h4 text-danger\" onclick='delete('" + device+"', '" + k + "')'>"
         s += "&otimes;</a></td>";
         s += "<td><a href='/details/app/" + device + "?id=" + k + "&ser=" + ser;
         s += "' target='_blank'>" + d[k]['title'] + "</td>";
         s += "<td><code>" + k + "</code></td>";
         s += "<td>" + d[k]["flags"] + "</td>";
         // s += "<td>" + get_actions(k) + "</td>";
         s += "<td><input type=\"text\" placeholder=\"Notes\" class='form-control'/></td>"
         s += '</tr>';
     }
     if (i <= 0) {
         s = "<tr><td colspan='5' class='alert-success'>No spyware found! ";
         s += "<sup>1</sup></td></tr>";
     }
     return s;
 }


function fetch(url, device) {
    startProgressbar();
    $.get(url, function (data) {
        perc = 100;
        updateProgress(100);
        var d = $.parseJSON(data);
        var ser = d['serial'];
        $('#device-id').attr("value", device);
        $('#device-id').css("font-size", "0.25in");
        var s = "";
        s += create_tab(d['apps'], device, ser);
        s += '<input type="hidden" name="url" value="';
        s += url.replace('/scan/', '') + '"></input>';
        $('#applist').html(s);
        $('input[value=ignore]').prop('checked', 'checked');
        $('#btn-submit').prop('disabled', false);
        $('#error-notice').html(d['error'])
    }).fail(function (err) {
        perc = 100;
        $('#error-notice').html(JSON.stringify(err));
    });
}


