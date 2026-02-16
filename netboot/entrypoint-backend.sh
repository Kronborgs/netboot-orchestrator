#!/bin/bash
set -e

echo "============================================="
echo " Netboot Orchestrator - Backend Services"
echo " Designed by Kenneth Kronborg AI Team"
echo "============================================="

# ====================================================
# Configuration
# ====================================================
BOOT_IP="${BOOT_SERVER_IP:-192.168.1.50}"
echo "[Config] Boot server IP: $BOOT_IP"

# ====================================================
# 1. Install custom iPXE bootloader
# ====================================================
# The custom undionly.kpxe has an embedded boot script that
# automatically chains to the HTTP boot menu API.
# This eliminates the classic "double iPXE" detection problem.
echo "[TFTP] Preparing TFTP directory and bootloaders..."
mkdir -p /data/tftp

if [ -f /opt/ipxe/undionly.kpxe ]; then
    cp /opt/ipxe/undionly.kpxe /data/tftp/undionly.kpxe
    KPXE_SIZE=$(stat -c%s /data/tftp/undionly.kpxe)
    echo "[TFTP] ✓ Custom undionly.kpxe installed ($KPXE_SIZE bytes, has embedded boot script)"
else
    echo "[WARN] Custom iPXE binary not found at /opt/ipxe/undionly.kpxe"
    echo "[WARN] Falling back to stock download (no embedded script)..."
    curl -fSL --connect-timeout 15 -o /data/tftp/undionly.kpxe \
        "https://boot.ipxe.org/undionly.kpxe" 2>/dev/null || \
    curl -fSL --connect-timeout 15 -o /data/tftp/undionly.kpxe \
        "https://github.com/ipxe/ipxe/releases/latest/download/undionly.kpxe" 2>/dev/null
fi

# Verify BIOS bootloader exists (required)
if [ ! -f /data/tftp/undionly.kpxe ] || [ $(stat -c%s /data/tftp/undionly.kpxe 2>/dev/null || echo 0) -lt 10000 ]; then
    echo "[ERROR] undionly.kpxe is missing or corrupt - PXE boot will not work!"
    exit 1
fi

# ====================================================
# 2. Create iPXE boot scripts
# ====================================================
echo "[TFTP] Creating boot scripts..."

# --- undionly.ipxe ---
# This is the Stage 2 script: iPXE loads this, it chains to the HTTP API menu.
# Uses heredoc with 'quoted' delimiter to preserve iPXE ${variables} literally.
# __BOOT_IP__ is replaced by sed afterwards with the actual server IP.
cat > /data/tftp/undionly.ipxe << 'IPXE_EOF'
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
echo Loading boot menu from __BOOT_IP__:8000 ...
chain http://__BOOT_IP__:8000/api/v1/boot/ipxe/menu || goto retry

:retry
echo
echo Boot menu failed - retrying with DHCP renewal...
dhcp
chain http://__BOOT_IP__:8000/api/v1/boot/ipxe/menu || goto shell

:shell
echo
echo ===============================================
echo ERROR: Could not load boot menu
echo ===============================================
echo
echo Server: http://__BOOT_IP__:8000/api/v1/boot/ipxe/menu
echo
echo Dropping to iPXE shell...
shell
reboot
IPXE_EOF
sed -i "s/__BOOT_IP__/${BOOT_IP}/g" /data/tftp/undionly.ipxe

# --- boot.ipxe ---
# Backup entry point (alternative chainload)
cat > /data/tftp/boot.ipxe << BOOT_EOF
#!ipxe
dhcp
chain http://${BOOT_IP}:8000/api/v1/boot/ipxe/menu
BOOT_EOF

