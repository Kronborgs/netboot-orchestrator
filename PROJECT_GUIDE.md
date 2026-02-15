# Netboot Orchestrator - Project Guide

**Last Updated:** February 15, 2026  
**Current Focus:** Fixing x86/x64 PXE boot chain (DHCP loop issue)  
**Status:** 🔄 In Progress - Stage 2 bootloader testing

---

## 🎯 Project Summary

**Netboot Orchestrator** is a web-based system for network booting (SD-card-less boot) for both **x86/x64** and **ARM/Raspberry Pi** devices, with centralized management for OS installation and iSCSI disk booting.

### Original Vision (Full Spec)
- Boot ISO to install Windows/Linux over network
- Create and mount iSCSI disks for network boot
- Support x86/x64 architecture
- Support ARM (Raspberry Pi 4/5) architecture  
- Modern React-based WebUI for file and device management
- Fully containerized with Docker

### Current Reality (Actual Implementation)
- ✅ **x86/x64 PXE boot infrastructure** - TFTP + iPXE working, HTTP chainload implemented
- ✅ **API backend** (FastAPI) - Device registration endpoints ready
- ✅ **Frontend UI** (React) - File browser and setup guide deployed
- ✅ **TFTP server** (dnsmasq) - Serving iPXE bootloaders
- ✅ **HTTP server** (nginx) - Available for boot files
- 🔄 **iSCSI target** (tgtd) - Running but untested
- ⏳ **RPI4/5 support** - Not yet started
- ⏳ **Device registration UI** - Not yet started

---

## 🏗️ Architecture

### Network Setup
```
Device (10.10.50.x)  ←DHCP/PXE→  Unraid Server (192.168.1.50)
                                    ├─ TFTP (UDP 69)      ← undionly.kpxe
                                    ├─ HTTP (TCP 8000)    ← boot script via API
                                    ├─ iSCSI (TCP 3260)   ← disk images
                                    └─ Frontend (TCP 3000/30000)
```

### Boot Flow (Current x86/x64)

1. **Device DHCP** → Unifi router provides Option 67 = `undionly.kpxe`
2. **Stage 1** (TFTP): Device downloads `undionly.kpxe` from TFTP server
3. **Stage 1.5** (iPXE Init): undionly.kpxe loads and does DHCP again
   - ✅ **NEW FIX**: dnsmasq detects iPXE (option 175) → serves `boot.ipxe` instead of repeating undionly
4. **Stage 2** (HTTP Chainload): boot.ipxe chains to API endpoint:
   ```
   chain http://192.168.1.50:8000/api/v1/boot/ipxe/menu
   ```
5. **Menu Display**: API returns iPXE script showing boot options
6. **User selects** option → boots installer or iSCSI disk

### Boot Files Location (TFTP Root)
```
/data/tftp/
├── undionly.kpxe    (70KB - BIOS bootloader)
├── ipxe.efi         (9.2KB - UEFI bootloader)
├── boot.ipxe        (1.3KB - Stage 2 auto-chainload script)
└── boot-menu.ipxe   (658B - Fallback menu)
```

---

## 📋 Current Status

### ✅ Completed
- [x] TFTP service deployment (dnsmasq v2.90)
- [x] iPXE bootloader downloads (undionly.kpxe, ipxe.efi)
- [x] Boot script infrastructure (boot.ipxe, boot-menu.ipxe)
- [x] Multi-VLAN network routing (tested TCP/UDP)
- [x] API endpoint creation (`/api/v1/boot/ipxe/menu`)
- [x] Docker infrastructure (build, deployment, volumes)
- [x] Frontend UI (folder browser, setup guide)
- [x] **VLAN TFTP issue diagnosed** → solution: use HTTP instead
- [x] **API bug identified & fixed** → dict vs list iteration (commit 55da7dd)
- [x] **dnsmasq DHCP loop fixed** → serve boot.ipxe to iPXE clients (commit 1193e3e)

### 🔄 In Progress
- **x86/x64 PXE boot verification** (95% complete)
  - Awaiting HyperV test with fixed DHCP handling
  - All infrastructure ready, needs end-to-end test

