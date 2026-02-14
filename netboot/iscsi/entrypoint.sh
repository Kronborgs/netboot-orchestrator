#!/bin/bash
set -e

echo "[iSCSI] Initializing TGT daemon..."

# Create data directories
mkdir -p /data/iscsi/images

# Initialize TGT configuration
if [ ! -f /data/iscsi/targets.tgt ]; then
    cat > /data/iscsi/targets.tgt << 'EOF'
# TGT configuration
# Auto-generated configuration file
# Targets should be created dynamically via API
EOF
fi

# Start TGT daemon
echo "[iSCSI] Starting TGT daemon..."
tgtd -f

echo "[iSCSI] Ready for targets..."
wait
