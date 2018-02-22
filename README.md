# Phone Scanner (OCDV Demo)


## Code struture


## Python tool Dependencies
Run `pip3 install -r requirements.txt` to get the `appJar` (gui) and `pandas`
modules.


## Dependencies 
Need `xcode` and `brew` installed in Mac.

### Dependencies (iOS)
Must be using a computer running macOS:
`brew install mobiledevice` on the Mac (or build from
https://github.com/imkira/mobiledevice).
Keep the phone unlocked and "trust this computer" when prompted.


### Dependencies (Android)
Install the Android Debug Bridge (`adb`). Enable developer mode 
on the target android phone, and "Enable USB Debugging". 
Keep the phone unlocked and "allow debugging" from host when prompted.
Run `adb kill-server && sudo adb start-server` with phone plugged in and
unlocked.

Run `adb devices` to see if the device is connected properly.

You will need to activate [`developer
options`](https://developer.android.com/studio/debug/dev-options.html) in the
phone. Follow the above link to activate the developer option. TODO: how to hide
it back after the scan.



## Use the tool
After dependencies are installed, with an android or iOS device plugged in and
unlocked, run the following command in the terminal

```bash
$ python3 phone_scanner.py
``` 
and click on the type of device you have connected.  


## TODO
https://docs.google.com/document/d/1fy6RTo9Gc0rBUBHAhKfSmqI99PSPCBsAdEUIbpGIkzQ/edit