### ⏳ Pending
- [ ] ARM/RPI4/5 U-Boot bootloader compilation
- [ ] Device MAC registration WebUI
- [ ] Device type selector (x86 vs RPI in menu)
- [ ] iSCSI boot testing
- [ ] OS installer upload and menu population

---

## 📁 Project Structure

```
netboot-orchestrator/
├── backend/                 # FastAPI REST API
│   ├── app/
│   │   ├── main.py         # FastAPI app initialization
│   │   ├── api/
│   │   │   └── v1.py       # Boot menu endpoint (FIXED)
│   │   └── services/
│   │       └── file_service.py  # OS installer listing
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                # React + TypeScript + Vite
│   ├── src/
│   │   ├── App.tsx
│   │   └── components/
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.ts
│
├── netboot/
│   ├── tftp/               # TFTP server (dnsmasq)
│   │   ├── Dockerfile
│   │   ├── config/
│   │   │   └── dnsmasq.conf       # DHCP-boot rules (UPDATED)
│   │   ├── entrypoint.sh          # Generates boot scripts
│   │   └── scripts/
│   │       └── embed.ipxe         # Old custom build (deprecated)
│   │
│   ├── http/               # HTTP server (nginx)
│   │   ├── Dockerfile
│   │   └── conf/
│   │       └── nginx.conf
│   │
│   └── iscsi/              # iSCSI target (tgtd)
│       ├── Dockerfile
│       └── entrypoint.sh
│
├── docker-compose.yml      # Orchestrates all services
├── data/                   # Persistent volume (created at runtime)
│   ├── tftp/              # TFTP root
│   ├── http/              # HTTP files
│   └── iscsi/images/      # iSCSI disk images
│
└── PROJECT_GUIDE.md        # ← You are here
```

---

## 🐳 Running the Project

### Prerequisites
- Docker & Docker Compose installed
- Windows/Linux/Mac
- Network access between boot VLAN (10.10.50.x) and Unraid server (192.168.1.50)

### Quick Start
```bash
cd c:\Users\Kronborgs_LabPC\netboot-orchestrator
docker-compose up -d
```

### Verify Services
```bash
docker ps
# Should show: api, tftp, http, iscsi-target, frontend
```

### Check Logs
```bash
# TFTP initialization
docker logs netboot-tftp --tail 20

# API startup
docker logs netboot-api --tail 20

# Test API endpoint
curl http://192.168.1.50:8000/api/v1/boot/ipxe/menu
```

---

## 🔧 Recent Fixes (Key Commits)

| Commit | Date | Issue | Fix |
|--------|------|-------|-----|
| `1193e3e` | Feb 15 | Infinite DHCP loop | Added `dhcp-boot` rules in dnsmasq to serve boot.ipxe to iPXE clients |
| `55da7dd` | Feb 15 | API 500 error | Fixed dict/list iteration in boot menu endpoint |
| `17ac220` | Feb 15 | TFTP chainload timeout | Changed from TFTP to HTTP for Stage 2 chainload |
| `e82c0f4` | Feb 15 | Custom build complexity | Simplified to use pre-built iPXE binaries |

---

## 🚨 Known Issues

### Issue #1: x86/x64 PXE Boot Loop (PARTIALLY FIXED)
**Symptom:** Device keeps downloading undionly.kpxe in infinite loop  
**Root Cause:** dnsmasq wasn't detecting iPXE clients, kept serving undionly.kpxe on second DHCP  
**Fix Applied:** Added `dhcp-boot=tag:ipxe,boot.ipxe` rule in dnsmasq.conf  
**Status:** ✅ Fixed (commit 1193e3e), needs testing

### Issue #2: TFTP Chainload Timeout (SOLVED)
**Symptom:** `chain tftp://192.168.1.50/boot-menu.ipxe` times out  
**Root Cause:** Multi-VLAN UDP routing not working from 10.10.50.x to 192.168.1.50  
**Solution:** Changed to HTTP chainload instead (TCP routing works)  
**Status:** ✅ Solved (commit 17ac220)