# --- boot-menu.ipxe ---
# Placeholder menu until FastAPI generates the real one.
# Uses proper iPXE menu/item/choose syntax.
cat > /data/tftp/boot-menu.ipxe << 'MENU_EOF'
#!ipxe
menu Netboot Orchestrator - Boot Menu
item --gap --
item --gap --  Waiting for API to generate menu...
item --gap --
item shell     Drop to iPXE Shell
item reboot    Reboot
choose --timeout 30 --default shell selected || goto shell
goto ${selected}

:shell
echo Entering iPXE shell...
shell

:reboot
reboot
MENU_EOF

echo "[TFTP] ✓ Boot scripts created"

# Raspberry Pi TFTP setup
echo "[TFTP] Creating Raspberry Pi boot directories..."
mkdir -p /data/tftp/raspi
# Pi boot files (kernel, config.txt, cmdline.txt) should be placed
# in /data/tftp/raspi/ or per-serial subdirectories.
# The Pi's boot ROM will fetch them via TFTP.
if [ ! -f /data/tftp/raspi/README.txt ]; then
    cat > /data/tftp/raspi/README.txt << 'PI_README'
Raspberry Pi Network Boot
=========================
Place boot files for Raspberry Pi here:
  - Per-serial: /data/tftp/raspi/<serial>/
  - Shared:     /data/tftp/raspi/

Required files per Pi:
  - start4.elf, fixup4.dat (from RPi firmware)
  - config.txt (with kernel=kernel8.img, initramfs initrd.img followkernel)
  - cmdline.txt (with root= iSCSI or NFS params)
  - kernel8.img, initrd.img (Linux kernel + initramfs)

The Netboot Orchestrator can generate these via the API/WebUI.
PI_README
fi
echo "[TFTP] ✓ Raspberry Pi directories ready"

# Show all TFTP files
echo "[TFTP] TFTP root contents:"
ls -lh /data/tftp/ 2>&1 | sed 's/^/  /'

# ====================================================
# 3. Generate dnsmasq configuration (Proxy DHCP)
# ====================================================
# Proxy DHCP: dnsmasq does NOT assign IP addresses.
# The existing DHCP server (e.g. Unifi router) handles IP assignment.
# dnsmasq only provides PXE boot options and serves TFTP.
# This eliminates DHCP conflicts and enables proper iPXE detection.
echo "[dnsmasq] Generating proxy DHCP configuration..."
mkdir -p /etc/dnsmasq.d

cat > /etc/dnsmasq.d/netboot.conf << DNSMASQ_EOF
# ========================================
# Netboot Orchestrator - dnsmasq config
# Generated at runtime by entrypoint
# ========================================

# Disable DNS server (not needed, only TFTP + proxy DHCP)
port=0

# TFTP server
enable-tftp
tftp-root=/data/tftp
tftp-no-blocksize
tftp-single-port
tftp-max=50

# Logging
log-facility=/dev/stdout
log-dhcp

# Listen on all interfaces
interface=*
bind-dynamic

# ========================================
# Proxy DHCP (PXE boot options only)
# No IP assignment - existing DHCP server handles that
# ========================================
dhcp-range=10.10.50.0,proxy
dhcp-range=192.168.1.0,proxy

# Make PXE clients boot immediately (no menu delay)
pxe-prompt="Netboot Orchestrator",0

# ========================================
# Client Detection
# ========================================

# iPXE detection - multiple methods for reliability
# Method 1: User class (option 77) - most widely supported
dhcp-userclass=set:ipxe,iPXE
# Method 2: Option 175 (iPXE feature flags) - backup detection
dhcp-match=set:ipxe,175

# Architecture detection (DHCP option 93)
dhcp-match=set:bios,93,0
dhcp-match=set:efi32,93,6
dhcp-match=set:efibc,93,7
dhcp-match=set:efi64,93,9

# ========================================
# Boot File Assignment
# ========================================

# iPXE clients: chain directly to HTTP boot menu API
# (no TFTP intermediate step - faster and more reliable)
dhcp-boot=tag:ipxe,http://${BOOT_IP}:8000/api/v1/boot/ipxe/menu

