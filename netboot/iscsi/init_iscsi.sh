#!/bin/bash
# Initialize iSCSI targets
# This script is called when the container starts

echo "Initializing iSCSI targets from config..."

# Load targets from configuration
if [ -f /data/iscsi/targets.tgt ]; then
    tgtadm --execute-admin-script /data/iscsi/targets.tgt
fi

# Show current targets
echo "Current targets:"
tgtadm --lld iscsi --mode target --op show
