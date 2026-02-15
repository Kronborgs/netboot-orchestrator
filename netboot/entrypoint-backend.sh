#!/bin/bash
set -e

echo "[Backend] Starting Netboot Orchestrator Services..."

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
