# ====================================================
# Netboot Orchestrator - All-in-One Docker Image
# Designed by Kenneth Kronborg AI Team
# ====================================================
# Single container: iPXE + dnsmasq + tgtd + FastAPI + nginx
# Pulls from: ghcr.io/kronborgs/netboot-orchestrator:latest

# ====================================================
# Stage 1: Build custom iPXE with embedded boot script
# ====================================================
FROM ubuntu:22.04 AS ipxe-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc gcc-multilib make binutils perl liblzma-dev mtools \
    git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN git clone https://github.com/ipxe/ipxe.git --depth 1

COPY netboot/tftp/scripts/embed.ipxe /build/embed.ipxe

# Build BIOS iPXE binary with embedded script
RUN cd ipxe/src && make bin/undionly.kpxe EMBED=/build/embed.ipxe \
    && echo "Built undionly.kpxe: $(ls -lh bin/undionly.kpxe | awk '{print $5}')"

# ====================================================
# Stage 2: Build frontend (React/Vite)
# ====================================================
FROM node:18-alpine AS frontend-builder

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ .
RUN npm run build

# ====================================================
# Stage 3: Final all-in-one image
# ====================================================
FROM ubuntu:22.04

LABEL org.opencontainers.image.title="Netboot Orchestrator"
LABEL org.opencontainers.image.description="Network boot management for x86, x64 & Raspberry Pi - PXE/iPXE/iSCSI"
LABEL org.opencontainers.image.source="https://github.com/Kronborgs/netboot-orchestrator"
LABEL org.opencontainers.image.vendor="Kenneth Kronborg AI Team"
LABEL org.opencontainers.image.licenses="MIT"

RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    dnsmasq curl \
    tgt \
    nginx \
    net-tools iproute2 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Create directories
RUN mkdir -p /data/tftp /app/backend /etc/dnsmasq.d /opt/ipxe /iscsi-images

# Copy custom iPXE binary
COPY --from=ipxe-builder /build/ipxe/src/bin/undionly.kpxe /opt/ipxe/undionly.kpxe

# Copy frontend build to the path our nginx config expects
COPY --from=frontend-builder /app/dist /usr/share/nginx/html

# Copy nginx config for frontend (Ubuntu uses sites-enabled)
COPY frontend/nginx.conf /etc/nginx/sites-available/netboot
RUN rm -f /etc/nginx/sites-enabled/default && \
    ln -sf /etc/nginx/sites-available/netboot /etc/nginx/sites-enabled/netboot

# Copy FastAPI backend
COPY backend /app/backend/
COPY VERSION /app/VERSION

# Copy entrypoint
COPY netboot/entrypoint-backend.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /data/tftp

# Ports: TFTP=69, DHCP=67, API=8000, WebUI=30000, iSCSI=3260
EXPOSE 69/udp 67/udp 8000 30000 3260

ENTRYPOINT ["/entrypoint.sh"]
