# Installing ISDi on Termux/Android

This guide walks you through installing and running ISDi directly on an Android device using [Termux](https://termux.dev/).

## What is Termux?

Termux is a Linux terminal emulator and environment for Android. It allows you to run Linux tools and Python applications on your Android device without rooting.

## Prerequisites

1. **Android Device**: Android 5.0+
2. **Termux App**: Install from [F-Droid](https://f-droid.org/packages/com.termux/) or [Google Play](https://play.google.com/store/apps/details?id=com.termux)
3. **USB Debugging**: Enabled on the device being scanned (Settings → Developer Options)
4. **USB Cable**: For connecting Android device to the device running Termux scans

## Installation

### Step 1: Install Termux Dependencies

Open Termux and run:

```bash
pkg update
pkg install python git build-essential libusb \
	python-cryptography python-pillow usbmux libusb-1.0-dev
```

**Note:** Native/compiled Python modules must be installed via `pkg` on Termux.
If a package is not available in Termux, let `pip` install it instead.

### Step 2: Clone ISDI Repository

```bash
git clone https://github.com/rchatterjee/isdi.git
cd isdi
```

### Step 3: Install ISDI

```bash
pip install -e .
```

This installs ISDI in development mode, making it editable for customization.

**First Run:** The app-info.db database (~47MB) will be automatically downloaded from GitHub on first run. This may take a minute depending on your connection.

## Running ISDi on Termux

### Using pip (Recommended)

After `pip install -e .`, simply run:

```bash
isdi run
```

Then access the web UI at `http://localhost:6200` from your browser.

## Scanning Devices from Termux

### Scanning Android Devices

1. **Connect Android device** via USB cable
2. **Enable USB Debugging** on the connected device
3. **Allow access** when prompted on the connected device
4. **Click "Android" button** in ISDI web UI
5. **Results will appear** after scan completes

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

### Python/Module Errors

If you get `ModuleNotFoundError` after installation:

```bash
# Reinstall in development mode
pip install --force-reinstall -e .

# OR use the .pyz archive instead
python3 dist/isdi.pyz run
```

### Native Python Modules on Termux

On Termux, install native/compiled modules using `pkg` (not `pip`).
Common ones needed for ISDI and dependencies:

```bash
pkg install python-cryptography python-pillow
```

If a module is not available in Termux (for example, `qh3`), allow `pip` to install it.
# Also try:
pip install -e .
```

### Permission Denied Errors

Some Termux operations require:

```bash
# Grant Termux storage access
termux-setup-storage
```

### Port Already in Use

If port 6200 is in use:

```bash
# Check what's using the port
lsof -i :6200

# Or use a different port via environment variable
FLASK_PORT=6201 isdi run
# Then access http://localhost:6201
```

## Performance Notes

- **First run**: Slower (database initialization)
- **Subsequent runs**: Faster (uses cached data)
- **Scans**: Take 30-60 seconds per device (depends on app count)
- **Memory**: ISDi uses ~200-400 MB RAM

## Building a Portable .pyz for Other Termux Devices

If you want to share the `.pyz` with another Termux device:

```bash
# On the build device (native ARM64):
./build-termux-pex.sh

# Transfer the .pyz to another Termux device:
adb push dist/isdi.pyz /sdcard/
# Then on the target device:
mv /sdcard/isdi.pyz ~/isdi.pyz
python3 ~/isdi.pyz run
```

## Next Steps

- [Main README](README.md) - For overview and general usage
- [BUILD-GUIDE.md](BUILD-GUIDE.md) - For detailed build options
- [Contributing](contribution.md) - To contribute to ISDI

## Support

For issues specific to Termux, check:
- [Termux Wiki](https://wiki.termux.com/)
- [ISDI GitHub Issues](../../issues/)
