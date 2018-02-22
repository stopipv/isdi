# Phone Scanner (OCDV Demo)

## Python tool Dependencies
Run `pip3 install -r requirements.txt` to get the `appJar` (gui) and `pandas`
modules.

## Dependencies (iOS)
Must be using a computer running macOS:
`brew install mobiledevice` on the Mac (or build from
https://github.com/imkira/mobiledevice).
Keep the phone unlocked and "trust this computer" when prompted.

## Dependencies (Android)
Install the Android Debug Bridge (`adb`). Enable developer mode 
on the target android phone, and "Enable USB Debugging". 
Keep the phone unlocked and "allow debugging" from host when prompted.
Run `adb kill-server && sudo adb start-server` with phone plugged in and
unlocked.

Run `adb devices` to see if the device is connected properly.

## TODO
https://docs.google.com/document/d/1fy6RTo9Gc0rBUBHAhKfSmqI99PSPCBsAdEUIbpGIkzQ/edit
