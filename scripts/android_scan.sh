#!/bin/bash

## For scanning the phone and downloading some specific information of the phone
## Input: serial number 

if [[ $# -lt 1 ]]; then
    echo -e "You have to provide a serial number. #Num args: $#"
    exit -1
fi

serial="-s $2"
dump_dir="./phone_dumps/"
ofname=$dump_dir/${serial:3}.txt

email="^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$"
function scan {
    act=$1
    adb $serial shell dumpsys $act | \
        sed -e 's/\(\s*\)[a-zA-Z0-9._%+-]\+@[a-zA-Z0-9.-]\+\.[a-zA-Z]\{2,4\}\b/\1<email>/g;s/\(\s*\)[a-zA-Z0-9._%+-]\+_gmail.com/\1<db_email>/g'
}


# The lines containing word spy in the phone! A heuristic to find
# Offstore spyware
function scan_spy {
    if [[ ! -e $ofname ]]; then
        echo "Run scan first"
        return -1
    fi
    grep -Eio '[a-zA-Z0-9\.]*spy[a-zA-Z0-9\.]*' $ofname | sort -u
}


function retrieve {
    # Make a python parser for this might be much faster
    if [[ ! -e $ofname ]]; then
        echo "Run scan first"
        return -1
    fi
    app="$1"
    process_uid=$(grep -A1 "Package \[$app\]" $ofname | sed '1d;s/.*userId=\([0-9]\+\).*/\1/g')
    process_uidu=$(grep -Eo "app=ProcessRecord{[a-f0-9]+ [0-9]+:$app/([a-z0-9]*)" $ofname  | cut -d '/' -f 2 | sort -u)

    # Install date
    echo "Install Date"
    awk "/Package \[$app\]/{flag=1;next}/install permissions:/{flag=0}flag" $ofname | grep Time

    # Memory info 
    echo "Memory Usage"
    awk "/Total PSS by process/{flag=1;next}/Total PSS/{flag=0}flag" $ofname | grep $app

    # Network info - cnt_set=0 => background,rx_bytes
    echo "Data Usage - '${process_uid}'"
    awk "/DUMP OF SERVICE net_stats/{flag=1;next}/DUMP OF SERVICE/{flag=0}flag" $ofname | sed 's/ /,/g' | csvgrep -c 4 -m ${process_uid} | csvcut -c 4,5,6,8
    # awk "/DUMP OF SERVICE net_stats/{flag=1;next}/DUMP OF SERVICE/{flag=0}flag" $ofname | sed 's/ /,/g' | grep -a "${process_uid}"

    # Battery info
    echo "Battery usage - '${process_uidu}'"
    awk '/Estimated power use/{flag=1;next}/^\s*$/{flag=0}flag' $ofname | grep "Uid ${process_uidu}"

    # Device Admin
}


services=(package location media.camera netpolicy mount 
          cpuinfo dbinfo meminfo
          procstats batterystats netstats usagestats
          activity appops)

function full_scan {
    if [[ ! -e $ofname ]]; then
        secs_since_last_modified=100000000;
    else
        secs_since_last_modified=$(($(date +%s) - $(stat -c %Y $ofname)))
    fi
    if [[ ${secs_since_last_modified} -lt 1200 ]]; then # 20 min no re dump
        echo "File is still pretty fresh (${secs_since_last_modified} sec)"
        echo "Not re-dumping"
        exit 0
    fi
    rm -rf $ofname
    for a in ${services[*]}; do
        echo "--------------------------------------------------------------------------------------"
        echo "DUMP OF SERVICE $a"
        scan $a
        echo "--------------------------------------------------------------------------------------"
    done > "$ofname" 2> error.txt
    echo "DUMP OF SERVICE net_stats"
    adb shell cat /proc/net/xt_qtaguid/stats | sed 's/ /,/g'  >> "$ofname" 2>> error.txt
}
    
if [[ "$1" == "scan" ]]; then 
    (>&2 echo "------ Running full scan ------- $2")
    full_scan
elif [[ "$1" == "info" ]]; then
    (>&2 echo "------ Running app info ------- $2 $3")
    retrieve $3
else
    echo "$ bash $0 <scan|info> <serial_no> [appId]"
    exit -1;
fi

