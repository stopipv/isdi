# Installing ISDi on Termux/Android

This guide walks you through installing and running ISDi directly on an Android device using [Termux](https://termux.dev/).

## What is Termux?

Termux is a Linux terminal emulator and environment for Android. It allows you to run Linux tools and Python applications on your Android device without rooting.

## Prerequisites

1. **Android Device**: Android 5.0+
2. **Termux App**: Install from [F-Droid](https://f-droid.org/packages/com.termux/) or the Termux GitHub releases. Do not use the Google Play version because it is outdated.
3. **USB Debugging**: Enabled on the device being scanned (Settings → Developer Options)
4. **USB Cable or OTG Adapter**: For connecting the scanned device to the Android device running Termux

## Installation

### Step 1: Install Termux Dependencies

Open Termux and run:

```bash
pkg update -y && pkg upgrade -y
pkg install -y python git build-essential libusb usbmuxd rust clang cmake pkg-config libffi openssl android-tools
```

Installing `pymobiledevice3` on Android is more involved because some dependencies may need to be compiled locally.

```bash
export ANDROID_API_LEVEL="$(getprop ro.build.version.sdk)"
echo "$ANDROID_API_LEVEL"
```

If you want to persist that setting for future Termux sessions, add it to your shell profile manually.

### Step 2: Install ISDI
Install some dependencies first to reduce the amount of local compilation:

```bash
pip install --extra-index-url https://termux-user-repository.github.io/pypi/ qh3 zeroconf pydantic-core gpxpy psutil pyyaml markupsafe hexdump
pip install isdi-scanner --prefer-binary
```

Keeping the phone screen on during installation can help prevent Android from pausing Termux while packages are compiling. The installation can take a while, so keep the device charged.

**First Run:** The app-info.db database (~47MB) will be automatically downloaded from GitHub on first run. This may take a minute depending on your connection.

## Running ISDi on Termux
```bash
$ isdi run
```

Then access the web UI at `http://localhost:6200` from your browser.

## Scanning Devices from Termux

### Scanning Android Devices

1. **Connect Android device** via USB cable
2. **Enable USB Debugging** on the connected device
3. **Click "Request USB Access"** in the web UI
4. **Allow access** when prompted on the connected device
5. **Click \"Android\" button** in ISDI web UI
6. **Results will appear** after scan completes

### Scanning iOS Devices

iOS scanning from Termux requires:

1. **USB connection** to the Termux device
2. **Usbmux socket setup** (automated by ISDI via pmd3_wrapper)

```bash
# ISDI automatically handles iOS connection setup
isdi run
# Click "iOS" button in web UI
```

## Troubleshooting

### USB Connection Issues

If devices aren't detected:

```bash
# Check ADB connection
adb devices

# On some devices, you may need:
termux-usb -r -E -e "usbmuxd -f -v" <device-path>
```

### Permission Denied Errors

Some Termux operations require:

```bash
# Grant Termux storage access
$ termux-setup-storage
```

### Port Already in Use

If port 6200 is in use:

```bash
# Check what's using the port
ss -ltnp | grep 6200

# Or use a different port
isdi run --port 6201
# Then access http://localhost:6201
```

## Performance Notes

- **First run**: Slower (database initialization)
- **Subsequent runs**: Faster (uses cached data)
- **Scans**: Take 30-60 seconds per device (depends on app count)
- **Memory**: ISDi uses ~200-400 MB RAM