### Issue #3: API Returns 500 Error (FIXED)
**Symptom:** `http://192.168.1.50:8000/api/v1/boot/ipxe/menu` → 500 Internal Server Error  
**Root Cause:** `list_os_installer_files()` returns dict, code tried to iterate directly  
**Fix:** Extract `files` array from dict: `installers = result.get('files', [])`  
**Status:** ✅ Fixed (commit 55da7dd), API restarted

---

## 🧪 Testing Checklist

### HyperV Test (Next Step)
- [ ] Boot HyperV VM on 10.10.50 VLAN
- [ ] Verify undionly.kpxe downloads (Stage 1)
- [ ] Verify boot.ipxe auto-executes (Stage 1.5)
- [ ] Verify chainload to API via HTTP (Stage 2)
- [ ] See boot menu or error message in iPXE shell

### Success Indicators
- **Boot menu appears** → full chain working ✅
- **iPXE shell with "No OS installers available"** → API working but no images ✅
- **TFTP Aborted error** → DHCP loop still happening ❌
- **HTTP Connection Refused** → API not responding ❌

---

## 📚 Key Files to Know

| File | Purpose | Status |
|------|---------|--------|
| `netboot/tftp/config/dnsmasq.conf` | TFTP/DHCP config | ✅ Updated (fix: dhcp-boot rules) |
| `netboot/tftp/entrypoint.sh` | Boot script generation | ✅ Generates boot.ipxe + fallback |
| `backend/app/api/v1.py` | Boot menu API | ✅ Fixed (dict extraction) |
| `backend/app/services/file_service.py` | OS installer listing | ✅ Returns correct structure |
| `docker-compose.yml` | Service orchestration | ✅ All services configured |

---

## 🔗 Quick Links

- **Frontend:** http://192.168.1.50:30000
- **API Docs:** http://192.168.1.50:8000/docs
- **API Boot Menu Endpoint:** http://192.168.1.50:8000/api/v1/boot/ipxe/menu
- **GitHub Repo:** https://github.com/Kronborgs/netboot-orchestrator
- **Current Branch:** `main`

---

## 💡 How to Continue Development

### To debug active systems:
```bash
# Watch TFTP logs
docker logs -f netboot-tftp

# Check API responses
curl -v http://192.168.1.50:8000/api/v1/boot/ipxe/menu

# Enter TFTP container
docker exec -it netboot-tftp bash

# Check dnsmasq config
cat /tftp/config/dnsmasq.conf
```

### To make changes:
1. Edit file in `netboot/`, `backend/`, or `frontend/`
2. Rebuild affected service: `docker-compose build <service>`
3. Restart: `docker-compose up -d <service>`
4. Commit to git with clear message
5. Push to GitHub

### To understand the boot flow:
1. Read `netboot/tftp/entrypoint.sh` (boot.ipxe generation)
2. Read `backend/app/api/v1.py` (boot menu endpoint logic)
3. Check `/data/tftp/boot.ipxe` inside container (actual script served)
4. Check DHCP logs: `docker logs netboot-tftp | grep dhcp`

---

## 🎓 Developer Notes

- **Docker is required** - All services run in containers for consistency
- **Data persists in `/data` volume** - Mounted on Unraid or local drive
- **Changes auto-reload on restart** - No need for code recompilation
- **Git is the source of truth** - Always commit changes with clear messages
- **Test in HyperV first** - Boot VM on 10.10.50 VLAN before production devices
- **API has no auth yet** - Boot endpoints are public (intentional for boot-time)

---

## ❓ Common Questions

**Q: Why use HTTP for Stage 2 instead of TFTP?**  
A: Multi-VLAN UDP routing issue. TCP (HTTP) works cross-VLAN but TFTP (UDP) doesn't. Using HTTP for chainload avoids complications.

**Q: Why not use custom-compiled iPXE?**  
A: Standard iPXE binaries already support what we need. Custom builds add complexity with no benefit.

**Q: How does device registration work?**  
A: Not yet implemented. Will be WebUI → API → generates per-MAC TFTP config.

**Q: Can I use this now?**  
A: x86/x64 boot chain is almost ready (needs testing). RPI support not started. iSCSI target ready but untested.

---

**For more context, check Git log:**
```bash
git log --oneline -10
```

**To understand architecture decisions, see original spec in README.md or ask in code comments.**
