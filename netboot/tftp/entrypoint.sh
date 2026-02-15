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
# Create boot-menu.ipxe with interactive menu options

cat > /data/tftp/boot-menu.ipxe << 'EOF'
#!ipxe
# Netboot Orchestrator - PXE Boot Menu
# https://ipxe.org

# Initialize
clear screen

# Detect system info
cpuid --ext -- x86_64 && set BITS 64 || set BITS 32
isset ${firmware} || set firmware BIOS

:menu
clear

echo  ========================================
echo  🚀 Netboot Orchestrator
echo  PXE Boot Menu
echo  ========================================
echo
echo  Client Information:
echo  - MAC Address: ${mac}
echo  - IP Address:  ${ip}
echo  - Boot Server: ${next-server}
echo  - Firmware:    ${firmware}
echo  - CPU Bits:    ${BITS}
echo
echo  Boot Options:
echo  [1] Network Boot (HTTP OS Installer)
echo  [2] iSCSI Network Disk Boot
echo  [3] API Boot Menu (select OS)
echo  [4] Local Disk Boot (if available)
echo  [5] iPXE Command Shell
echo  [0] Exit / Power Off
echo
echo  Select boot method (timeout 30 seconds):
echo

# Menu with timeout
choose --timeout 30 --default 3 selected
goto ${selected}

# ==================== Option 1: HTTP Boot ====================
:1
clear
echo  Attempting to boot from HTTP server...
echo  Server: ${next-server}:8000
echo

# Set boot image URL
set base_url http://${next-server}:8000

echo  Downloading boot menu from API...
chain ${base_url}/api/v1/boot/ipxe/menu
goto menu

# ==================== Option 2: iSCSI Boot ====================
:2
clear
echo  iSCSI Network Disk Boot
echo  Server: ${next-server}
echo

# Configure iSCSI target
set root-path iscsi:${next-server}::3260:0:*:*
echo  Connecting to iSCSI: ${root-path}

sanboot ${root-path} || (
    echo  iSCSI boot failed!
    sleep 5
    goto menu
)

# ==================== Option 3: API Menu ====================
:3
clear
echo  Loading dynamic OS installer menu...
echo  Server: ${next-server}:8000
echo

set base_url http://${next-server}:8000
chain ${base_url}/api/v1/boot/ipxe/menu || (
    echo
    echo  Failed to load API menu!
    echo  Retrying in 5 seconds...
    sleep 5
    goto menu
)

# ==================== Option 4: Local Boot ====================
:4
clear
echo  Attempting to boot from local disk...
echo  (if your computer has a bootable disk)
echo

# Try exit to local boot
exit

# If exit fails, show message
echo  Local disk boot not available
sleep 3
goto menu

# ==================== Option 5: Shell ====================
:5
clear
echo  iPXE Command Shell
echo  (Type 'help' for commands, 'exit' to return to menu)
echo

shell
goto menu

# ==================== Option 0: Exit ====================
:0
clear
echo  Exiting iPXE boot menu...
echo  Powering off in 3 seconds...
sleep 3
poweroff

# ==================== Default: Unknown Selection ====================
:unknown
echo  Error: Unknown selection
sleep 2
goto menu
EOF

echo "[TFTP] ✓ boot-menu.ipxe interactive menu created"
echo "[TFTP] TFTP root: /data/tftp"
echo "[TFTP] Available boot files:"
ls -lh /data/tftp/*.{kpxe,efi,ipxe} 2>/dev/null | grep -v "boot-menu\|boot\." || echo "[TFTP] No standard boot files found"

echo "[TFTP] Starting dnsmasq DHCP/TFTP server..."
exec dnsmasq -C /tftp/config/dnsmasq.conf -d

