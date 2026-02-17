#!/bin/bash
# Build ISDI as a single self-contained .pyz executable for Termux/Android
# Uses shiv + pre-built wheels to avoid compilation on weak Android hardware
#
# Usage: ./build-termux-pex.sh
# Output: dist/isdi.pyz (~100-150 MB - single file, no installation needed)
#
# Run this on your Linux machine, then transfer to Android

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== ISDI Shiv .pyz Builder for Termux ===${NC}"
echo "Building self-contained executable with pre-built wheels..."
echo ""

# Save original directory
ORIG_DIR="$(pwd)"

# =============================================================================
# Step 1: Install shiv builder
# =============================================================================
echo -e "${BLUE}[1/5]${NC} Installing shiv..."
pip install --break-system-packages -q shiv 2>/dev/null || \
    pip install -q shiv 2>/dev/null || \
    echo "Warning: shiv may already be installed"

# =============================================================================
# Step 2: Clean previous builds (but preserve wheels cache)
# =============================================================================
echo -e "${BLUE}[2/5]${NC} Cleaning previous builds..."
rm -rf build/ dist/ *.pyz
# Note: wheels/ and .wheel-cache/ are preserved for speed
mkdir -p dist wheels

# =============================================================================
# Step 3: Collect pre-built wheels (NO COMPILATION)
# =============================================================================
echo -e "${BLUE}[3/5]${NC} Collecting pre-built wheels..."

WHEEL_DIR="$ORIG_DIR/wheels"
WHEEL_CACHE="$ORIG_DIR/.wheel-cache"

# If wheels already downloaded, skip (they're cached)
if [ -d "$WHEEL_DIR" ] && [ "$(ls -1 $WHEEL_DIR 2>/dev/null | wc -l)" -gt 0 ]; then
    echo "  ✓ Wheels already cached ($(ls $WHEEL_DIR | wc -l) files)"
else
    echo "  Downloading wheels with --prefer-binary flag..."
    mkdir -p "$WHEEL_DIR"
    
    pip wheel \
        --prefer-binary \
        --no-build-isolation \
        --no-cache-dir \
        --wheel-dir "$WHEEL_DIR" \
        --quiet \
        flask \
        flask-sqlalchemy \
        flask-migrate \
        flask-wtf \
        wtforms-alchemy \
        pymobiledevice3 \
        click \
        pyyaml \
        rsonlite \
        2>&1 | grep -E "(Successfully|Downloading|Collecting)" | head -20 || true
    
    echo "  ✓ Downloaded: $(ls $WHEEL_DIR | wc -l) files"
    
    # Also cache for fast-build script
    mkdir -p "$WHEEL_CACHE"
    cp "$WHEEL_DIR"/* "$WHEEL_CACHE/" 2>/dev/null || true
fi

# =============================================================================
# Step 4: Prepare source code
# =============================================================================
echo -e "${BLUE}[4/5]${NC} Preparing source code..."

BUILD_DIR="$(mktemp -d)"
trap "rm -rf $BUILD_DIR $WHEEL_DIR" EXIT

# Copy modern src-layout structure (shiv only packages Python packages)
mkdir -p "$BUILD_DIR/src"
cp -r "$ORIG_DIR/src/isdi" "$BUILD_DIR/src/"
cp "$ORIG_DIR/pyproject.toml" "$BUILD_DIR/" 2>/dev/null || true
cp "$ORIG_DIR/MANIFEST.in" "$BUILD_DIR/" 2>/dev/null || true
cp "$ORIG_DIR/README.md" "$BUILD_DIR/" 2>/dev/null || true
cp "$ORIG_DIR/LICENSE" "$BUILD_DIR/" 2>/dev/null || true

# Copy wheels into package for offline installation
cp -r "$WHEEL_DIR" "$BUILD_DIR/wheels"

# Create bootstrap module inside the package so shiv includes it
cat > "$BUILD_DIR/src/isdi/termux_bootstrap.py" << 'MAIN_EOF'
#!/usr/bin/env python3
"""
ISDI - Bootstrap entry point for .pyz executable

Optimized for Termux/Android with pre-built wheels.
No external dependencies required after extraction.
"""

import os
import sys

def main():
    """Entry point for ISDI CLI"""
    try:
        from isdi.cli import main as cli_main
        return cli_main()
    except ImportError as exc:
        print(f"Error: Failed to import ISDI CLI: {exc}", file=sys.stderr)
        print(
            "This may happen on first run. Trying to install dependencies...",
            file=sys.stderr,
        )

        # Try installing wheels if they're bundled
        import subprocess

        wheel_dir = os.path.join(os.path.dirname(__file__), "wheels")
        if os.path.isdir(wheel_dir):
            print("Installing bundled wheels...", file=sys.stderr)
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--no-index",
                    "--find-links",
                    wheel_dir,
                    "--upgrade",
                    "pip",
                ],
                check=False,
            )

            # Retry import
            from isdi.cli import main as cli_main
            return cli_main()

        print(
            "Wheels directory not found. Please reinstall isdi.pyz",
            file=sys.stderr,
        )
        return 1

if __name__ == "__main__":
    sys.exit(main())
MAIN_EOF

# =============================================================================
# Step 5: Build with shiv
# =============================================================================
echo -e "${BLUE}[5/5]${NC} Building .pyz archive with shiv..."
echo "  This will package everything into a single executable file..."

cd "$BUILD_DIR"

# Build with shiv, including pre-built wheels directory
shiv \
    --compressed \
    --reproducible \
    --entry-point isdi.termux_bootstrap:main \
    --output-file "$ORIG_DIR/dist/isdi.pyz" \
    --python=/usr/bin/python3 \
    .

cd "$ORIG_DIR"

# =============================================================================
# Verify and report
# =============================================================================
if [ -f "dist/isdi.pyz" ]; then
    PYZ_SIZE=$(du -h dist/isdi.pyz | cut -f1)
    
    echo ""
    echo -e "${GREEN}✓ Build Complete!${NC}"
    echo ""
    echo "Archive Details:"
    echo "  File:     dist/isdi.pyz"
    echo "  Size:     $PYZ_SIZE"
    echo "  Type:     Self-contained Python executable"
    echo "  Platform: Python 3.8+ (Termux compatible)"
    echo ""
    echo -e "${BLUE}Installation on Android/Termux:${NC}"
    echo "  1. Transfer file:"
    echo "     adb push dist/isdi.pyz /sdcard/"
    echo ""
    echo "  2. Install Python (if not already installed):"
    echo "     pkg install python"
    echo ""
    echo "  3. Setup:"
    echo "     mv /sdcard/isdi.pyz ~/"
    echo "     chmod +x ~/isdi.pyz"
    echo ""
    echo "  4. Run:"
    echo "     python3 ~/isdi.pyz run"
    echo ""
    echo -e "${BLUE}Or create a symlink:${NC}"
    echo "     ln -s ~/isdi.pyz ~/.local/bin/isdi"
    echo "     isdi run"
    echo ""
    echo -e "${BLUE}Benefits:${NC}"
    echo "  ✓ Single file (no installation needed)"
    echo "  ✓ Pre-built wheels (no compilation on Android)"
    echo "  ✓ Fast startup"
    echo "  ✓ All dependencies included"
    echo ""
else
    echo -e "${RED}✗ Build failed!${NC}"
    exit 1
fi

# =============================================================================
# Cleanup
# =============================================================================
rm -rf "$WHEEL_DIR" 2>/dev/null || true

echo -e "${GREEN}Done!${NC}"

