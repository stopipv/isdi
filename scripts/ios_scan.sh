#!/bin/bash
idb=pymobiledevice3
if grep -qi microsoft /proc/version; then
    platform="wsl"
    idb=pymobiledevice3.exe
fi

# test if idb is installed
if ! command -v ${idb} &> /dev/null
then
    echo "idb could not be found. Please install it first."
    exit
fi
if [ $# -ne 2 ]; then
    echo "Usage: $0 <serial> <dumpfile>"
    exit 1
fi
serial="--udid $1"
outf="$2"

printf "Serial: %s\n" "$serial"

if [[ $(find "$ofname" -mmin +20 -print) ]]; then 
        (>&2 echo "File is still pretty fresh. Not re-dumping")
    else
        echo "{
            \"apps\": $("${idb}" apps list $ser),
            \"devinfo\": $("${idb}" lockdown info $ser)
        }" > "$outf"
fi