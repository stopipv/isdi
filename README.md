# IPV Spyware Discovery (ISDi) Tool

Checks Android or iOS devices for apps used to surveil or track victims
("stalkerware", "spouseware", "spyware"). ISDi's technical details are included
in ["Clinical Computer Security for Victims of Intimate Partner Violence"
(USENIX 2019)](https://havron.dev/pubs/clinicalsec.pdf).


## How can I install ISDi?

Right now, ISDi currently only supports **macOS and Linux**. If you are using a
Windows device, it will probably be sufficient to install 
[WSL2](https://docs.microsoft.com/en-us/windows/wsl/wsl2-install)
and then follow the remaining instructions as a Linux user would, cloning/running 
ISDi inside the Linux container of your choice. If it works, let us know!

0. You will need Python 3.6 or higher. On macOS, you can get this by
running the following commands in your Terminal application: `xcode-select
--install` (installs developer tools); followed by `/usr/bin/ruby -e "$(curl
-fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"` to
get Brew (a software package manager); finally, `brew install python` to get Python
3.6+.

1. Run `pip3 install -r
requirements.txt` in the base directory of this repository to get the required
Python modules.

2. Install ADB for your operating system (via
https://developer.android.com/studio/releases/platform-tools.html). On
Macintosh, try `brew cask install android-platform-tools`. On Debian-based
systems, try `sudo apt install adb`.

3. Contact the authors (<havron@cs.cornell.edu> or <rahul@cs.cornell.edu>) with
a legitimate request for the blacklist ISDi requires to run.  We will provide
`static_data.zip`, which should be unzipped and replacing the public facing
`static_data` directory in this repository.

## How can I run ISDi?

After [dependencies](#dependencies) are installed, with an Android or iOS
device plugged in and unlocked, run the following command in the terminal (in
the base directory of this repository)

```bash $ bash run.sh ```

Navigate to `http://localhost:5000` on a browser (or `http://localhost:5002` if
in test mode). You will see the page of the ISDi tool running. 

It should look something like this:

![Phone Scanner UI before scan](webstatic/ISDi_before_scan.png "Phone Scanner
UI before scan")

Connect a device and click on the suitable button `Android` or `iOS`. Give it a
nickname and click "Scan now". (**Please connect one device at a time.**) It
will take a few seconds for the scan to complete. We are working to have all
scan results done at once on Android, but for the time being please leave the
device plugged in when clicking on apps on the scan results table.

After the scan, the UI will look something like this:

![Phone Scanner UI after scan](webstatic/ISDi_after_scan.png "Phone Scanner
UI")

## Consultation form data Some consult form data may not be relevant for use in
other organizations.  Please consider adapting it for your needs (modify the
`Client` class in `server.py` and use `sa.create_all()` to obtain the new
schema. Place the new schema in `schema.sql`.

## Debugging tips If there are errors, please send your server error output to
<havron@cs.cornell.edu>. If you feel confident enough in the codebase to try to
fix them yourself, do so, but don't push to this repo until emailing Sam.
Inspect apps on the device manually if you cannot resolve a failure.


#### Android tips In the terminal of the computer, run `adb devices` to see if
the device is connected properly.


#### iOS tips In the terminal of the computer, run `idevice_id -l` to see if
the device is connected properly.


#### Prepare the mobile device for scanning **Android** (also see
`localhost:5000/instruction` for more details step-by-step.) 1. You will need
to activate [`developer
options`](https://developer.android.com/studio/debug/dev-options.html) in the
phone. Follow the above link to activate the developer option.  **TODO**: how
to hide it back after the scan.  `$ adb shell pm clear com.android.setting`
cleans the data for  many (if not most) Android, but not all.  Some might need
manual cleaning of the settings data by going `Setting -> Apps -> "Settings" ->
Data -> Clear data`.

2. Connect the phone to the laptop using USB. If `PhoneScanner` is running, try
refreshing the page, and see if the phone ask for "Do you trust this computer?"
(or similar) message.  3. Do the scan.  If `PhoneScanner` does not identify the
device (that is no device enlisted under `Android` group on the left of the
page), disconnect the USB cable from the phone, reconnect, and refresh the
page.  4. The scanner will automatically reset the developer option. Restart
the phone to get to original state.  If you still see the developer options
(a.k.a, `developer mode`) is on, open `Settings -> Apps`, you will see list of
apps installed in your device.  Find `Settings` app in the list, tap on it, and
tap `clear data` (sometimes listed inside `Storage`).


**iOS**

There is not much preparation required for iOS. Once the USB cable is
connected, refresh the page; on the device you have to enter the passcode to
unlock the device, and then once more to accept the "trust this computer"
dialog.  Even if you use touchID, passcode is required to enable the USB
access. If you don't see the device, refresh the page a couple of times, and
check the phone if it went to "Enter passcode" mode and the "trust this
computer" dialog.


## Cast iOS Screens or Mirror Android Screens It is possible to view your
device screen(s) in real time on the macOS computer in a new window. This may
be useful to have while you are running the scan (and especially if you use the
privacy checkup feature), as it will be easy for you to see the mobile device
screen(s) in real time on the Mac side-by-side with the scanner.

**"Mirroring" vs "Casting":** Mirroring Android devices allows you to not only
view the mobile device’s screen, but also maneuver the screen directly with
your mouse and even use your keyboard to input to the Android device. Casting
iOS devices only allows you to view the device screen -- the iOS device itself
must be maneuvered by hand.

**How to do it:** you can mirror Android device screens in a new window using
[scrcpy](https://github.com/Genymobile/scrcpy), and cast iOS device screens on
macOS with QuickTime 10 (launch it and click File --> New Movie Recording -->
(on dropdown by red button) the iPhone/iPad name).

## Downloaded data ## The data downloaded and stored in the study are the
following.  1. A `sqlite` database containing the feedback and actions taken by
the user.  2. `phone_dump/` folder will have dump of some services in the
phone.  (For Android I have figured out what are these, for iOS I don't know
how to get those information.)

##### Android The services that we can dump safely using `dumpsys` are the
following.
* Application static details: `package` Sensor and configuration info:
* `location`, `media.camera`, `netpolicy`, `mount` Resource information:
* `cpuinfo`, `dbinfo`, `meminfo` Resource consumption: `procstats`,
* `batterystats`, `netstats`, `usagestats` App running information: `activity`,
* `appops`

See details about the services in [notes.md](notes.md)

##### iOS Only the `appIds`, and their names. Also, I got "permissions" granted
to the application. I don't know how to get install date, resource usage, etc.
(Any help will be greatly welcomed.)


## Code structure  
* `phone_scanner.py` has all the logic required to communicate with Android and
  iOS devices.
* `parse_dump.py` has all of the logic required to extract dumped info from the
* devices. After the initial scan, the server will rely on this parser rather
* than needing an active connection to the device (work in progress). For now,
* please keep your device plugged in when looking at scan results.  `server.py`
* is the Flask web server.  `templates/` folder contains the html templates
* rendering in the UI `webstatic/` folder contains the `.css` and `.js` files
* `phone_dumps/` folder will contain the data recorded from the phone.



## TODO 1.
https://docs.google.com/document/d/1fy6RTo9Gc0rBUBHAhKfSmqI99PSPCBsAdEUIbpGIkzQ/edit
2. ~How to figure out off-store apps in Android and iOS? Check the installer in
`adb shell pm packages -i`~ 3. For iOS, how to find out app installation dates,
resource usage, etc?  4. Explore viability of
[WebUSB](https://github.com/WICG/webusb) and
[WebADB](https://github.com/webadb/webadb.js).

See [notes.md](notes.md) for other developer helps.



