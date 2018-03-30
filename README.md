# Phone Scanner
Simple tool to check Android or iOS phones for IPS-spyware.


## Use the tool
After [dependencies](#dependencies) are installed, with an Android or iOS device plugged in and
unlocked, run the following command in the terminal

```bash
$ ./run.sh
```
Navigate to `http://localhost:5000`, on the Google Chrome browser, you will
see the page of the `PhoneScanner` tool running.
If any device is connected, it will show in the left list,
click on the device id for scanning it. **Please connect one device at a time.**


#### Prepare the phone for scanning
**Android**
1. You will need to activate [`developer options`](https://developer.android.com/studio/debug/dev-options.html)
in the phone. Follow the above link to activate the developer option.
**TODO**: how to hide it back after the scan.
2. Connect the phone to the laptop using USB. If `PhoneScanner` is running, try
refreshing the page, and see if the phone ask for "Do you trust this computer?" (or similar)
message.
3. Do the scan.  If `PhoneScanner` does not identify the device (that is
no device enlisted under `Android` group on the left of the page),
disconnect the USB cabel from the phone, reconnect, and refresh the page.
4. The scanner will automatically reset the developer option. Restart the phone
to get to original state.
If you still see the developer optinos (a.k.a, `dveloper mode`) is on, open
`Settings -> Apps`, you will see list of apps installed in your device.
Find `Settings` app in the list, tap on it, and tap `clear data` (some times
listed inside `Storage`).


**iOS**

There is not much preparation required for iOS. Once the USB
cabel is connected, refresh the page; on the device you have to enter
the passcode to unlock the device. Even if you use touchID, passcode is
required to enable the USB access. If you don't see the device, refresh
the page couple of times, and check the phone if it went to
"Enter passcode" mode.




## Downloaded data ##
The data downloaded and stored in the study are the following.
1. A `sqlite` database containing the feed back and actions taken by the user.
2. `phone_dump/` folder will have dump of some services in the phone.
(For Android I have figured out what are these, for Ios I don't know how to get those information.)

##### Android
The services that we can dump safely using `dumpsys` are the following.
* Application static details: `package`
* Sensor and configuration info: `location`, `media.camera`, `netpolicy`, `mount`
* Resource information: `cpuinfo`, `dbinfo`, `meminfo`
* Resource consumption: `procstats`, `batterystats`, `netstats`, `usagestats`
* App running information: `activity`, `appops`

See a details about the services in [notes.md](notes.md)

##### iOS
Only the `appIds`, and their names. Also, I got "permissions" granted to the
application. I don't konw how to get install date, resource usage, etc.
(Any help will be greatly welcomed.)


## Code struture  
* `phone_scanner.py` has all the logic rquired to communicate with Android and
  iOS phones.
* `server.py` is the flask server. 
* `templates/` folder contains the html templates rendering in the UI
* `static/` folder contains the `.css` and `.js` files 
* `phone_dumps/` folder will contain the data recorded from the phone.

## Dependencies
Need `python3.6+`, `xcode`, and `brew` installed in a Mac running OSX 10.9+.
Run `pip3 install -r requirements.txt` to get the required Python modules.

To scan Android and iOS we need third party software, as given below.
#### Dependencies (iOS)
Must be using a computer running macOS. We are using [`ios-deploy`](https://github.com/rchatterjee/ios-deploy
for accessing ios devices via USB. The tool is added as submodule to this project.
If after so do `git clone <url> --recursive`, or (if you have already cloned),
`git submodules update --init`.The command
`run.sh` automatically compiles `ios-deploy` too.

#### Dependencies (Android)
Install the Android Debug Bridge (`adb`).  Download [adb from
here](https://androidsdkoffline.blogspot.com/p/android-sdk-platform-tools.html)
(for correct platform), unzip it in the folder and set `ANDROID_HOME`
environment variable to the location of the unzipped folder.
If you run `run.sh`, it will be automatically set.
See [below prepare the phone for scanning](#prepare-the-phone-for-scanning).

In the terminal of the computer, run `adb devices` to see if the device is connected properly.


## TODO
1. https://docs.google.com/document/d/1fy6RTo9Gc0rBUBHAhKfSmqI99PSPCBsAdEUIbpGIkzQ/edit
2. How to figure out off-store apps in Android and iOS?
3. For iOS, how to find out app installation dates, resource usage, etc?


See [notes.md](notes.md) for other developer helps.
