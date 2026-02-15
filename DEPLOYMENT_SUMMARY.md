# Netboot Orchestrator - Unraid Deployment Summary

## ✅ What Was Created

### 🚀 Deployment Scripts

#### 1. **deploy-to-unraid.sh** (Bash)
- **Location:** `/netboot-orchestrator/deploy-to-unraid.sh`
- **Purpose:** Direct deployment on Unraid via SSH terminal
- **Usage:** 
  ```bash
  ssh root@192.168.1.50
  cd /mnt/user/appdata/netboot-orchestrator
  bash deploy-to-unraid.sh
  ```

#### 2. **deploy-to-unraid.ps1** (PowerShell) ⭐ RECOMMENDED
- **Location:** `C:\Users\Kronborgs_LabPC\netboot-orchestrator\deploy-to-unraid.ps1`
- **Purpose:** Remote deployment from Windows via PowerShell
- **Usage:**
  ```powershell
  .\deploy-to-unraid.ps1 -UnraidHost 192.168.1.50
  ```
- **Features:**
  - ✅ SSH connection validation
  - ✅ Automatic backup creation
  - ✅ Progress indicators
  - ✅ Error handling
  - ✅ 100% safe (no data deletion)

### 📚 Documentation

#### 1. **QUICKSTART_UNRAID.md** (Quick Reference)
- **5-minute quick-start guide**
- **Simple step-by-step instructions**
- **Verification commands**
- **Common troubleshooting**

#### 2. **DEPLOYMENT_UNRAID.md** (Complete Guide)
- **300+ lines of detailed documentation**
- **Two deployment methods (PowerShell & SSH)**
- **File locations and data preservation**
- **Troubleshooting guide**
- **Rollback instructions**
- **Safety guarantees**
- **Manual deployment steps**

#### 3. **README.md** (Updated)
- Links to deployment guides
- Quick access to all documentation

---

## 🛡️ Safety Guarantees

### ✅ PROTECTED (Won't be deleted)
- `/mnt/user/appdata/netboot-orchestrator/data/` - Device profiles, images, settings
- `/mnt/user/appdata/netboot-orchestrator/backup/` - Automatic backups
- All data with device UUID outside the project directory
- Other Docker containers on Unraid
- Unraid system files and configuration

### ❌ ONLY CHANGED (For deployment)
- Netboot Docker containers (can be stopped/restarted)
- Netboot Docker images (rebuilt from source code)
- Netboot application files (pulled from GitHub)

**Bottom line: NO DATA WILL BE LOST**

---

## 🚀 How to Deploy

### Step 1: Prerequisites
- [ ] Unraid server running
- [ ] Know Unraid IP address (e.g., `192.168.1.50`)
- [ ] SSH enabled in Unraid settings
- [ ] Windows PowerShell available

### Step 2: Open PowerShell (As Admin)
```powershell
# Right-click PowerShell → Run as Administrator
```

### Step 3: Navigate to Project Directory
```powershell
cd C:\Users\Kronborgs_LabPC\netboot-orchestrator
```

### Step 4: Run Deployment Script
```powershell
# Replace 192.168.1.50 with your actual Unraid IP
.\deploy-to-unraid.ps1 -UnraidHost 192.168.1.50
```

### Step 5: Confirm Deployment
When prompted:
```
Continue with deployment? (yes/no): yes
```

### Step 6: Wait for Completion
- Docker build takes 10-15 minutes
- Script shows progress
- Access URL provided when done

### Step 7: Access Web UI
```
http://192.168.1.50:30000
```

---

## 📋 What the Deploy Script Does

```
1. Validates SSH connection to Unraid
2. Clones/updates repository from GitHub
3. Creates DATED BACKUP of current data
   └─ Stored in: /mnt/user/appdata/netboot-orchestrator/backup/
4. Stops any running containers
5. Builds Docker images (fresh, no caching)
   └─ 5 services: API, Web UI, TFTP, HTTP, iSCSI
6. Creates /data directory
7. Starts all services
8. Shows status and access URLs
```

**Total time:** 10-15 minutes (mostly Docker build)

---

## 🔄 Optional Commands

### Backup Before Deployment
```powershell
# The script asks you automatically
# Choose 'yes' to create backup
```

### Update Existing Deployment
```powershell
# Same command - pulls latest code and rebuilds
.\deploy-to-unraid.ps1 -UnraidHost 192.168.1.50
```

### Stop Containers (Preserve Data)
```powershell
# SSH and run:
ssh root@192.168.1.50
cd /mnt/user/appdata/netboot-orchestrator
docker-compose down

# All data is safe, nothing deleted
```

### Clean Deployment
```powershell
# Using the script with -Clean flag
.\deploy-to-unraid.ps1 -UnraidHost 192.168.1.50 -Clean

# This stops containers only (data preserved)
```

### Manual Deployment (If Script Fails)
```bash
# SSH into Unraid: ssh root@192.168.1.50
cd /mnt/user/appdata/netboot-orchestrator
git pull origin main
docker-compose build --no-cache
docker-compose up -d
docker-compose ps
```

---

## ✅ Verification After Deploy

### Check Web UI
```
Open browser: http://192.168.1.50:30000
```
Should show dashboard with empty device list.

### Check Services Status
```powershell
# SSH into Unraid and run:
docker-compose ps
```
Should show 5 containers all with status "Up X minutes".

