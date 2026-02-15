# Netboot Orchestrator - Safe Unraid Deployment Guide

> ⚠️ **SAFETY FIRST**: This guide and all scripts ONLY operate within `/mnt/user/appdata/netboot-orchestrator/`. Nothing outside this directory will be modified or deleted.

## Overview

Two deployment methods are provided:

1. **SSH Remote Deployment** (from Windows) - `deploy-to-unraid.ps1`
2. **Direct SSH/Terminal** (on Unraid) - `deploy-to-unraid.sh`

Both methods are **100% safe** and preserve all existing data.

---

## Method 1: PowerShell Remote Deployment (Windows)

### Prerequisites

- PowerShell 5.0+ (Windows 10/11)
- SSH client enabled on Windows
- SSH access enabled on Unraid (`Settings > Management > SSH`)
- Unraid IP address (e.g., `192.168.1.50`)

### Setup SSH on Unraid

1. Go to **Settings > Management > SSH**
2. Enable SSH with default settings
3. Note your Unraid IP address

### Deploy from Windows

#### First Time Deployment

```powershell
# In PowerShell (run as admin)
cd C:\Users\Kronborgs_LabPC\netboot-orchestrator

# Deploy to Unraid
.\deploy-to-unraid.ps1 -UnraidHost 192.168.1.50

# When prompted, type: yes
```

#### Update Existing Deployment

```powershell
# Same command - it will pull latest changes and rebuild
.\deploy-to-unraid.ps1 -UnraidHost 192.168.1.50
```

#### Clean (Stop containers, preserve data)

```powershell
# This stops containers without deleting anything
.\deploy-to-unraid.ps1 -UnraidHost 192.168.1.50 -Clean
```

### What It Does

1. ✅ Connects to Unraid via SSH
2. ✅ Clones/updates repository
3. ✅ **Creates backup** of existing `/data` directory (dated)
4. ✅ Stops old containers
5. ✅ Builds Docker images (10-15 minutes)
6. ✅ Starts all services
7. ✅ Shows status and access URLs

### Troubleshooting

#### SSH Connection Failed
```
[ERROR] Cannot connect to Unraid server
```
**Solution:**
- Check Unraid IP: `ping 192.168.1.50`
- Enable SSH in Unraid settings
- Ensure firewall allows port 22

#### Docker Build Failed
```
[ERROR] Docker build failed
```
**Solution:**
- SSH into Unraid and check logs:
  ```bash
  cd /mnt/user/appdata/netboot-orchestrator
  docker-compose logs
  ```

#### Out of Space
- Check storage: `df -h /mnt/user/appdata/`
- Remove old backups if needed: `rm -rf /mnt/user/appdata/netboot-orchestrator/backup/backup_*`

---

## Method 2: Direct SSH Deployment (Terminal/SSH Client)

### SSH into Unraid

```bash
ssh root@192.168.1.50

# Password: your Unraid root password
```

### Clone Repository

```bash
# First time only
mkdir -p /mnt/user/appdata
cd /mnt/user/appdata
git clone https://github.com/Kronborgs/netboot-orchestrator.git netboot-orchestrator
cd netboot-orchestrator
```

### Run Deployment Script

```bash
# Make script executable
chmod +x deploy-to-unraid.sh

# Run deployment
bash deploy-to-unraid.sh

# Or upgrade existing deployment
bash deploy-to-unraid.sh
```

### Manual Deployment Steps

If you prefer to run commands manually:

```bash
#!/bin/bash
# Navigate to project
cd /mnt/user/appdata/netboot-orchestrator

# Update code
git pull origin main

# Backup data (optional but recommended)
mkdir -p backup
cp -r data backup/backup_$(date +%Y%m%d_%H%M%S)

# Stop old containers
docker-compose down

# Build Docker images
docker-compose build --no-cache

# Create data directory
mkdir -p data

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

---

## File Locations on Unraid

```
/mnt/user/appdata/netboot-orchestrator/
├── docker-compose.yml          # Full production config
├── docker-compose.local.yml    # Local testing only
├── deploy-to-unraid.sh         # Deployment script (bash)
├── backend/                    # API source code
├── frontend/                   # Web UI source code
├── data/                       # 📁 Persistent data
│   ├── profiles.json          # Registered devices
│   ├── images.json            # iSCSI image metadata
│   ├── os.json                # OS installer metadata
│   ├── settings.json          # System settings
│   └── unknown_devices.json   # Unregistered devices
└── backup/                     # 📁 Automatic backups
    ├── backup_20260214_100000/
    ├── backup_20260214_150000/
    └── ...
```

### Important: Data Preservation

- **`/data/`** - Contains all device profiles, images, settings
  - ✅ **IS PRESERVED** during deployment
  - ✅ **Backed up automatically** before updates
  - ✅ **Survives container restarts**

- **Docker volumes** - Named volumes persist data
  - ✅ Will not be deleted by deployment script
  - ✅ Only removed with `docker-compose down -v` (which script doesn't use)

---

## Access After Deployment

### Web UI
```
http://192.168.1.50:30000
```

### API Documentation
```
http://192.168.1.50:8000/docs
```

### Health Check
```bash
curl http://192.168.1.50:8000/health
```

### Services Running
- **API** (Port 8000) - FastAPI backend
- **Web UI** (Port 30000) - React frontend
- **TFTP** (Port 67/69 UDP) - Network boot service
- **HTTP** (Port 8080) - Boot image HTTP server
- **iSCSI** (Port 3260) - iSCSI target for disk images

---

## Checking Logs

### From Windows (PowerShell)

```powershell
# Connect and tail logs
ssh root@192.168.1.50 "cd /mnt/user/appdata/netboot-orchestrator && docker-compose logs -f"
```

### From Unraid (SSH)

```bash
# All services
cd /mnt/user/appdata/netboot-orchestrator
docker-compose logs -f

