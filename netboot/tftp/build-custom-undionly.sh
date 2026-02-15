#!/bin/bash
# Build custom undionly.kpxe with embedded boot script
# This avoids network issues during multi-VLAN PXE boot

set -e

BUILD_DIR="/tmp/ipxe-build"
EMBED_SCRIPT="/tmp/embed.ipxe"
OUTPUT_DIR="/data/tftp"

echo "[BUILD] Building custom undionly.kpxe with embedded script..."
echo "[BUILD] Build directory: $BUILD_DIR"
echo "[BUILD] Embed script: $EMBED_SCRIPT"
echo

# Create build directory
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Check if we've already cloned iPXE
if [ ! -d "ipxe" ]; then
    echo "[BUILD] Cloning iPXE repository from GitHub..."
    git clone https://github.com/ipxe/ipxe.git --depth 1 2>&1 | grep -E "Cloning|done|fatal" || true
else
    echo "[BUILD] iPXE repository already exists, skipping clone"
fi

# Copy embed script
if [ -f "$EMBED_SCRIPT" ]; then
    echo "[BUILD] Using embed script from: $EMBED_SCRIPT"
else
    echo "[BUILD] ERROR: Embed script not found at $EMBED_SCRIPT"
    exit 1
fi

# Build undionly.kpxe with embedded script
echo "[BUILD] Compiling undionly.kpxe with embedded script..."
cd "$BUILD_DIR/ipxe/src"

# Clean previous builds
make clean 2>&1 | tail -1 || true

# Build with embedded script
make bin/undionly.kpxe EMBED="$EMBED_SCRIPT" 2>&1 | grep -E "Building|built|Error" || true

# Copy to TFTP directory
if [ -f "bin/undionly.kpxe" ]; then
    SIZE=$(ls -lh bin/undionly.kpxe | awk '{print $5}')
    echo "[BUILD] ✓ Successfully built undionly.kpxe ($SIZE)"
    cp bin/undionly.kpxe "$OUTPUT_DIR/undionly.kpxe"
    echo "[BUILD] ✓ Copied to $OUTPUT_DIR/undionly.kpxe"
    ls -lh "$OUTPUT_DIR/undionly.kpxe"
else
    echo "[BUILD] ERROR: Build failed - bin/undionly.kpxe not found"
    exit 1
fi

echo "[BUILD] Complete!"