# Non-iPXE BIOS PXE: serve custom iPXE binary (has embedded boot script)
dhcp-boot=tag:!ipxe,tag:bios,undionly.kpxe,,${BOOT_IP}

# UEFI: serve iPXE EFI binary
dhcp-boot=tag:!ipxe,tag:efi64,ipxe.efi,,${BOOT_IP}
dhcp-boot=tag:!ipxe,tag:efibc,ipxe.efi,,${BOOT_IP}
dhcp-boot=tag:!ipxe,tag:efi32,ipxe.efi,,${BOOT_IP}

# PXE boot service discovery (for legacy PXE ROM)
pxe-service=tag:!ipxe,x86PC,"Netboot Orchestrator",undionly
pxe-service=tag:!ipxe,x86-64_EFI,"Netboot Orchestrator",ipxe
pxe-service=tag:!ipxe,BC_EFI,"Netboot Orchestrator",ipxe

# ========================================
# Raspberry Pi 4/5 Support
# Pi sends vendor class "PXEClient:Arch:00000:UNDI:002001"
# The Pi's boot ROM fetches files from TFTP at /<serial>/
# We serve the boot files from /data/tftp/raspi/
# ========================================
dhcp-match=set:raspi,60,PXEClient:Arch:00011
# Pi 4/5 ARM64 boot
dhcp-boot=tag:raspi,bootcode.bin,,${BOOT_IP}
DNSMASQ_EOF

echo "[dnsmasq] ✓ Configuration generated (proxy DHCP mode)"
echo "[dnsmasq] Boot rules:"
grep -E "dhcp-boot|pxe-service|dhcp-range" /etc/dnsmasq.d/netboot.conf | sed 's/^/  /'

# ====================================================
# 4. Start services
# ====================================================

# Start dnsmasq (TFTP + Proxy DHCP)
echo "[dnsmasq] Starting TFTP + Proxy DHCP server..."
/usr/sbin/dnsmasq -C /etc/dnsmasq.d/netboot.conf -d &
DNSMASQ_PID=$!
echo "[dnsmasq] Started with PID $DNSMASQ_PID"

# Start tgtd (iSCSI)
echo "[tgtd] Starting iSCSI target..."
mkdir -p /iscsi-images
/usr/sbin/tgtd -f &
TGTD_PID=$!
sleep 2
echo "[tgtd] Started with PID $TGTD_PID"

# Start FastAPI
echo "[FastAPI] Starting API server on 0.0.0.0:8000..."
cd /app/backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!

# Wait for FastAPI to initialize
echo "[Boot Menu] Waiting for FastAPI to initialize..."
sleep 5

# ====================================================
# 5. Boot menu generation (from API)
# ====================================================
generate_boot_menu() {
    local tmpfile="/tmp/boot-menu-tmp.ipxe"
    curl -sf http://127.0.0.1:8000/api/v1/boot/ipxe/menu -o "$tmpfile" 2>/dev/null
    if [ $? -eq 0 ] && [ -s "$tmpfile" ] && head -1 "$tmpfile" | grep -q '#!ipxe'; then
        mv "$tmpfile" /data/tftp/boot-menu.ipxe
        echo "[Boot Menu] ✓ Menu updated from API"
    else
        rm -f "$tmpfile"
        echo "[Boot Menu] ✗ API not ready or returned invalid menu"
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

echo "============================================="
echo " All services started successfully"
echo "   TFTP:    0.0.0.0:69  (proxy DHCP + TFTP)"
echo "   API:     0.0.0.0:8000"
echo "   iSCSI:   0.0.0.0:3260"
echo "   Boot IP: $BOOT_IP"
echo ""
echo " Netboot Orchestrator is designed by"
echo " Kenneth Kronborg AI Team"
echo "============================================="

# Wait for FastAPI (foreground process)
wait $FASTAPI_PID
