# Deployment Guide

Production deployment instructions for RPi Netboot Orchestrator on various platforms.

## Hardware Requirements

### Minimum
- 2 CPU cores
- 2GB RAM
- 50GB storage
- 1Gbps network interface

### Recommended
- 4+ CPU cores
- 8GB+ RAM
- 500GB+ storage (varies with image count)
- 10Gbps network interface
- Redundant storage (RAID 1 or better)

## Pre-Deployment Checklist

- [ ] Verify Docker and Docker Compose installed
- [ ] Check network connectivity and DHCP server
- [ ] Ensure port 69 (TFTP), 80/8080 (HTTP), 3260 (iSCSI) available
- [ ] Prepare SSL certificates (if using TLS)
- [ ] Create backups of any existing configs
- [ ] Test network boot on a test client

## Linux Server Deployment

### Ubuntu 22.04 / Debian 12

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y docker.io docker-compose

# Add user to docker group (optional, for non-root usage)
sudo usermod -aG docker $USER
newgrp docker

# Clone repository
git clone https://github.com/Kronborgs/netboot-orchestrator.git
cd netboot-orchestrator

# Run setup
bash setup.sh

# Configure environment
cp .env.example .env
nano .env  # Edit configuration

# Create data directories with proper permissions
sudo mkdir -p /data/{http/{raspi/kernels/{default,test},os,ipxe},tftp/{raspi,pxe},iscsi/images}
sudo chown -R 1000:1000 /data

# Start services
docker-compose up -d

# Verify services
docker-compose ps
curl http://localhost:8000/health
```

### Unraid Integration

```bash
# SSH into Unraid
ssh root@your-unraid-ip

