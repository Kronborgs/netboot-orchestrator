# Quick Start: Deploy to Unraid

## ⚡ 5-Minute Deployment

### Prerequisites
- Unraid server with IP address (e.g., `192.168.1.50`)
- SSH enabled on Unraid (Settings > Management > SSH)
- Windows PC with PowerShell

---

## Option 1: PowerShell (From Windows) ⭐ Recommended

### Step 1: Open PowerShell
```powershell
# As Administrator
```

### Step 2: Run Deployment
```powershell
cd C:\Users\Kronborgs_LabPC\netboot-orchestrator

.\deploy-to-unraid.ps1 -UnraidHost 192.168.1.50
```

Replace `192.168.1.50` with your actual Unraid IP.

### Step 3: Confirm and Wait
- Type `yes` when prompted
- Wait 10-15 minutes for Docker build to complete
- Script will show access URLs when done

### Access Web UI
```
http://192.168.1.50:30000
```

---

## Option 2: SSH Terminal (Direct on Unraid or SSH Client)

### Step 1: Connect to Unraid
```bash
ssh root@192.168.1.50
```

### Step 2: Run Script
```bash
# First time
mkdir -p /mnt/user/appdata
cd /mnt/user/appdata
git clone https://github.com/Kronborgs/netboot-orchestrator.git netboot-orchestrator
cd netboot-orchestrator
bash deploy-to-unraid.sh

# Subsequent updates
cd /mnt/user/appdata/netboot-orchestrator
bash deploy-to-unraid.sh
```

### Step 3: Wait for Completion
- Build takes 10-15 minutes
- All data is automatically backed up
- Services start automatically

---

## Verify Deployment

### Check Web UI
```
Open browser: http://192.168.1.50:30000
```

### Check Services
```bash
# SSH into Unraid
ssh root@192.168.1.50
cd /mnt/user/appdata/netboot-orchestrator
docker-compose ps
```

Should show:
```
CONTAINER ID   IMAGE                                  STATUS
abc123...      netboot-orchestrator-api              Up 2 minutes
def456...      netboot-orchestrator-frontend        Up 2 minutes
ghi789...      netboot-orchestrator-tftp            Up 2 minutes
jkl012...      netboot-orchestrator-http-server     Up 2 minutes
mno345...      netboot-orchestrator-iscsi-target    Up 2 minutes
```

### Test API
```bash
curl http://192.168.1.50:8000/health
# Should return: {"status": "healthy"}
```

---

## Data Safety ✅

Your data is **100% protected**:

```
/mnt/user/appdata/netboot-orchestrator/
├── data/                    # 📁 Device profiles, images, settings
├── backup/                  # 📁 Automatic daily backups
└── docker-compose.yml       # 📁 Configuration
```

- ✅ Data backed up before each update
- ✅ Containers can be stopped without data loss
- ✅ Full rollback possible from backup folder

---

## Common Commands

| Command | Purpose |
|---------|---------|
| `.\deploy-to-unraid.ps1 -UnraidHost 192.168.1.50` | Deploy/update |
| `docker-compose ps` | Check service status |
| `docker-compose logs -f` | View live logs |
| `docker-compose restart` | Restart all services |
| `docker-compose down` | Stop services (data safe) |

---

## Access Points After Deploy

| Service | URL |
|---------|-----|
| **Web UI** | http://192.168.1.50:30000 |
| **API Docs** | http://192.168.1.50:8000/docs |
| **API Health** | http://192.168.1.50:8000/health |
| **TFTP Boot** | :69 (UDP) |
| **HTTP Boot** | :8080 |
| **iSCSI Target** | :3260 |

---

## Troubleshooting

### PowerShell: "SSH Not Found"
```powershell
# Enable SSH on Windows
Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
```

### SSH: "Connection Refused"
```
1. Check Unraid IP is correct
2. Enable SSH in Unraid settings
3. Wait 10 seconds after enabling SSH
4. Try: ping 192.168.1.50
```

### Unraid: "docker-compose not found"
```bash
# Install Docker (comes with Unraid by default)
# If missing, enable Docker in Unraid settings
```

### Port Already in Use (30000)
```bash
# Edit docker-compose.yml, change:
# 30000:3000 to 30001:3000
# Then redeploy
```

---

## Need More Help?

Full deployment guide with advanced options:
```
DEPLOYMENT_UNRAID.md
```

Features documentation:
```
FEATURES_INVENTORY.md
```

---

## Summary

| Step | Command |
|------|---------|
| **1. Open PowerShell** | Right-click → Run as Admin |
| **2. Navigate** | `cd C:\Users\...\netboot-orchestrator` |
| **3. Deploy** | `.\deploy-to-unraid.ps1 -UnraidHost 192.168.1.50` |
| **4. Confirm** | Type `yes` when prompted |
| **5. Access** | http://192.168.1.50:30000 |

**Total time:** 10-15 minutes (mostly Docker build)

---

✅ **Your Netboot Orchestrator is ready!**
