#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
platform='unknown'
unamestr=`uname`
if [[ "$unamestr" == 'Linux' ]]; then
   platform='linux'
elif [[ "$unamestr" == 'Darwin' ]]; then
    platform='darwin'
elif [[ "$unamestr" == 'FreeBSD' ]]; then
   platform='freebsd'
fi

echo "$platform" "$adb"

serial=$(pymobiledevice3 usbmux list | awk -F'"' '/Identifier/ {print $4}')
mkdir -p phone_dumps/"$1"_ios
cd phone_dumps/"$1"_ios
# gets all of the details about each app (basically what ios_deploy does but with extra fields)
# ideviceinstaller -u "$serial" -l -o xml -o list_all > "$2"
pymobiledevice3 apps list > "$2"

# get around bug in Python 3 that doesn't recognize utf-8 encodings.
# sed -i -e 's/<data>/<string>/g' $2
# sed -i -e 's/<\/data>/<\/string>/g' $2

# maybe for macOS...
# plutil -convert json $2

# gets OS version, serial, etc. -x for xml. Raw is easy to parse, too.
pymobiledevice3 lockdown info > $3

# sed -i -e 's/<data>/<string>/g' $3
# sed -i -e 's/<\/data>/<\/string>/g' $3

# remove identifying info (delete file after saving
# relevant bits of scan in server.py, actually)
#sed -i -e '/<\key>DeviceName<\/key>/,+1d' $3
#sed -i -e '/<\key>MobileEquipmentIdentifier<\/key>/,+1d' $3
#sed -i -e '/<\key>MLBSerialNumber<\/key>/,+1d' $3
#sed -i -e '/<\key>SerialNumber<\/key>/,+1d' $3
#sed -i -e '/<\key>UniqueChipID<\/key>/,+1d' $3
#sed -i -e '/<\key>EthernetAddress<\/key>/,+1d' $3
#sed -i -e '/<\key>DieID<\/key>/,+1d' $3
#sed -i -e '/<\key>UniqueDeviceID<\/key>/,+1d' $3

# delete this after hashing when session ends.
#sed -i -e '/<\key>InternationalMobileEquipmentIdentity<\/key>/,+1d' $3

# try to check for jailbroken by mounting the entire filesystem.
# Gets output:
# "Failed to start AFC service 'com.apple.afc2' on the device.
# This service enables access to the root filesystem of your device.
# Your device needs to be jailbroken and have the AFC2 service installed."
# if fails (so in that case not jailbroken -- or 'not sure' for false negative).
rm -rf /tmp/phonescanmnt
mkdir -p /tmp/phonescanmnt
# ifuse -u "$serial" --root /tmp/phonescanmnt &> $4

#lsof -ti tcp:2222 | xargs kill
iproxy 2222 22 & "${DIR}/ios_ssh_expect.sh" localhost
echo $? > $5
cd ..

# for consumption by python
echo $serial
