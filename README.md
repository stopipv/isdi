# IPV Spyware Discovery (ISDi) Tool

Checks Android or iOS devices for apps used to surveil or track victims
("stalkerware", "spouseware", "spyware"). ISDi's technical details are included
in ["Clinical Computer Security for Victims of Intimate Partner Violence"
(USENIX 2019)](https://www.usenix.org/conference/usenixsecurity19/presentation/havron). The blacklist is based
on apps crawled in ["The Spyware Used in Intimate Partner Violence" (IEEE S&P 2018)](https://www.computer.org/csdl/pds/api/csdl/proceedings/download-article/12OmNxWuiny/pdf).

## Contribution Guidelines
For more information about contributing to ISDi, see the [contribution guidelines](contribution.md).

## Installing ISDi :computer:

Right now, ISDi currently only natively supports **macOS and Linux**. If you are using a Windows device, you can use the Windows Subsystem for Linux 2
(WSL2), which can be installed by following [these instructions](https://docs.microsoft.com/en-us/windows/wsl/wsl2-install). After this,
follow the remaining instructions as a Linux user would, cloning/running 
ISDi inside the Linux container of your choice. 

### Python dependencies
- You will need Python 3.6 or higher (check by running `python3` in your
Terminal and see what happens).  On macOS, you can get this by running the
following commands in your Terminal application: `xcode-select --install`
(installs developer tools); followed by `/usr/bin/ruby -e "$(curl -fsSL
https://raw.githubusercontent.com/Homebrew/install/master/install)"` to get
Brew (a software package manager); finally, `brew install python` to get Python
3.6+.

- Run `pip3 install -r
requirements.txt` in the base directory of this repository to get the required
Python modules.

### Operating system dependencies
On macOS you can quickly install project dependencies with Homebrew by running `brew bundle`.

- Install ADB for your operating system (via
https://developer.android.com/studio/releases/platform-tools.html). On
macOS, try `brew install --cask android-platform-tools`. On Debian-based
systems, try `sudo apt install adb`. 
**Windows via WSL2 only:** Installing adb is not so straightforward in WSL2, and
it won't work straightaway. You have to ensure having the *same* version of adb
*both* in WSL2 and in normal Windows (with `adb version`), then you will need to
start the adb process first in Windows, then in WSL2 (with for example `adb
devices`).

- Install `expect`. On macOS, run `brew install expect`. On Debian-based
  systems, run `sudo apt install expect`.

- Install `libimobiledevice`. On macOS, run `brew install libimobiledevice`.

- Install `ideviceinstaller`. On macOS, run `brew install ideviceinstaller`.

- Install `ifuse` (via https://github.com/libimobiledevice/ifuse). On macOS, run:
`brew install autoconf`
`brew install automake`
`brew install libtool`
`brew install --cask macfuse`
`cd ifuse`
`./autogen.sh`
`make`
`sudo make install`

- **Linux/WSL2 only:** If you are running Linux or WSL2, install
   [patchelf](https://nixos.org/patchelf.html) (on Debian-based systems, this
can be done like `sudo apt install patchelf`) and then run
`./scripts/patch_ios_dylibs.sh`. You may need to re-run this script if you are
collaborating and other ISDi users overwrite the iOS binaries with their own 
absolute shared object paths. [More details here (including for macOS users)](notes.md).


## Running ISDi

After ISDi is installed, with an Android or iOS
device plugged in and unlocked, run the following command in the terminal (in
the base directory of this repository)

```$ ./isdi ```

Then navigate to `http://localhost:5000` in the browser of your choice. You will see ISDi running as a web app. Click on `"Scan Instructions"` and follow 
the instructions to prepare your device for the scan.

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

## Consultation form data 
ISDi is intended to be used by advocates for victims of intimate partner violence in 
a [clinical setting](http://www.nixdell.com/papers/2019-usenix_clinical_security_FULL.pdf); 
you can add detailed notes about a victim's tech abuse situation 
by clicking `"Start Consult Form"` on ISDi's homepage. The results
will be saved in `data/fieldstudy.db` and can be viewed/edited
by navigating to `/form/edit`.

Some consult form data may not be relevant for use in
other organizations (e.g., the meeting location being 
in a borough of New York City). Please consider adapting the form 
for your needs. One can do this by modifying the `Client` class in 
`isdi` and use `sa.create_all()` (`sa` is obtained by wrapping SQLAlchemy over 
the Flask app) to obtain the new
schema. Then place the new schema in `schema.sql` by updating the `clients_notes` table.

## Debugging tips 
If you encounter errors, please file a [GitHub issue](../../issues/) with the server error output. 
Pull requests are welcome. 

#### Android tips 
In the terminal of the computer, run `adb devices` to see if
the device is connected properly.


#### iOS tips 
In the terminal of the computer (in the base directory of this repository), 
run `./static_data/libimobiledevice-darwin/idevice_id -l` to see if
the device is connected properly (replace `darwin` with `linux` if your system is Linux.)

#### Cast iOS Screens or Mirror Android Screens 
It is possible to view your
device screen(s) in real time on the macOS computer in a new window. This may
be useful to have while you are running the scan (and especially if you use the
privacy checkup feature), as it will be easy for you to see the mobile device
screen(s) in real time on the Mac side-by-side with the scanner.

**How to do it:** 
you can mirror Android device screens in a new window using
[scrcpy](https://github.com/Genymobile/scrcpy), and cast iOS device screens on
macOS with QuickTime 10 (launch it and click File --> New Movie Recording -->
(on dropdown by red button) the iPhone/iPad name).

## Downloaded data ## 
The data downloaded and stored in the study are the
following.  1. A `sqlite` database containing the feedback and actions taken by
the user.  2. `phone_dump/` folder will have dump of some services in the
phone.  (For Android I have figured out what are these, for iOS I don't know
how to get those information.)

##### Android 
The services that we can dump safely using `dumpsys` are the
following.
* Application static details: `package` Sensor and configuration info:
* `location`, `media.camera`, `netpolicy`, `mount` Resource information:
* `cpuinfo`, `dbinfo`, `meminfo` Resource consumption: `procstats`,
* `batterystats`, `netstats`, `usagestats` App running information: `activity`,
* `appops`

See details about the services in [notes.md](notes.md)

##### iOS 
Only the `appIds`, and their names. Also, I got "permissions" granted
to the application. I don't know how to get install date, resource usage, etc.
(Any help will be greatly welcomed.)


## Code structure  
* `phone_scanner.py` has all the logic required to communicate with Android and
  iOS devices.
* `parse_dump.py` has all of the logic required to extract dumped info from the
 devices. After the initial scan, the server will rely on this parser rather
 than needing an active connection to the device (work in progress). For now,
 please keep your device plugged in when looking at scan results.  
* `isdi` is the Flask web server and the application's main entry point.
* `templates/` folder contains the html templates rendering in the UI 
* `webstatic/` folder contains the `.css` and `.js` files
* `phone_dumps/` folder will contain the data recorded from the phone (as well as in 
`data/fieldstudy.db`.



## TODO 1.
https://docs.google.com/document/d/1fy6RTo9Gc0rBUBHAhKfSmqI99PSPCBsAdEUIbpGIkzQ/edit
2. ~How to figure out off-store apps in Android and iOS? Check the installer in
`adb shell pm packages -i`~ 3. For iOS, how to find out app installation dates,
resource usage, etc?  4. Explore viability of
[WebUSB](https://github.com/WICG/webusb) and
[WebADB](https://github.com/webadb/webadb.js).

See [notes.md](notes.md) for other developer helps.