# Download and run setup
bash <(curl -fsSL https://raw.githubusercontent.com/Kronborgs/netboot-orchestrator/main/unraid-setup.sh)

# Or use the provided script
curl -fsSL https://raw.githubusercontent.com/Kronborgs/netboot-orchestrator/main/unraid-deploy.ps1 > deploy.ps1
# Run on Windows connected to Unraid
.\deploy.ps1 -UnraidHost your-unraid-ip
```

## Docker Swarm Deployment

For multi-node clusters:

```bash
# Initialize swarm (on manager node)
docker swarm init --advertise-addr <manager-ip>

# Create overlay network
docker network create --driver overlay netboot-overlay

# Deploy stack
docker stack deploy -c docker-compose.yml netboot-orchestrator

# Check status
docker stack ps netboot-orchestrator

# Scale services (if needed)
docker service scale netboot-orchestrator_api=3 netboot-orchestrator_http-server=2
```

## Kubernetes Deployment

Create `netboot-orchestrator-helm-values.yaml`:

```yaml
replicaCount: 1

image:
  repository: netboot-orchestrator
  tag: latest

service:
  type: LoadBalancer
  ports:
    http: 80
    api: 8000
    tftp: 69
    iscsi: 3260

persistence:
  enabled: true
  size: 500Gi
  storageClass: "fast-ssd"
  mountPath: /data

resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "8Gi"
    cpu: "4000m"
```

Deploy:

```bash
helm install netboot-orchestrator ./helm -f netboot-orchestrator-helm-values.yaml
```

## SSL/TLS Configuration

### Self-signed Certificate

```bash
# Generate certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /data/tls.key \
  -out /data/tls.crt

# Set permissions
chmod 600 /data/tls.key /data/tls.crt
```

### Update nginx.conf

```nginx
server {
  listen 443 ssl http2;
  ssl_certificate /data/tls.crt;
  ssl_certificate_key /data/tls.key;
  
  # SSL settings
  ssl_protocols TLSv1.2 TLSv1.3;
  ssl_ciphers HIGH:!aNULL:!MD5;
  
  # ... rest of configuration
}

# Redirect HTTP to HTTPS
server {
  listen 80;
  return 301 https://$host$request_uri;
}
```

## Firewall Configuration

### Required Ports

```bash
# UFW (Ubuntu)
sudo ufw allow 69/udp      # TFTP
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 8000/tcp    # API
sudo ufw allow 8080/tcp    # HTTP (alt)
sudo ufw allow 3260/tcp    # iSCSI
sudo ufw allow 3260/udp    # iSCSI alt
sudo ufw allow 67/udp      # DHCP
sudo ufw enable
```

### iptables Rules

```bash
# Allow TFTP
iptables -A INPUT -p udp --dport 69 -j ACCEPT

# Allow HTTP
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 8080 -j ACCEPT

# Allow API
iptables -A INPUT -p tcp --dport 8000 -j ACCEPT

# Allow iSCSI
iptables -A INPUT -p tcp --dport 3260 -j ACCEPT

# Allow DHCP
iptables -A INPUT -p udp --dport 67 -j ACCEPT
iptables -A INPUT -p udp --dport 68 -j ACCEPT
```

## Monitoring Setup

### Prometheus Metrics (Future)

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'netboot-orchestrator'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### ELK Stack Logging

```bash
docker-compose -f docker-compose.monitoring.yml up -d

# Access Kibana
# http://localhost:5601
```

## Backup Strategy

### Automated Backup

```bash
#!/bin/bash
# /usr/local/bin/netboot-backup.sh

BACKUP_DIR="/backup/netboot"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup data volume
docker run --rm \
  -v netboot-orchestrator_data:/data \
  -v $BACKUP_DIR:/backup \
  busybox tar czf /backup/netboot_$DATE.tar.gz -C / data

# Keep last 30 days
find $BACKUP_DIR -mtime +30 -delete

echo "Backup completed: netboot_$DATE.tar.gz"
```

Schedule with cron:

```
0 2 * * * /usr/local/bin/netboot-backup.sh >> /var/log/netboot-backup.log 2>&1
```

### Restore from Backup

```bash
# Stop services
docker-compose down

# Restore backup
docker run --rm \
  -v netboot-orchestrator_data:/data \
  -v /backup:/backup \
  busybox tar xzf /backup/netboot_20240214_020000.tar.gz -C /

# Start services
docker-compose up -d
```

## High Availability Setup

### Multi-Node Architecture

```
┌─────────────────┐
│  Load Balancer  │
│  (nginx/HAProxy)│
└────────┬────────┘
         │
    ┌────┴────┐
    │          │
┌───▼──┐   ┌──▼───┐
│API-1 │   │API-2 │
└───┬──┘   └──┬───┘
    │    ┌─────┘
    │    │
    ▼    ▼
┌──────────────────┐
│  Shared Storage  │
│  (NFS/SMB/GlusterFS)
└──────────────────┘
```

Configuration:

```yaml
# docker-compose-ha.yml
services:
  api:
    build: ./backend
    replicas: 3
    ports:
      - "8000"  # Dynamic port assignment
    volumes:
      - shared_data:/data
    environment:
      - DATABASE_BACKEND=redis  # Shared cache

  loadbalancer:
    image: nginx:latest
    ports:
      - "8000:8000"
    volumes:
      - ./nginx-lb.conf:/etc/nginx/conf.d/default.conf

volumes:
  shared_data:
    driver: local-persist
```

## Performance Tuning

### System Parameters

```bash
# /etc/sysctl.conf
net.ipv4.ip_forward = 1
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.core.netdev_max_backlog = 65535

# Apply
sysctl -p
```

### Docker Configuration

```json
{
  "/etc/docker/daemon.json": {
    "storage-driver": "overlay2",
    "log-driver": "json-file",
    "log-opts": {
      "max-size": "10m",
      "max-file": "3"
    }
  }
}
```

## Troubleshooting Production Deployments

### Check Service Status

```bash
# All services
docker-compose ps
docker-compose logs

# Individual service
docker-compose logs api
docker-compose logs tftp

# Real-time
docker-compose logs -f
```

### Network Connectivity Issues

```bash
# Test TFTP
timeout 5 bash -c 'cat < /dev/null > /dev/udp/localhost/69' && echo "TFTP OK"

# Test HTTP
curl -I http://localhost:8000/health
curl -I http://localhost:8080/health

# Test iSCSI
telnet localhost 3260
```

### Disk Space Issues

```bash
# Check usage
df -h /data
du -sh /data/*

# Clean old images
docker system prune -a

# Remove old backups
find /backup -mtime +30 -delete
```

### Memory Issues

```bash
# Monitor docker
docker stats

# Check container limits
docker inspect netboot-api | grep -A 5 Memory

# Increase if needed (update docker-compose.yml)
# Add to service: mem_limit: 2g
```

## Security Hardening

### Update All Components

```bash
docker-compose down
docker pull $(docker-compose config --services | xargs -I {} docker inspect {} --format='{{.Config.Image}}')
docker-compose up -d
```

### Network Isolation

```bash
# Create dedicated network
docker network create --driver bridge --subnet=172.20.0.0/16 netboot-prod

# Use in docker-compose.yml
networks:
  netboot:
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### User Permissions

```bash
# Don't run as root
docker run --user 1000:1000 ...

# Or use Docker security options
docker run --security-opt=no-new-privileges ...
```

## Post-Deployment Validation

```bash
# Check all services
#!/bin/bash
echo "Checking API..."
curl http://localhost:8000/health

echo "Checking Frontend..."
curl http://localhost:3000/

echo "Checking HTTP Server..."
curl http://localhost:8080/health

echo "Testing TFTP..."
timeout 5 bash -c 'cat < /dev/null > /dev/udp/localhost/69'

echo "All checks passed! ✓"
```

## Support and Documentation

- Check Docker logs for errors
- Review documentation in `/docs`
- Test with known working device first
- Ensure network configuration matches docs
