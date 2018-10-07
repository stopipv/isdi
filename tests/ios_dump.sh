#!/bin/bash
# gets all of the details about each app (basically what ios_deploy does but with extra fields)
ideviceinstaller -l -o xml -o list_all > iphone_plist.xml
# use with installer_parse.py

# gets OS version, serial, etc. -x for xml. Raw is easy to parse, too.
ideviceinfo -x

# try to check for jailbroken by mounting the entire filesystem. 
# Gets output:
# "Failed to start AFC service 'com.apple.afc2' on the device.
# This service enables access to the root filesystem of your device.
# Your device needs to be jailbroken and have the AFC2 service installed."
# if fails (so in that case not jailbroken -- or 'not sure' for false negative).
mkdir /tmp/mnt
ifuse --root /tmp/mnt
