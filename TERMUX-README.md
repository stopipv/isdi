# ISDI for Termux/Android - Quick Start

## ✅ Build Complete!

You now have a **91MB self-contained package** at `dist/isdi.pyz`

## Installation on Android/Termux

### 1. Transfer to Device
```bash
adb push dist/isdi.pyz /sdcard/
```

### 2. On Termux
```bash
# Install Python (only ~50MB)
pkg install python

# Move and set permissions
mv /sdcard/isdi.pyz ~/
chmod +x ~/isdi.pyz

# Run ISDI
~/isdi.pyz
```

## How It Works

- ✅ **Works with pymobiledevice3** - includes the Termux socket patchφ
- ✅ **No dependency hell** - everything bundled (91MB total)
- ✅ **Data stored externally** - writes to `~/isdi_data/` (Termux) or `~/.isdi/` (Linux)
- ✅ **Binary extensions handled** - shiv auto-extracts numpy, pandas, etc. on first run

## Usage

```bash
# Normal mode (opens browser)
~/isdi.pyz

# Test mode (no browser)
~/isdi.pyz test

# Access web UI
# Open browser to: http://127.0.0.1:6202 (test) or http://127.0.0.1:6200 (normal)
```

## Data Locations (Termux)

- App data: `~/isdi_data/`
- Reports: `~/isdi_data/reports/`
- Dumps: `~/isdi_data/dumps/`
- Database: `~/isdi_data/data/clientInfo.db`
- Logs: `~/isdi_data/logs/`

## Rebuilding

```bash
# Clean rebuild
rm -rf dist/isdi.pyz ~/.shiv ~/.isdi
./build-termux-pex.sh
```

## File Size Breakdown

- **91MB total**
  - Python packages: ~70MB (numpy, pandas, pymobiledevice3, Flask, etc.)
  - Source code: ~5MB
  - Data files: ~16MB

## Notes

- First run extracts binary extensions to `~/.shiv/` (~200MB cache)
- Subsequent runs are instant (uses cached extraction)
- On Termux, remember to use the pymobiledevice3 wrapper for iOS device access
- Android device scanning works via native `adb` (no special setup needed)

## Troubleshooting

**Problem**: "Permission denied"
```bash
chmod +x ~/isdi.pyz
```

**Problem**: "No module named..."
```bash
# Rebuild from scratch
rm -rf ~/.shiv
~/isdi.pyz
```

**Problem**: Can't connect to iOS device
```bash
# Make sure usbmuxd socket exists
ls $PREFIX/var/run/usbmuxd

# Use the pymobiledevice3 wrapper from earlier
python3 ~/pymobiledevice3-termux.py usbmux list
```

---

**Next Step**: Transfer `dist/isdi.pyz` to your Android device and test!