### Test API
```bash
curl http://192.168.1.50:8000/health
# Response: {"status": "healthy"}
```

### View Logs
```bash
cd /mnt/user/appdata/netboot-orchestrator
docker-compose logs -f netboot-orchestrator-api
```

---

## 🆘 Troubleshooting

### Problem: "SSH Command Not Found"
```powershell
# Enable SSH on Windows 10/11:
Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
```

### Problem: "Cannot Connect to 192.168.1.50"
```
1. Verify IP is correct
2. Enable SSH in Unraid: Settings > Management > SSH
3. Ping Unraid: ping 192.168.1.50
4. Check firewall allows port 22
```

### Problem: "Docker Build Failed"
```bash
# SSH into Unraid and check logs:
cd /mnt/user/appdata/netboot-orchestrator
docker-compose logs | tail -50
```

### Problem: "Port 30000 Already in Use"
```bash
# Edit docker-compose.yml:
# Change: "30000:3000"
# To: "30001:3000"
# Then redeploy
```

---

## 📂 File Structure After Deploy

```
/mnt/user/appdata/netboot-orchestrator/
├── docker-compose.yml                    # Production config ← USED
├── docker-compose.local.yml             # Local testing only
├── deploy-to-unraid.sh                  # This deployment script
├── backend/                              # API source code
│   └── app/
│       ├── models.py
│       ├── database.py
│       ├── main.py
│       ├── api/
│       │   ├── v1.py (comprehensive endpoints)
│       │   ├── boot.py
│       │   └── __init__.py
│       └── services/
│           └── file_service.py
├── frontend/                             # Web UI source code
│   └── src/
│       ├── components/
│       │   ├── ImageManagement.tsx
│       │   ├── OsInstallerList.tsx
│       │   ├── UnknownDeviceWizard.tsx
│       │   └── DeviceList.tsx
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   └── Inventory.tsx
│       └── styles/
│           └── index.css (dark mode, branding)
│
├── data/                                 # 📁 PERSISTENT DATA
│   ├── profiles.json                    # Device profiles
│   ├── images.json                      # iSCSI image metadata
│   ├── os.json                          # OS installer metadata
│   ├── settings.json                    # System settings
│   └── unknown_devices.json             # Unregistered devices
│
└── backup/                               # 📁 AUTOMATIC BACKUPS
    ├── backup_20260214_100000/
    ├── backup_20260214_110000/
    └── ...
```

---

## 🎯 What Runs After Deploy

### 5 Docker Services:

1. **netboot-orchestrator-api** (Port 8000)
   - FastAPI backend
   - REST API endpoints
   - Device, image, and OS management

2. **netboot-orchestrator-frontend** (Port 30000)
   - React web UI
   - Dark mode interface
   - Dashboard and inventory

3. **netboot-orchestrator-tftp** (Port 67/69 UDP)
   - TFTP boot server
   - PXE boot service
   - Boot file serving

4. **netboot-orchestrator-http-server** (Port 8080)
   - HTTP boot server
   - Boot image hosting
   - ISO serving for installation

5. **netboot-orchestrator-iscsi-target** (Port 3260)
   - iSCSI target server
   - Disk image serving
   - Network boot target

---

## 🔐 Data Backup Locations

### Automatic Backups Created
```
/mnt/user/appdata/netboot-orchestrator/backup/
├── backup_20260214_100000/    ← Before first deploy
├── backup_20260214_110000/    ← Before upgrade 1
├── backup_20260214_120000/    ← Before upgrade 2
└── ...
```

### Restore from Backup
```bash
# If something goes wrong:
cd /mnt/user/appdata/netboot-orchestrator

# Restore specific backup
cp -r backup/backup_20260214_100000/* data/

# Or check backup contents first
ls -la backup/backup_20260214_100000/
cat backup/backup_20260214_100000/profiles.json
```

---

## 📞 Support

### Check Current Version
```bash
cat /mnt/user/appdata/netboot-orchestrator/VERSION
# Output: 2026-02-14-V1
```

### View Commit History
```bash
cd /mnt/user/appdata/netboot-orchestrator
git log --oneline | head -10
```

### GitHub Repository
```
https://github.com/Kronborgs/netboot-orchestrator
```

### Documentation Files
```
- QUICKSTART_UNRAID.md      ← Start here
- DEPLOYMENT_UNRAID.md      ← Full guide
- FEATURES_INVENTORY.md     ← Feature details
- README.md                 ← Project overview
```

---

## ⚡ TL;DR (Too Long, Didn't Read)

1. Open PowerShell as Admin
2. Run: `.\deploy-to-unraid.ps1 -UnraidHost 192.168.1.50`
3. Answer `yes` to confirm
4. Wait 10-15 minutes
5. Access: `http://192.168.1.50:30000`
6. Done! ✅

**All data is safe. Nothing will be deleted.**

---

## Version Information

**Netboot Orchestrator v2026-02-14-V1**

- ✅ Complete inventory management system
- ✅ Dark mode UI with brand colors
- ✅ Image management, OS installers, device wizard
- ✅ Safe Unraid deployment scripts
- ✅ Automatic backup and rollback support
- ✅ Full documentation and guides

**Last Updated:** February 14, 2026
**Repository:** https://github.com/Kronborgs/netboot-orchestrator
