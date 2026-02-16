#!/bin/bash
# Build a self-contained executable for Termux/Android using Shiv
# Run this on your Linux machine, then transfer to Android

set -e

echo "Building isdi for Termux/Android..."

# Save original directory
ORIG_DIR="$(pwd)"

# Install buildtools
pip install --break-system-packages -q shiv 2>/dev/null || pip install -q shiv 2>/dev/null || echo "shiv may already be installed"

# Clean previous builds
rm -rf build/ dist/ isdi.pyz
mkdir -p dist

# Copy our patched config
BUILD_DIR="$(mktemp -d)"
trap "rm -rf $BUILD_DIR" EXIT

# Copy files to temp
cp -r phone_scanner web templates webstatic static_data scripts "$BUILD_DIR/"
cp isdi config.py "$BUILD_DIR/"
cp -r data stalkerware-indicators "$BUILD_DIR/" 2>/dev/null || true

# Patch config
echo "Patching config.py for zipapp mode..."
python3 patch_config.py "$BUILD_DIR/config.py"

# Create a proper __main__.py entry point
cat > "$BUILD_DIR/__main__.py" << 'EOF'
#!/usr/bin/env python3
"""Main entry point for ISDI"""
import sys
import os
from pathlib import Path

# Ensure package is in path
sys.path.insert(0, os.path.dirname(__file__))

if __name__ == '__main__':
    import webbrowser
    from threading import Timer
    
    import config
    from phone_scanner import db
    from web import app, sa
    
    PORT = 6200 if not (config.TEST or config.DEBUG) else 6202
    HOST = "127.0.0.1" if config.DEBUG else "0.0.0.0"
    
    def open_browser():
        """Opens a browser to make it easy to navigate to ISDi"""
        if not config.TEST:
            webbrowser.open(f"http://{HOST}:{PORT}", new=0, autoraise=True)
    
    # Check for test mode
    if 'TEST' in sys.argv[1:] or 'test' in sys.argv[1:]:
        print("Running in test mode.")
        config.set_test_mode(True)
    
    print(f"TEST={config.TEST}")
    if hasattr(config, 'DATA_DIR'):
        print(f"Data directory: {config.DATA_DIR}")
    
    db.init_db(app, sa, force=config.TEST)
    config.setup_logger()
    Timer(1, open_browser).start()
    app.run(host=HOST, port=PORT, debug=config.DEBUG, use_reloader=config.DEBUG)
EOF

# Build with shiv (it extracts binary deps automatically)
echo "Building with shiv (this will take a few minutes)..."
cd "$BUILD_DIR"
shiv \
    --site-packages . \
    --compressed \
    --entry-point __main__ \
    --output-file "$ORIG_DIR/dist/isdi.pyz" \
    --reproducible \
    $(grep -v '^#' "$ORIG_DIR/requirements.txt" | tr '\n' ' ')

cd "$ORIG_DIR"

echo ""
echo "✓ Build complete: dist/isdi.pyz"
echo ""
echo "Transfer to Termux:"
echo "  adb push dist/isdi.pyz /sdcard/"
echo ""
echo "On Termux:"
echo "  pkg install python"
echo "  mv /sdcard/isdi.pyz ~/"
echo "  chmod +x ~/isdi.pyz"
echo "  ~/isdi.pyz"
echo ""
echo "Size: $(du -h dist/isdi.pyz 2>/dev/null | cut -f1 || echo 'N/A')"
