#!/bin/bash
idb=pymobiledevice3
if [ -n "${PREFIX:-}" ]; then
    idb="python3 -m isdi.scanner.pmd3_wrapper"
    if command -v termux-usb >/dev/null 2>&1; then
        termux-usb -r -E -e "usbmuxd -f -v" $(termux-usb -l | python -c "import sys, json; a=json.load(sys.stdin); print(a[0] if len(a)>0 else '');")
    fi
elif grep -qi microsoft /proc/version; then
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
serial="$1"
outf="$2"

printf "Serial: %s\n" "$serial"

# Always dump: a cached dump would hide apps installed since the last scan.
echo "{
    \"apps\": $(${idb} apps list --udid "$serial"),
    \"devinfo\": $(${idb} lockdown info --udid "$serial")
}" > "$outf"

if [ -s "$outf" ]; then
    echo "Dump completed successfully: $outf"
    exit 0
else
    echo "Error: Failed to create dump file"
    exit 1
fi
