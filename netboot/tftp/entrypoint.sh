#!/bin/bash
set -e

echo "[TFTP] Starting dnsmasq TFTP server..."

mkdir -p /data/tftp/raspi /data/tftp/pxe

exec dnsmasq -C /tftp/config/dnsmasq.conf -d
