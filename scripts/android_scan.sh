#!/usr/bin/env bash

## For scanning the phone and downloading some specific information of the phone
## Input: serial number 
adb=$((command -v adb || command -v adb.exe) | tr -d '\r')
if [[ -z "$adb" ]]; then
    echo "adb not found in path. Please install it from https://developer.android.com/studio/command-line/adb"
    echo "Or use brew install android-platform-tools"
    exit 1
else 
    echo "adb found at $adb"
fi
export adb=$adb

function usage {
    echo "$ bash $0 scan <serial_no>"
    echo "Or"
    echo "$ bash $0 info <dump_file> <appId>"
    echo "scan: Scan the phone and dump the information"
    echo "info: Retrieve information about a specific app"
    echo "serial_no: Serial number of the device. Use adb devices to find the serial number"
    echo "appId: Package name of the app (only for info)"
    echo "dump_file: File to dump the information into"
}
# If number of arguments is less than 2, print usage
if [[ $# -lt 2 ]]; then
    usage
    exit 1
fi

function scan {
    act=$1
    $adb $serial shell dumpsys "$act" | sed -e 's/\(\s*\)[a-zA-Z0-9._%+-]\+@[a-zA-Z0-9.-]\+\.[a-zA-Z]\{2,4\}\b/\1<email>/g;s/\(\s*\)[a-zA-Z0-9._%+-]\+_gmail.com/\1<db_email>/g'
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
        echo; echo "DUMP OF SERVICE $a"
        scan "$a"
    done

    echo; echo "DUMP OF SERVICE net_stats"
    $adb shell cat /proc/net/xt_qtaguid/stats | sed 's/ /,/g'

    for namespace in secure system global; do
        echo; echo "DUMP OF SETTINGS $namespace"
	    $adb shell settings list "$namespace"
    done
}

function full_scan {
    # Create dump output with error redirection
	dump  | sed \
         -e 's/^\(\s*\)lastDisabledCaller: /\1lastDisabledCaller:\1  /g;' \
         -e 's/^\(\s*\)User 0: ceDataInode\(.*\)/\1User 0:\n\1  ceDataInode\2/g' \
         -e 's/^\(\s*\)\(Excluded packages:\)/  \1\2/g' \
         -e 's/^\(\s*\)#\(.*\)$/\1\2/g' > "$ofname"
    
    # Verify dump was written
    if [[ ! -s "$ofname" ]]; then
        (>&2 echo "ERROR: Dump file is empty: $ofname")
        return 1
    fi
    
    (>&2 echo "Dump written to: $ofname")
    ## The apks can be huge and wasting space. 
    # (>&2 echo "Pulling apks in background...")
    # mkdir -p ./logs
    # bash ./scripts/pull_apks.sh "$serial" >> ./logs/android_scan.logs 2>&1 &
}

info="$3"
if [ ! -z "$info" ]; then
    (>&2 echo "------ Running app info ------- $1 $2")
    ofname="$2"
    appId="$3"
    retrieve "$appId"
else 
    (>&2 echo "------ Running full scan ------- $1")
    serial="-s $1"
    ofname="$2"
    (>&2 echo "Device serial: $serial")
    (>&2 echo "Output file: $ofname")
    $adb devices
    full_scan
    echo "Finished scanning. Pulling apks in background"
    # Clear the settings to remove developer options
    $adb $serial shell pm clear com.android.settings 2>/dev/null || true
    exit 0
fi
