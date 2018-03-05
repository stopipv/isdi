# Phone Scanner (OCDV Demo)


## Code struture  
* `phone_scanner.py` has all the logic rquired to communicate with Android and
  iOS phones.
* `server.py` is the flask server. 
* `templates/` folder contains the html templates rendering in the UI
* `static/` folder contains the `.css` and `.js` files 
* `phone_dumps` folder will contain the data recorded from the phone. 

## Python tool Dependencies
Run `pip3 install -r requirements.txt` to get the required modules.


## Dependencies 
Need `xcode` and `brew` installed in Mac.

### Dependencies (iOS)
Must be using a computer running macOS:
`brew install mobiledevice` on the Mac (or build from
https://github.com/imkira/mobiledevice).
Keep the phone unlocked and "trust this computer" when prompted.

iOS devices can be accessed from Linux using `ideviceinstaller` (Mainted by
Ubuntu developers).  Needs some dependencies that are not specified in the
file. Possibly `libusbmuxd-dev`. (I have to check). 



### Dependencies (Android)
* Install the Android Debug Bridge (`adb`). 
  Download [adb from here](https://androidsdkoffline.blogspot.com/p/android-sdk-platform-tools.html)
  (for correct platform) unzip it in the folder and add it to PATH. 
* Enable developer mode on the target android phone, and "Enable USB Debugging".
* Keep the phone unlocked and "allow debugging" from host when prompted.  
* Run `adb kill-server && sudo adb start-server` with phone plugged in and
  unlocked.

In the terminal of the computer, run `adb devices` to see if the device is connected properly.

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


## Downloaded data ##
The data downloaded and stored in the study are the following. 
1. A `sqlite` database containing the feed back and actions taken by the user. 
2. `phone_dump` folder will have dump of some services in the phone. (For Android I have figured out what are these, for Ios I don't know how to get those information.)

The services that we can dump safely using `dumpsys` are the following.
* activity
* appops
* cpuinfo: (CPU usage info of apps)
* graphicsstats: (stats about use of graphics info of apps)
* location (which apps and how often using location services)
* camera
* meminfo
* notification (what notifications are being shown or was shown. PII?)
* package (MUST)
* window (??)
* procstats and procinfo (Process stats, but not sure how useful)
* usagestats
    
Other interesting services, but may have PII
* backup: (where the account backing up the data)
* batterystats: (which app is using how much of battery)
* content: (have data about syncing, which app is syncing what, how frequently)
* user

I don't know following services:
* country_detector??
* lock_settings:

Definitely has PII
* account, user
* trust

## TODO
1. https://docs.google.com/document/d/1fy6RTo9Gc0rBUBHAhKfSmqI99PSPCBsAdEUIbpGIkzQ/edit
2. How to figure out off-store apps


## Warnings  
~2. I (Rahul) was deciding ~decided~ to dump the whole system information of the device. `adb
shell dumpsys`. This might contain PII, so the data need to be cleaned before
further processing.~




## Android ADB helps
1. `adb shell settings list [global|system|secure]` Gives a details of system settings. 
2. `pm clear com.android.settings` might remove the developer settings. Need to check.
3. `pm dump <appid>` will output a huge dump of information, which might be useful. For example, we can get the installt time, 
   `firstInstallTime=2018-02-23 19:46:51` and the `installerPackageName` from this dump. 
4. TODO: How to find whether an app is installed outside play store?

