# IPV Spyware Discovery (ISDi) Tool

ISDi tool checks Android or iOS devices for apps that can be used for surveillaince
(a.k.a "stalkerware", "spouseware", "spyware" apps). ISDi's technical details are included
in ["Clinical Computer Security for Victims of Intimate Partner Violence"
(USENIX 2019)](https://www.usenix.org/conference/usenixsecurity19/presentation/havron). The blacklist is based
on apps crawled in ["The Spyware Used in Intimate Partner Violence" (IEEE S&P 2018)](https://www.computer.org/csdl/pds/api/csdl/proceedings/download-article/12OmNxWuiny/pdf).

[![ISDI_Linter](https://github.com/stopipv/isdi/actions/workflows/super-linter.yml/badge.svg)](https://github.com/stopipv/isdi/actions/workflows/super-linter.yml)
[![Sync with IOC stalkerware indicators](https://github.com/stopipv/isdi/actions/workflows/get-stalkerware-indicators.yml/badge.svg)](https://github.com/stopipv/isdi/actions/workflows/get-stalkerware-indicators.yml)

## Contribution Guidelines
For more information about contributing to ISDi, see the [contribution guidelines](https://github.com/stopipv/isdi/blob/main/contribution.md).


## Installing ISDi :computer:

ISDi currently supports **macOS, Linux, and Termux/Android**. If you are using a Windows device, you can use the Windows Subsystem for Linux 2
(WSL2), which can be installed by following [these instructions](https://docs.microsoft.com/en-us/windows/wsl/wsl2-install). After this,
follow the remaining instructions as a Linux user would.

### System Requirements

#### Python
- Python 3.8 or higher is required
- Check your version: `python3 --version`
- On macOS, install via: `brew install python`
- On Linux (Debian/Ubuntu): `sudo apt install python3 python3-pip`

#### Operating System Dependencies
ISDi needs `adb` for scanning Android devices and `pymobiledevice3` for scanning iOS devices. 

**macOS:**
```bash
brew bundle
# Or manually:
brew install --cask android-platform-tools
```

For iOS device support on macOS, `pymobiledevice3` will be installed automatically with ISDi. For Android device support, ensure `adb` (Android Debug Bridge) is installed via the android-platform-tools above.

**Linux (Debian/Ubuntu):**
```bash
sudo apt install adb
```

For iOS device support on Linux, `pymobiledevice3` will be installed automatically with ISDi. For Android device support, ensure `adb` is installed via the command above.

**Windows Subsystem Linux (v2):**
- Install `adb` and `pymobiledevice3` in Windows and ensure it's in PATH. Do not install them in WSL2, as WSL cannot have access to USB devices. Verify the installation by running `adb.exe` and `pymobiledevice3.exe` in a command prompt terminal. 


**Termux/Android:**
See [TERMUX_INSTALL.md](https://github.com/stopipv/isdi/blob/main/TERMUX_INSTALL.md) for Android device setup.

### Option 1: Install via pip (Recommended)

The easiest way to install ISDi is via pip:

```bash
pip install isdi-scanner
```

### Option 2: Install from Source (Development)

Clone the repository and install in development mode:

```bash
git clone https://github.com/stopipv/isdi.git
cd isdi
pip install -e .
``` 

## Running ISDi

After ISDi is installed, with an Android or iOS device plugged in and unlocked, run:

```bash
isdi run
```

ISDi will start a local web server on port 6200. Open your browser to `http://localhost:6200` for the ISDi UI. In debug mode, the server is on port 6202. 

**Note:** On first run, ISDi will download the app information database (~47MB) from GitHub. This may take a minute depending on your internet connection. An internet connection is required for the first run.

### Command Options

```bash
isdi run              # Normal mode
isdi run --debug      # Debug mode (verbose logging)
DEBUG=1 isdi run      # Alternative debug flag
isdi --help           # Show all options
```

Then navigate to the URL shown in the terminal. Click on `"Scan Instructions"` and follow the instructions to prepare your device for the scan.

It should look something like this:

![Phone Scanner UI before scan](https://github.com/stopipv/isdi/blob/main/webstatic/ISDi_before_scan.png "Phone Scanner
UI before scan")

Connect a device and click on the suitable button `Android` or `iOS`. Give it a
nickname and click "Scan now". (**Please connect one device at a time.**) It
will take a few seconds for the scan to complete. We are working to have all
scan results done at once on Android, but for the time being please leave the
device plugged in when clicking on apps on the scan results table.

After the scan, the UI will look something like this:

![Phone Scanner UI after scan](https://github.com/stopipv/isdi/blob/main/webstatic/ISDi_after_scan.png "Phone Scanner
UI")


## Debugging Tips

### Android
Check device connection:
```bash
adb devices
```

### iOS  
Check device connection:
```bash
pymobiledevice3 usbmux list
```

### General
- Run ISDi with `--debug` flag for verbose logging
- Check logs in `~/.local/share/isdi/logs/`
- File issues on [GitHub](https://github.com/stopipv/isdi/issues/) with error messages

### Termux/Android
See [TERMUX_INSTALL.md](https://github.com/stopipv/isdi/blob/main/TERMUX_INSTALL.md) for Termux-specific troubleshooting.

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

See details about the services in [notes.md](https://github.com/stopipv/isdi/blob/main/notes.md)

##### iOS 
Only the `appIds`, and their names. Also, I got "permissions" granted
to the application. I don't know how to get install date, resource usage, etc.
(Any help will be greatly welcomed.)


## Code Structure  

- **`src/isdi/scanner/`** - Core scanning logic
  - `parse_dump.py` - Parses device dumps (Android/iOS)
  - `android_permissions.py` - Android permission analysis
  - `privacy_scan_android.py` - Android privacy scanning
  - `blocklist.py` - Stalkerware/spyware blocklist management
  - `lightweight_df.py` - CSV/data processing (pandas-free)
  - `db.py` - SQLite database operations
  - `pmd3_wrapper.py` - Termux-compatible pymobiledevice3 wrapper

- **`src/isdi/web/`** - Flask web application
  - `templates/` - HTML templates for the web UI
  - `static/` - CSS, JavaScript, and images
  - `schema.sql` - Database schema (embedded in code)
  - `forms/` - WTForms for consultation forms
  - `model/` - SQLAlchemy models
  - `view/` - Flask route handlers

- **`src/isdi/scripts/`** - Shell scripts for device interaction
  - `android_scan.sh` - Android device scanning
  - `ios_scan.sh` - iOS device scanning

- **`src/isdi/data/`** - Static data and reference files
  - `app-flags.csv` - App classification metadata
  - `app-info.db` - Cached app information
  - `android_permissions.csv` - Android permission database
  - `ios_permissions.json` - iOS permission database



See [notes.md](https://github.com/stopipv/isdi/blob/main/notes.md) for other developer helps.
