# Installing ISDi on Raspberry Pi

This guide explains how to install and run ISDi on a Raspberry Pi for scanning Android and iOS devices over USB.

## Prerequisites

1. **Raspberry Pi**: A Raspberry Pi running Raspberry Pi OS or another Debian-based distribution
2. **Powered USB connection**: Use a powered USB hub or powered USB port. The Raspberry Pi may not provide enough power for the connected device by itself.
3. **Network access**: The Raspberry Pi and the computer used for SSH should be on the same network.
4. **USB debugging**: Enable USB debugging on any Android device that will be scanned.
5. **Trust permission**: When connecting an iPhone or iPad, unlock it and tap **Trust This Computer**.

## Connecting to the Raspberry Pi

Connect to the Raspberry Pi over SSH:

```bash
ssh <username>@<device-name>.local
```

For example, if the username is `peng` and the device name is `pi4`, run:

```bash
ssh peng@pi4.local
```

## Installation

### Step 1: Install System Dependencies

Update the package list and install the required packages:

```bash
sudo apt update && sudo apt install -y python3-full python3-venv python3-pip usbmuxd openssl libusb-1.0-0-dev libimobiledevice-utils adb
```

### Step 2: Start Device Services

Start the ADB server for Android devices:

```bash
adb start-server
```

Enable and start `usbmuxd` for iOS devices:

```bash
sudo systemctl enable --now usbmuxd
```

### Step 3: Create a Python Virtual Environment

Raspberry Pi OS and Debian use the PEP 668 protection mechanism, so install ISDi inside a virtual environment:

```bash
python3 -m venv ~/isdi-venv
source ~/isdi-venv/bin/activate
```

### Step 4: Install ISDi

Upgrade `pip`, install the required `rsonlite` dependency, and install ISDi:

```bash
pip install --upgrade pip
pip install rsonlite
pip install isdi-scanner
```

## Running ISDi

Activate the virtual environment and start ISDi:

```bash
source ~/isdi-venv/bin/activate
isdi run
```

Open the web interface at:

```text
http://<raspberry-pi-ip>:6200
```

If you are using a browser directly on the Raspberry Pi, open:

```text
http://localhost:6200
```

## Verifying Device Connections

### iOS Devices

Connect and unlock the iPhone or iPad, tap **Trust This Computer**, and run:

```bash
idevice_id -l
```

If the command prints a device ID, the Raspberry Pi can detect the iOS device.

### Android Devices

Connect the Android device, enable USB debugging, and run:

```bash
adb devices
```

If an authorization prompt appears on the Android device, tap **Allow**. The command should then list the device as `device` rather than `unauthorized`.

## Known Issues and Source Fixes

The following fixes may be required for the current ISDi package.

### Issue 1: Incorrect UDID Argument in `ios_scan.sh`

The script may combine the `--udid` option and its value into one shell argument:

```text
'--udid 00008130-001E1D192021401C'
```

However, `pymobiledevice3` expects them as two separate arguments:

```text
--udid 00008130-001E1D192021401C
```

Open `isdi/scripts/ios_scan.sh` and make the following changes.

Replace:

```bash
serial="--udid $1"
```

with:

```bash
udid="$1"
```

Replace:

```bash
printf "Serial: %s\n" "$serial"
```

with:

```bash
printf "UDID: %s\n" "$udid"
```

Update the `apps` and `devinfo` commands to pass the option and value separately:

```bash
"apps": $(${idb} apps list --udid "$udid"),
"devinfo": $(${idb} lockdown info --udid "$udid")
```

If ISDi previously generated an empty iOS dump, remove or rename that cached dump before scanning again so the corrected commands can run.

### Issue 2: Application Database Initialization Failure

The original `app-info.db` download location may be unavailable. If ISDi cannot initialize its application database, edit `isdi/scanner/__init__.py`.

Replace the `_init_db` method with:

```python
def _init_db(self) -> None:
    """Initialize SQLite connection for app info database."""
    try:
        db_path = str(cfg.database_path)
        AppScanner.app_info_conn = sqlite3.connect(
            db_path, check_same_thread=False
        )
    except Exception as e:
        logging.error(f"Failed to connect to database: {e}")
        AppScanner.app_info_conn = None
```

In the application lookup query, replace:

```python
cur.execute(f"SELECT * FROM apps WHERE appid IN ({placeholders})", appids)
```

with:

```python
cur.execute(f"SELECT * FROM app_info WHERE appid IN ({placeholders})", appids)
```

### Issue 3: Application Name Appears as Unknown

Some scan results may show the application name as `Unknown`. This issue is not yet resolved.

## Troubleshooting

### The Virtual Environment Is Not Active

If the `isdi` command is not found, activate the environment again:

```bash
source ~/isdi-venv/bin/activate
```

### No iOS Device Is Detected

Check the `usbmuxd` service:

```bash
sudo systemctl status usbmuxd
```

Then reconnect and unlock the device, confirm the trust prompt, and rerun:

```bash
idevice_id -l
```

### No Android Device Is Detected

Restart ADB and check the device list:

```bash
adb kill-server
adb start-server
adb devices
```

### Port 6200 Is Already in Use

Check which process is using the port:

```bash
ss -ltnp | grep 6200
```

If supported by the installed ISDi version, start the server on another port:

```bash
isdi run --port 6201
```

Then open `http://<raspberry-pi-ip>:6201`.
