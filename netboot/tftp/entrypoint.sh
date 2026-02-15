#!/bin/bash
set -e

echo "[TFTP] Starting dnsmasq TFTP server..."

# Create TFTP directories
mkdir -p /data/tftp

# ===============================================
# Build custom undionly.kpxe with embedded script
# ===============================================
echo "[TFTP] Checking for custom undionly.kpxe build..."

if [ -f "/tftp/scripts/embed.ipxe" ] && command -v gcc &>/dev/null; then
    echo "[TFTP] Building custom undionly.kpxe with embedded boot script..."
    bash /entrypoint-build.sh 2>&1 || (
        echo "[TFTP] WARNING: Custom build failed, falling back to standard download"
        rm -f /data/tftp/undionly.kpxe
    )
else
    echo "[TFTP] Custom build dependencies not available, will download standard undionly.kpxe"
fi

# ===============================================
# Download standard boot files if custom build unavailable
# ===============================================
echo "[TFTP] Checking iPXE boot files..."

if [ ! -f /data/tftp/undionly.kpxe ]; then
    echo "[TFTP] Downloading undionly.kpxe (standard BIOS bootloader)..."
    curl -L -o /data/tftp/undionly.kpxe https://boot.ipxe.org/undionly.kpxe 2>&1 || echo "[TFTP] Warning: Failed to download"
fi

if [ ! -f /data/tftp/ipxe.efi ]; then
    echo "[TFTP] Downloading ipxe.efi (standard UEFI bootloader)..."
    curl -L -o /data/tftp/ipxe.efi https://boot.ipxe.org/ipxe.efi 2>&1 || echo "[TFTP] Warning: Failed to download"
fi

# boot.ipxe is no longer needed - embedded script is in undionly.kpxe now
# Create SIMPLE boot-menu.ipxe (minimal for debugging)

cat > /data/tftp/boot-menu.ipxe << 'EOF'
#!ipxe
# Netboot Orchestrator - Simple Test Menu

clear
echo ========================================
echo Netboot Orchestrator
echo ipxe Menu (Simple Version)
echo ========================================
echo
echo Mac: ${mac}
echo IP: ${ip}
echo Server: ${next-server}
echo
echo [1] Shell
echo [0] Reboot
echo

choose --timeout 60 --default 1 selected
goto ${selected}

:1
echo Opening shell...
shell
reboot

:0
reboot
EOF

echo "[TFTP] ✓ Simple boot-menu.ipxe created"
echo "[TFTP] TFTP root: /data/tftp"
echo "[TFTP] Available boot files:"
ls -lh /data/tftp/*.{kpxe,efi,ipxe} 2>/dev/null | grep -v "boot-menu\|boot\." || echo "[TFTP] No standard boot files found"

echo "[TFTP] Starting dnsmasq DHCP/TFTP server..."
exec dnsmasq -C /tftp/config/dnsmasq.conf -d

