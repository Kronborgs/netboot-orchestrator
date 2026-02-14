#!/bin/bash
set -e

echo "[HTTP] Setting up directories..."
mkdir -p /data/http/{raspi/kernels/{default,test},os,ipxe}

echo "[HTTP] Starting nginx..."
exec nginx -g "daemon off;"
