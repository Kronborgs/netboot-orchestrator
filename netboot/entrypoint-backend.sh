#!/bin/bash
set -e

echo "[Backend] Starting Netboot Orchestrator Services..."

# Ensure boot scripts exist in TFTP directory
echo "[TFTP] Creating boot scripts..."
mkdir -p /data/tftp

# Create undionly.ipxe - chains to boot menu via TFTP
printf '#!ipxe\necho\necho ====================================================\necho        Netboot Orchestrator - iPXE Stage 2\necho ====================================================\necho\necho MAC Address: ${mac}\necho\necho Initializing network with DHCP...\ndhcp\necho IPv4 Address: ${net0/ip}\necho Gateway: ${net0/gateway}\necho\necho Attempting TFTP chainload to boot menu on 192.168.1.50\ntimeout 15 chain tftp://192.168.1.50/boot-menu.ipxe || goto retry\n\n:retry\necho\necho WARNING: TFTP boot menu failed - retrying with DHCP renewal...\ndhcp\ntimeout 15 chain tftp://192.168.1.50/boot-menu.ipxe || goto shell\n\n:shell\necho\necho ===============================================\necho ERROR: Could not load boot menu\necho ===============================================\necho\necho Cannot reach: tftp://192.168.1.50/boot-menu.ipxe\necho\necho Falling back to iPXE shell...\nshell\nreboot\n' > /data/tftp/undionly.ipxe

# Create boot.ipxe - chains to HTTP API (backup method)
printf '#!ipxe\ndhcp\nchain http://192.168.1.50:8000/api/v1/boot/ipxe/menu\n' > /data/tftp/boot.ipxe

# Create boot-menu.ipxe - initial placeholder  
printf '#!ipxe\nclear\necho ========================================\necho Netboot Orchestrator\necho Main Boot Menu\necho ========================================\necho\necho Device MAC: ${mac}\necho Device IP: ${ip}\necho\necho [1] iPXE Shell\necho [2] Boot Menu (reload)\necho [0] Reboot\necho\n' > /data/tftp/boot-menu.ipxe

echo "[TFTP] ✓ Boot scripts created:"
ls -lh /data/tftp/*.ipxe

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
