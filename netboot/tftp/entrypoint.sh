#!/bin/bash
set -e

echo "[TFTP] Starting dnsmasq TFTP server..."

# Create TFTP directories
mkdir -p /data/tftp

# ===============================================
# Copy pre-built iPXE binaries from Docker image
# ===============================================
echo "[TFTP] Setting up iPXE bootloaders..."

if [ -f /tftp/undionly.kpxe ]; then
    echo "[TFTP] ✓ Copying undionly.kpxe to TFTP volume..."
    cp /tftp/undionly.kpxe /data/tftp/undionly.kpxe
fi

if [ -f /tftp/ipxe.efi ]; then
    echo "[TFTP] ✓ Copying ipxe.efi to TFTP volume..."
    cp /tftp/ipxe.efi /data/tftp/ipxe.efi
fi

# ===============================================
# Create undionly.ipxe - Script that undionly.kpxe will AUTO-EXECUTE
# ===============================================
# When undionly.kpxe boots as a firmware extension, it will look for 
# a script with the same name but .ipxe extension. By creating undionly.ipxe,
# we make undionly.kpxe automatically execute our boot script!
cat > /data/tftp/undionly.ipxe << 'EOF'
#!ipxe
echo
echo ====================================================
echo        Netboot Orchestrator - iPXE Stage 2
echo ====================================================
echo
echo MAC Address: ${mac}
echo IPv4 Address: ${ipv4}
echo Gateway: ${gw}
echo
echo Initializing network with DHCP...
dhcp
echo
echo Attempting HTTP chainload to API on 192.168.1.50:8000
timeout 15 chain http://192.168.1.50:8000/api/v1/boot/ipxe/menu || goto retry

:retry
echo
echo WARNING: HTTP request failed - retrying with DHCP renewal...
dhcp
timeout 15 chain http://192.168.1.50:8000/api/v1/boot/ipxe/menu || goto shell

:shell
echo
echo ===============================================
echo ERROR: Could not load boot menu
echo ===============================================
echo
echo Cannot reach: http://192.168.1.50:8000/api/v1/boot/ipxe/menu
echo
echo Try these diagnostic commands:
echo   ping 192.168.1.50
echo   chain http://192.168.1.50:8000/api/v1/boot/ipxe/menu
echo   dhcp
echo
shell
reboot
EOF

echo "[TFTP] ✓ undionly.ipxe auto-execute script created"

# ===============================================
# Create boot.ipxe - Fallback explicit boot script
# ===============================================
# Legacy: Kept for compatibility. undionly.ipxe is the primary auto-boot mechanism.
cat > /data/tftp/boot.ipxe << 'EOF'

echo "[TFTP] ✓ Boot.ipxe auto-chainload script created"

# ===============================================
# Create boot-menu.ipxe - Main boot menu
# ===============================================
cat > /data/tftp/boot-menu.ipxe << 'EOF'
#!ipxe
# Netboot Orchestrator - Main Boot Menu

clear
echo ========================================
echo Netboot Orchestrator
echo Main Boot Menu
echo ========================================
echo
echo Device MAC: ${mac}
echo Device IP: ${ip}
echo Next Server: ${next-server}
echo
echo [1] iPXE Shell
echo [2] Boot Menu (reload)
echo [0] Reboot
echo

choose --timeout 60 --default 1 selected
goto ${selected}

:1
echo
echo Opening iPXE command shell...
echo Type 'help' for commands or 'chain tftp://${next-server}/boot-menu.ipxe' to return
echo
shell
goto boot-menu.ipxe

:2
echo Reloading boot menu...
chain tftp://${next-server}/boot-menu.ipxe

:0
reboot
EOF

echo "[TFTP] ✓ Main boot-menu.ipxe created"

# ===============================================
# Display TFTP configuration summary
# ===============================================
echo
echo "[TFTP] ========================================" 
echo "[TFTP] TFTP Configuration Ready"
echo "[TFTP] ========================================"
echo "[TFTP] TFTP root: /data/tftp"
echo "[TFTP] Available boot files:"
ls -lh /data/tftp/*.{kpxe,efi,ipxe} 2>/dev/null | awk '{printf "[TFTP]   %-30s %6s\n", $9, $5}'
echo "[TFTP]"
echo "[TFTP] Boot flow:"
echo "[TFTP]   1. Device DHCP → gets Option 67: undionly.kpxe"
echo "[TFTP]   2. Device downloads undionly.kpxe from TFTP"
echo "[TFTP]   3. undionly.kpxe auto-searches for boot.ipxe in TFTP root"
echo "[TFTP]   4. boot.ipxe chainloads to boot-menu.ipxe"
echo "[TFTP]   5. boot-menu.ipxe displays menu to user"
echo "[TFTP]"
echo "[TFTP] Starting dnsmasq..."
echo

exec dnsmasq -C /tftp/config/dnsmasq.conf -d

