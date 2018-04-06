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
