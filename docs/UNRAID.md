# Unraid Deployment Guide

This guide covers deploying Netboot Orchestrator on Unraid OS systems for network boot testing and production use.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Networking Setup](#networking-setup)
- [Storage Configuration](#storage-configuration)
- [Troubleshooting](#troubleshooting)
- [Performance Tuning](#performance-tuning)

## Prerequisites

- **Unraid Version**: 6.12.0 or later
- **System Requirements**:
  - Minimum 4GB RAM (8GB recommended for this application)
  - At least 50GB free space in your array or cache
  - Docker service enabled (default in Unraid 6.12+)
  - Docker Compose installed on your system
  - Network connectivity for PXE booting devices

- **Required Knowledge**:
  - SSH access to your Unraid server
  - Basic networking concepts (DHCP, TFTP, NFS/iSCSI)
  - Understanding of Unraid share structure

## Installation

### Unraid Template (Recommended)

Use the project template XML for quick import in Unraid:

- Repo file: `docs/my-netboot-orchestrator.xml`
- Raw URL: `https://raw.githubusercontent.com/Kronborgs/netboot-orchestrator/main/docs/my-netboot-orchestrator.xml`

### Step 1: Enable Required Unraid Services

1. Access your Unraid web GUI (typically `http://<unraid-ip>:6080`)
2. Go to **Settings → Docker**
   - Ensure Docker is enabled
   - Verify Docker service is running

3. Go to **Settings → Network**
   - Note your Unraid server's IP address
   - Verify DHCP server settings (if hosting your own)

### Step 2: Prepare Storage

The application requires persistent storage for:
- Boot images and OS installers (5-50GB depending on images)
- Device profiles and configurations
- Kernel sets and boot files

**Option A: Using Array Storage** (Recommended for production)

```bash
# SSH into Unraid
ssh root@<unraid-ip>

# Create necessary directories
mkdir -p /mnt/user/netboot-orchestrator/data
mkdir -p /mnt/user/netboot-orchestrator/iscsi-targets
mkdir -p /mnt/user/netboot-orchestrator/tftp
mkdir -p /mnt/user/netboot-orchestrator/http

# Set permissions
chmod -R 755 /mnt/user/netboot-orchestrator
```

**Option B: Using Cache Storage** (For testing)

```bash
mkdir -p /mnt/cache/netboot-orchestrator/data
mkdir -p /mnt/cache/netboot-orchestrator/iscsi-targets
chmod -R 755 /mnt/cache/netboot-orchestrator
```

### Step 3: Deploy Application

1. **SSH into your Unraid server**:
```bash
ssh root@<unraid-ip>
```

2. **Clone or download the repository**:
```bash
cd /tmp
git clone https://github.com/yourusername/netboot-orchestrator.git
cd netboot-orchestrator
```

3. **Modify docker-compose for Unraid paths**:

Edit `docker-compose.yml` and replace volume paths:

```yaml
volumes:
  # Change from: ./data:/app/data
  # To:
  - /mnt/user/netboot-orchestrator/data:/app/data
  
  # For other volumes:
  - /mnt/user/netboot-orchestrator/iscsi-targets:/iscsi-targets
  - /mnt/user/netboot-orchestrator/tftp:/tftp
  - /mnt/user/netboot-orchestrator/http:/http
```

4. **Create environment file**:
```bash
cp .env.example .env
# Edit .env with your settings
nano .env
```

5. **Start the services**:
```bash
docker-compose up -d
```

6. **Verify deployment**:
```bash
docker-compose ps
docker-compose logs -f
```

## Configuration

### API Server Configuration

The FastAPI backend will be available at `http://<unraid-ip>:8000`

Create or modify `.env`:
```bash
# Backend configuration
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
BACKEND_DEBUG=false

# Frontend configuration
FRONTEND_PORT=30000

# Netboot configuration
TFTP_SERVER_IP=<your-unraid-ip>
HTTP_SERVER_ADDR=<your-unraid-ip>
ISCSI_TARGET_IP=<your-unraid-ip>
```

### Persistent Configuration Files

Configuration persists in `/mnt/user/netboot-orchestrator/data/`:

```
data/
├── profiles.json      # Device registration and MAC addresses
├── images.json        # Available boot images
├── os.json            # OS installers
└── settings.json      # Global settings
```

You can edit these JSON files directly or use the web interface.

## Networking Setup

### DHCP Configuration (If Using Unraid DHCP)

If you're using Unraid's DHCP server:

1. **Go to Settings → Network Settings**
2. Configure **DHCP Server** if not already enabled
3. Add DHCP options for PXE:

For **dnsmasq** (Unraid's default), edit `/boot/config/dhcpd.conf`:

```conf
# PXE Boot Configuration
dhcp-option=vendor:PXEClient,6,<unraid-ip>
dhcp-option=option:tftp-server,<unraid-ip>
dhcp-option=option:bootfile-name,lpxelinux.0
```

### Firewall Rules

Ensure these ports are accessible from your network:

```
30000/tcp  - Frontend UI
8000/tcp   - API Server
69/udp     - TFTP (netboot)
80/tcp     - HTTP (boot files)
3260/tcp   - iSCSI Target
```

In Unraid Settings → Firewall, add these rules or verify they're not blocked.

### Network Interface Configuration

Ensure your Netboot Orchestrator container can access your network:

```yaml
# In docker-compose.yml
services:
  api:
    network_mode: "bridge"  # Or "host" for direct access
    # ...
```

## Storage Configuration

### Direct Block Device Access (For iSCSI)

For iSCSI targets to work properly:

1. **Create iSCSI target storage**:
```bash
# Create sparse image files for iSCSI targets
cd /mnt/user/netboot-orchestrator/iscsi-targets

# Example: 50GB image for Raspberry Pi OS
dd if=/dev/zero of=raspios-install.img bs=1G count=50 seek=0

# Example: 100GB image for Ubuntu on x86
dd if=/dev/zero of=ubuntu-install.img bs=1G count=100 seek=0

# Set permissions
chmod 666 *.img
```

2. **Or use actual partitions** (Advanced):
```bash
# If you have dedicated drives for iSCSI
lsblk  # View available devices
# Configure TGT daemon to use /dev/sdX directly
```

### Backup Recommendations

```bash
# Backup configuration daily
tar -czf /mnt/user/backups/netboot-config-$(date +%Y%m%d).tar.gz \
  /mnt/user/netboot-orchestrator/data/

# Backup iSCSI images monthly
rsync -av /mnt/user/netboot-orchestrator/iscsi-targets/ \
  /mnt/backup/netboot-iscsi-$(date +%Y%m%d)/
```

## Troubleshooting

### Services Won't Start

```bash
# Check Docker daemon
systemctl status docker

# Check docker-compose syntax
docker-compose config

# View detailed logs
docker-compose logs --tail=50

# Restart specific service
docker-compose restart api
docker-compose restart tftp
```

### Network Connectivity Issues

```bash
# From Unraid server, test connectivity
ping <device-ip>

# Test TFTP access
tftp -c get /boot/lpxelinux.0 <unraid-ip>

# Test HTTP access
curl http://<unraid-ip>:80/boot/

# Test iSCSI discovery
iscsiadm -m discovery -t sendtargets -p <unraid-ip>:3260
```

### Performance Issues

Check resource usage:

```bash
# Monitor Docker container stats
docker stats

# Check Unraid system status
# Via GUI: Dashboard tab shows CPU, RAM, network usage

# View storage I/O
iostat -x 1 10
```

If slow, consider:
- Moving data to array instead of cache
- Increasing RAM allocated to Docker
- Using dedicated network interfaces

### Device Not Registering

```bash
# Check device check-in logs
curl http://localhost:8000/api/v1/devices

# View API logs
docker-compose logs api

# Verify MAC address in profiles.json
cat /mnt/user/netboot-orchestrator/data/profiles.json | grep -i "your-mac"
```

### iSCSI Target Not Found

```bash
# Verify TGT is running
docker-compose exec iscsi systemctl status tgt

# Check TGT configuration
docker-compose exec iscsi tgtadm --lld iscsi --op show --mode target

# View iSCSI target details
docker-compose logs iscsi
```

### Storage Space Issues

```bash
# Check available space
df -h /mnt/user/netboot-orchestrator

# Find large files
du -sh /mnt/user/netboot-orchestrator/* | sort -hr

# Check Docker disk usage
docker system df
```

## Performance Tuning

### I/O Optimization

For faster boot image downloads:

```bash
# Increase TFTP/HTTP buffer sizes in docker-compose.yml
# Add to nginx service:
environment:
  - NGINX_WORKER_PROCESSES=auto
  - NGINX_WORKER_CONNECTIONS=4096
```

### Memory Optimization

```bash
# In docker-compose.yml, set memory limits
services:
  api:
    mem_limit: 512m
    memswap_limit: 1g
  frontend:
    mem_limit: 256m
```

### Network Optimization

Use a dedicated network interface if available:

```yaml
networks:
  netboot:
    driver: bridge
services:
  api:
    networks:
      - netboot
```

### Cache Management

```bash
# Unraid-specific: Place frequently accessed images on cache
# Move populated data to cache for faster access
mv /mnt/user/netboot-orchestrator/tftp/* /mnt/cache/netboot-orchestrator/tftp/
```

## Monitoring & Maintenance

### Regular Maintenance Tasks

```bash
# Weekly: Check for issues
docker-compose ps
docker-compose logs --since 7d

# Monthly: Backup configuration
tar -czf /mnt/user/backups/netboot-$(date +%Y%m%d).tar.gz \
  /mnt/user/netboot-orchestrator/

# Quarterly: Update to latest version
cd /path/to/netboot-orchestrator
git pull
docker-compose pull
docker-compose up --build -d
```

### Unraid Notifications

To get notifications about issues on your Unraid server:

```bash
# Enable Syslog notifications in Unraid GUI
# Settings → Notifications → Syslog
```

## Testing Checklist

Before using in production, verify:

- [ ] All containers running: `docker-compose ps`
- [ ] API responsive: `curl http://localhost:8000/health`
- [ ] Frontend accessible: Open in browser to `http://<ip>:30000`
- [ ] TFTP working: Test boot file access
- [ ] HTTP working: Download boot image
- [ ] iSCSI working: Test target connection
- [ ] Storage accessible: Can read/write files
- [ ] Network connectivity: Ping test devices
- [ ] Device registration: Add a test device
- [ ] Boot workflow: Test actual boot from a device

## Security Considerations for Unraid

1. **SSH Security**:
   - Use SSH keys instead of passwords
   - Restrict SSH to local network only
   - Disable root login, use dedicated admin account

2. **API Security**:
   - Consider adding authentication to API endpoints
   - Use HTTPS in production (add reverse proxy)
   - Restrict API access to local network

3. **Storage Security**:
   - Use Unraid's Share Access Control for `/mnt/user/netboot-orchestrator`
   - Enable encryption for sensitive images
   - Regular backups to secondary storage

4. **Network Security**:
   - Enable Unraid firewall
   - Restrict DHCP/PXE to trusted VLANs
   - Use MAC filtering if needed

## Advanced: Using Unraid UniFi Controller Integration

If you have Unraid UniFi on the same system:

```bash
# Configure UniFi to use netboot-orchestrator's DHCP
# In UniFi controller: Settings → Services → DHCP
# Set DHCP server to <unraid-ip>:67
```

## Getting Help

For Unraid-specific issues:
- Check Unraid forums: https://forums.unraid.net
- Unraid documentation: https://docs.unraid.net
- Netboot Orchestrator issues: https://github.com/yourusername/netboot-orchestrator/issues

## Next Steps

1. [Verify installation](#testing-checklist)
2. [Read the Boot Flow documentation](../docs/BOOT_FLOW.md)
3. [Add your first device via the Web UI](../docs/DATA_STRUCTURE.md#device-registration)
4. [Configure boot images and OS installers](../docs/DATA_STRUCTURE.md#image-management)

---

**Last Updated**: 2026-02-14  
**For Issues**: Report on GitHub with `[Unraid]` prefix in title
