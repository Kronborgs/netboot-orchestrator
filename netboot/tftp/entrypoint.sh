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
# Create boot.ipxe - Auto-chainload script in TFTP root
# ===============================================
# Standard undionly.kpxe will look for boot.ipxe in TFTP root as default
cat > /data/tftp/boot.ipxe << 'EOF'
#!ipxe
# Netboot Orchestrator - Auto-chainload boot script
# This runs automatically when undionly.kpxe boots

echo
echo ========================================
echo Netboot Orchestrator - Chainload
echo ========================================
echo

# Show boot info
echo Device MAC: ${mac}
echo Device IP: ${ip}
echo Next Server: ${next-server}
echo

# Attempt to load boot menu from menu script
echo Loading boot menu...
echo

# Try to load from DHCP-provided server (192.168.1.50)
isset ${next-server} && goto chain_from_next_server || goto chain_hardcoded

:chain_from_next_server
echo Attempting to load from: ${next-server}
chain tftp://${next-server}/boot-menu.ipxe && goto menu_loaded || goto chain_hardcoded

:chain_hardcoded
echo Attempting to load from hardcoded: 192.168.1.50
chain tftp://192.168.1.50/boot-menu.ipxe && goto menu_loaded || goto fallback_shell

:menu_loaded
# Boot menu executed successfully
goto end

:fallback_shell
echo
echo WARNING: Failed to load boot menu!
echo Dropping to iPXE shell for manual commands...
echo Type 'help' for commands, 'reboot' to start over, 'exit' to retry boot menu
echo

shell

# Retry boot menu
chain tftp://${next-server}/boot-menu.ipxe || reboot

:end
EOF

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

