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

# Start FastAPI (foreground - main process)
echo "[FastAPI] Starting API server on 0.0.0.0:8000..."
cd /app/backend
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
