#!/bin/bash
set -e

echo "[TFTP] Starting dnsmasq TFTP server..."

# Create TFTP directories
mkdir -p /data/tftp

# Download iPXE boot files if they don't exist
echo "[TFTP] Checking iPXE boot files..."

if [ ! -f /data/tftp/undionly.kpxe ]; then
    echo "[TFTP] Downloading undionly.kpxe..."
    curl -L -o /data/tftp/undionly.kpxe \
        https://boot.ipxe.org/undionly.kpxe 2>&1 || echo "[TFTP] Warning: Failed to download undionly.kpxe"
    if [ -f /data/tftp/undionly.kpxe ]; then
        echo "[TFTP] ✓ undionly.kpxe downloaded successfully"
    fi
fi

if [ ! -f /data/tftp/ipxe.efi ]; then
    echo "[TFTP] Downloading ipxe.efi (UEFI)..."
    curl -L -o /data/tftp/ipxe.efi \
        https://boot.ipxe.org/ipxe.efi 2>&1 || echo "[TFTP] Warning: Failed to download ipxe.efi"
    if [ -f /data/tftp/ipxe.efi ]; then
        echo "[TFTP] ✓ ipxe.efi downloaded successfully"
    fi
fi

# Create a simple boot.ipxe that chains to API menu
echo "[TFTP] Creating boot menu script..."
cat > /data/tftp/boot.ipxe << 'EOF'
#!ipxe
# Chain to API boot menu
chain http://api:8000/api/v1/boot/ipxe/menu
EOF

echo "[TFTP] Boot files ready!"
echo "[TFTP] TFTP root: /data/tftp"
echo "[TFTP] Available boot files:"
ls -lah /data/tftp/ 2>/dev/null | grep -E "kpxe|efi|ipxe" || echo "[TFTP] No boot files found yet"

echo "[TFTP] Starting dnsmasq..."
exec dnsmasq -C /tftp/config/dnsmasq.conf -d