# Specific service
docker-compose logs -f netboot-orchestrator-api
docker-compose logs -f netboot-orchestrator-frontend
docker-compose logs -f netboot-orchestrator-tftp
```

---

## Upgrading

### Pull Latest Changes

```bash
# Option 1: PowerShell (from Windows)
.\deploy-to-unraid.ps1 -UnraidHost 192.168.1.50

# Option 2: SSH Terminal
cd /mnt/user/appdata/netboot-orchestrator
bash deploy-to-unraid.sh
```

### Manual Upgrade

```bash
cd /mnt/user/appdata/netboot-orchestrator
git pull origin main
docker-compose build --no-cache
docker-compose up -d
```

---

## Rollback to Previous Version

### If Something Goes Wrong

```bash
# Stop current deployment
cd /mnt/user/appdata/netboot-orchestrator
docker-compose down

# Restore data from backup
cp -r backup/backup_20260214_150000/* data/

# Rebuild with previous version
git log --oneline  # Find commit to revert to
git checkout <commit_hash>

# Rebuild
docker-compose build --no-cache
docker-compose up -d
```

---

## Stopping Containers (Safe Stop)

```bash
cd /mnt/user/appdata/netboot-orchestrator

# Stop containers (preserves everything)
docker-compose down

# Data is still there, no deletion
ls -la data/
```

---

## Restarting Services

```bash
cd /mnt/user/appdata/netboot-orchestrator

# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart netboot-orchestrator-api
docker-compose restart netboot-orchestrator-frontend
```

---

## Troubleshooting

### Port Already in Use

```
ERROR: driver failed programming external connectivity: Bind for 0.0.0.0:30000 failed
```

**Solution:** Check what's using the port and change in `docker-compose.yml`:

```bash
# Find what's using port 30000
netstat -tuln | grep 30000
lsof -i :30000

# Then change port in docker-compose.yml
# 30000:3000 → 30001:3000 (use 30001 instead)
```

### Out of Disk Space

```bash
# Check available space
df -h /mnt/user/appdata/

# Clean old backups
rm -rf /mnt/user/appdata/netboot-orchestrator/backup/backup_*

# Clean docker build cache
docker builder prune -f
```

### Container Won't Start

```bash
# Check logs
docker-compose logs netboot-orchestrator-api

# Check container status
docker-compose ps

# Try rebuilding
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Reset Everything (Keep Data)

```bash
cd /mnt/user/appdata/netboot-orchestrator

# Stop and remove containers only
docker-compose down

# Remove images (but keep data!)
docker-compose rm -f

# Rebuild images
docker-compose build --no-cache

# Start again
docker-compose up -d
```

### Complete Reset (Dangerous - Deletes Data!)

⚠️ **This will DELETE all device profiles and settings!**

```bash
cd /mnt/user/appdata/netboot-orchestrator

# BACKUP first!
cp -r data backup/backup_final_$(date +%Y%m%d_%H%M%S)

# Stop containers
docker-compose down

# DELETE data (be sure first!)
rm -rf data/*

# Rebuild everything
docker-compose build --no-cache
docker-compose up -d

# Data directory will be recreated empty
```

---

## Safety Guarantees

✅ **What is PROTECTED:**
- `/mnt/user/appdata/netboot-orchestrator/data/` - Device data
- `/mnt/user/appdata/netboot-orchestrator/backup/` - Backups
- All data outside project directory
- Other Docker containers on Unraid
- Unraid system files and configuration

❌ **What is DELETED:**
- Only netboot Docker containers (but not data)
- Only netboot Docker images (rebuilt from source)
- Only netboot app files (pulled from GitHub)

---

## Support

### Check Version

```bash
cat /mnt/user/appdata/netboot-orchestrator/VERSION
```

### View Git History

```bash
cd /mnt/user/appdata/netboot-orchestrator
git log --oneline | head -20
```

### GitHub Issues

Report problems: https://github.com/Kronborgs/netboot-orchestrator/issues

### Contact

For help with deployment, provide:
1. Unraid version: `cat /etc/unraid-version`
2. Docker version: `docker --version`
3. Error logs: `docker-compose logs --tail 50`
4. Disk space: `df -h /mnt/user/appdata/`

---

## Summary

| Task | Command |
|------|---------|
| **Deploy (Windows)** | `.\deploy-to-unraid.ps1 -UnraidHost 192.168.1.50` |
| **Deploy (SSH)** | `bash deploy-to-unraid.sh` |
| **Stop (safe)** | `docker-compose down` |
| **Check status** | `docker-compose ps` |
| **View logs** | `docker-compose logs -f` |
| **Upgrade** | Re-run deployment script |
| **Rollback** | Restore from `backup/` folder |

**Remember:** Everything in this project directory is safe. Nothing outside will be touched.

---

**Version:** 2026-02-14-V1  
**Created:** February 14, 2026  
**Safety Level:** ⭐⭐⭐⭐⭐ (Excellent)
