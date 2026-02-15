#!/bin/bash
set -e

echo "[Backend] Starting Netboot Orchestrator Services..."

# Ensure boot scripts exist in TFTP directory
echo "[TFTP] Creating boot scripts..."
mkdir -p /data/tftp

# Create undionly.ipxe - chains to boot menu
cat > /data/tftp/undionly.ipxe << 'EOF'
#!ipxe
echo
echo ====================================================
echo        Netboot Orchestrator - iPXE Stage 2
echo ====================================================
echo
echo MAC Address: ${mac}
echo
echo Initializing network with DHCP...
dhcp
echo IPv4 Address: ${net0/ip}
echo Gateway: ${net0/gateway}
echo
echo Attempting TFTP chainload to boot menu on 192.168.1.50
timeout 15 chain tftp://192.168.1.50/boot-menu.ipxe || goto retry

:retry
echo
echo WARNING: TFTP boot menu failed - retrying with DHCP renewal...
dhcp
timeout 15 chain tftp://192.168.1.50/boot-menu.ipxe || goto shell

:shell
echo
echo ===============================================
echo ERROR: Could not load boot menu
echo ===============================================
echo
echo Cannot reach: tftp://192.168.1.50/boot-menu.ipxe
echo
echo Falling back to iPXE shell...
shell
reboot
EOF

# Create boot.ipxe - chains to HTTP API
cat > /data/tftp/boot.ipxe << 'EOF'
#!ipxe
dhcp
chain http://192.168.1.50:8000/api/v1/boot/ipxe/menu
EOF

# Create boot-menu.ipxe - initial placeholder
cat > /data/tftp/boot-menu.ipxe << 'EOF'
#!ipxe
clear
echo ========================================
echo Netboot Orchestrator
echo Main Boot Menu
echo ========================================
echo
echo Device MAC: ${mac}
echo Device IP: ${ip}
echo
echo [1] iPXE Shell
echo [2] Boot Menu (reload)
echo [0] Reboot
echo
EOF

ls -lh /data/tftp/*.ipxe
echo "[TFTP] ✓ Boot scripts ready"

# Start dnsmasq in background
echo "[dnsmasq] Starting TFTP/DHCP server..."
/usr/sbin/dnsmasq -C /etc/dnsmasq.d/netboot.conf -d &
DNSMASQ_PID=$!

# Start tgtd (iSCSI) in background
echo "[tgtd] Starting iSCSI target..."
/usr/sbin/tgtd -f &
TGTD_PID=$!

# Start FastAPI (background)
echo "[FastAPI] Starting API server on 0.0.0.0:8000..."
cd /app/backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!

# Wait for FastAPI to be ready
echo "[Boot Menu] Waiting for FastAPI to initialize..."
sleep 3

# Generate boot menu from API and save to TFTP
generate_boot_menu() {
    echo "[Boot Menu] Generating menu from API endpoint..."
    curl -s http://127.0.0.1:8000/api/v1/boot/ipxe/menu -o /data/tftp/boot-menu.ipxe
    if [ $? -eq 0 ]; then
        echo "[Boot Menu] ✓ Menu generated: /data/tftp/boot-menu.ipxe"
    else
        echo "[Boot Menu] ✗ Failed to generate menu"
    fi
}

# Generate menu initially
generate_boot_menu

# Regenerate menu every 5 minutes in background
while true; do
    sleep 300
    generate_boot_menu
done &
BOOT_MENU_PID=$!

# Wait for FastAPI (foreground)
wait $FASTAPI_PID
