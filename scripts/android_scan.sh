#!/usr/bin/env bash

## For scanning the phone and downloading some specific information of the phone
## Input: serial number 

if [[ $# -lt 1 ]]; then
    echo -e "You have to provide a serial number. #Num args: $#"
    exit 1
fi
platform='unknown'
unamestr="$(uname)"
if [[ "$unamestr" == 'Linux' ]]; then
   platform='linux'
elif [[ "$unamestr" == 'Darwin' ]]; then
    platform='darwin'
elif [[ "$unamestr" == 'FreeBSD' ]]; then
   platform='freebsd'
fi

if command -v adb &>/dev/null;
then
    adb=$(command -v adb)
else
    echo "Trying static adb. Unlikely to work on newer MAC or Linux. Please install 'adb'"
    if [[ $platform == 'darwin' ]]; then
        adb='static_data/adb-darwin'
    elif [[ $platform == 'linux' ]]; then
        adb="static_data/adb-linux.$(uname -r)"
        if [[ ! -e $adb ]]; then
            adb="static_data/adb-linux"
        fi
    fi
fi
# if adb exists please use that and don't try to override

echo "$platform" "$adb"
export adb=$adb


serial="-s $2"
hmac_serial="-s $3"
dump_dir="./phone_dumps/"
ofname=$dump_dir/${hmac_serial:3}_android.txt

function scan {
    act=$1
    $adb "$serial" shell dumpsys "$act" | \
        sed -e 's/\(\s*\)[a-zA-Z0-9._%+-]\+@[a-zA-Z0-9.-]\+\.[a-zA-Z]\{2,4\}\b/\1<email>/g;s/\(\s*\)[a-zA-Z0-9._%+-]\+_gmail.com/\1<db_email>/g'
}


# The lines containing word spy in the phone! A heuristic to find
# Offstore spyware
function scan_spy {
    if [[ ! -e $ofname ]]; then
        echo "Run scan first"
        return 1
    fi
    grep -Eio '[a-zA-Z0-9\.]*spy[a-zA-Z0-9\.]*' "$ofname" | sort -u
}


function retrieve {
    # Make a python parser for this might be much faster
    if [[ ! -e $ofname ]]; then
        echo "Run scan first"
        return 1
    fi
    app="$1"
    process_uid=$(grep -A1 "Package \[$app\]" $ofname | sed '1d;s/.*userId=\([0-9]\+\).*/\1/g')
    process_uidu=$(grep -Eo "app=ProcessRecord{[a-f0-9]+ [0-9]+:$app/([a-z0-9]*)" "$ofname" | cut -d '/' -f 2 | sort -u)
    
    echo "$process_uid  $process_uidu"
    # Install date
    printf 'Install: %s\n' "$(awk "/Package \[$app\]/{flag=1;next}/install permissions:/{flag=0}flag" "$ofname" | grep Time | tr -d '  ')"

    # Memory info 
    printf 'Memory: %s\n' "$(awk '/Total PSS by process/{flag=1;next}/Total PSS/{flag=0}flag' "$ofname" | grep $app | sed '/^\s*$/d')"

    # Network info - cnt_set=0 => background,rx_bytes
    printf 'DataUsage (%s): %s\n' "${process_uid}" "$(awk "/DUMP OF SERVICE net_stats/{flag=1;next}/DUMP OF SERVICE/{flag=0}flag" "$ofname" | sed 's/ /,/g' | csvgrep -c 4 -m ${process_uid} | csvcut -c 4,5,6,8)"
    # awk "/DUMP OF SERVICE net_stats/{flag=1;next}/DUMP OF SERVICE/{flag=0}flag" $ofname | sed 's/ /,/g' | grep -a "${process_uid}"

    # Battery info
    printf "Battery (%s): %s\n" "${process_uidu}" "$(awk '/Estimated power use/{flag=1;next}/^\s*$/{flag=0}flag' "$ofname" | grep "Uid ${process_uidu}")"
    # Device Admin
}


services=(package location media.camera netpolicy mount 
          cpuinfo dbinfo meminfo
          procstats batterystats "netstats detail" usagestats
          activity appops)

function dump {
    for a in "${services[@]}"; do
        echo "DUMP OF SERVICE $a"
        scan "$a"
    done
    echo "DUMP OF SERVICE net_stats"
    $adb shell cat /proc/net/xt_qtaguid/stats | sed 's/ /,/g'
    for namespace in secure system global; do
	echo "DUMP OF SETTINGS $namespace"
	$adb shell settings list "$namespace"
    done
}

function full_scan {
    # If file older than 20 min then receate
    if [[ $(find "$ofname" -mmin +20 -print) ]]; then 
        echo "File is still pretty fresh"
        echo "Not re-dumping"
    else
	dump  > "$ofname" 2> error.txt
    fi
    echo "Pulling apks."
    bash ./scripts/pull_apks.sh "$serial"
}

if [[ "$1" == "scan" ]]; then 
    (>&2 echo "------ Running full scan ------- $2")
    $adb devices
    full_scan >> ./dumps/android_scan.logs & 
    sleep 120;  # sleep for 2 minutes
    # Clear the settings to remove developer options
    $adb $serial shell pm clear com.android.settings
elif [[ "$1" == "info" ]]; then
    (>&2 echo "------ Running app info ------- $2 $3")
    retrieve "$3"
else
    echo "$ bash $0 <scan|info> <serial_no> [appId]"
    exit 1;
fi


