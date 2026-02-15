#!/bin/bash
set -e

echo "[TFTP] Starting dnsmasq TFTP server..."

# Create TFTP directories
mkdir -p /data/tftp/pxe

# Download iPXE boot files if they don't exist
echo "[TFTP] Checking iPXE boot files..."

if [ ! -f /data/tftp/pxe/undionly.kpxe ]; then
    echo "[TFTP] Downloading undionly.kpxe..."
    curl -L -o /data/tftp/pxe/undionly.kpxe \
        https://boot.ipxe.org/undionly.kpxe 2>/dev/null || echo "[TFTP] Warning: Failed to download undionly.kpxe"
fi

if [ ! -f /data/tftp/pxe/ipxe.efi ]; then
    echo "[TFTP] Downloading ipxe.efi (UEFI)..."
    curl -L -o /data/tftp/pxe/ipxe.efi \
        https://boot.ipxe.org/ipxe.efi 2>/dev/null || echo "[TFTP] Warning: Failed to download ipxe.efi"
fi

# Create a simple boot.ipxe that chains to API menu
echo "[TFTP] Creating boot menu script..."
cat > /data/tftp/pxe/boot.ipxe << 'EOF'
#!ipxe
# Chain to API boot menu
chain http://api:8000/api/v1/boot/ipxe/menu
EOF

echo "[TFTP] Boot files ready!"
echo "[TFTP] TFTP root: /data/tftp"
echo "[TFTP] Available boot files:"
ls -lah /data/tftp/pxe/ 2>/dev/null || echo "[TFTP] No files yet"

exec dnsmasq -C /tftp/config/dnsmasq.conf -d
