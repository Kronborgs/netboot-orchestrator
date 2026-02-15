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
- **x86/x64 PXE boot verification** (80% complete - IMPROVEMENTS DEPLOYED)
  - ✅ Stage 1: undionly.kpxe downloads successfully (70KB) 
  - ✅ Stage 1.5: undionly.kpxe boots (iPXE shell accessible via Ctrl+B)
  - ✅ Stage 2: boot.ipxe now has improved timeout & retry logic (commit c8b058d)
  - **Improvements Deployed:**
    - Uses DHCP-provided `${next-server}` instead of hardcoding IP
    - Added 10-second timeout on HTTP chainload
    - Auto-retry with DHCP renewal if first attempt fails
    - Better diagnostics showing which server is being used
  - **Next Test:** HyperV boot should now handle timeouts better and retry if needed

### ⏳ Pending
- [ ] Fix HTTP chainload network connectivity (blocking test)
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
| `c8b058d` | Feb 15 | HTTP chainload timeout | Added 10s timeout, DHCP retry, $next-server variable, better diagnostics |
| `1193e3e` | Feb 15 | Infinite DHCP loop | Added `dhcp-boot` rules in dnsmasq to serve boot.ipxe to iPXE clients |
| `55da7dd` | Feb 15 | API 500 error | Fixed dict/list iteration in boot menu endpoint |
| `17ac220` | Feb 15 | TFTP chainload timeout | Changed from TFTP to HTTP for Stage 2 chainload |
| `e82c0f4` | Feb 15 | Custom build complexity | Simplified to use pre-built iPXE binaries |

---

## 🚨 Known Issues

### Issue #1: x86/x64 PXE Boot Fails at Stage 2 (CURRENT - NETWORK CONNECTIVITY)
**Symptom:** Device boots undionly.kpxe successfully, iPXE shell available, but HTTP chainload fails  
**Error:** "Network unreachable (https://ipxe.org/2808b011)" when attempting `chain http://192.168.1.50:8000/api/v1/boot/ipxe/menu`  
**Root Cause:** Device on 10.10.50.x VLAN cannot reach API on 192.168.1.50:8000 (inter-VLAN routing may be blocked or API unreachable)  
**Status:** 🔄 **DEBUGGING IN PROGRESS** - Need to verify network connectivity from device to API  
**Test Date:** February 15, 2026

### Issue #2: DHCP Boot Loop (ATTEMPTED FIX - NEEDS VERIFICATION)
**Original Symptom:** Device kept downloading undionly.kpxe in infinite loop  
**Root Cause:** dnsmasq wasn't configured to serve boot.ipxe to iPXE clients on second DHCP  
**Attempted Fix:** Added `dhcp-boot=tag:ipxe,boot.ipxe` rules in dnsmasq.conf (commit 1193e3e)  
**Current Status:** ⏳ **Cannot verify yet** - depends on fixing Stage 2 network connectivity  
**Note:** The router (not dnsmasq) provides DHCP Option 67, so dnsmasq dhcp-boot rules may not apply as expected

### Issue #3: TFTP Chainload Timeout (SOLVED)
**Original Symptom:** `chain tftp://192.168.1.50/boot-menu.ipxe` times out  
**Root Cause:** Multi-VLAN UDP routing not working from 10.10.50.x to 192.168.1.50  
**Solution:** Changed to HTTP chainload instead (TCP routing works better)  
**Status:** ✅ Solved (commit 17ac220)

### Issue #4: API Returns 500 Error (FIXED)
**Symptom:** `http://192.168.1.50:8000/api/v1/boot/ipxe/menu` → 500 Internal Server Error  
**Root Cause:** `list_os_installer_files()` returns dict, code tried to iterate directly  
**Fix:** Extract `files` array from dict: `installers = result.get('files', [])`  
**Status:** ✅ Fixed (commit 55da7dd), API restarted

---

## 🧪 Testing Checklist

### HyperV Test Results (February 15, 2026 - PARTIAL FAILURE)

**Test Setup:**
- Device: HyperV VM (MAC: 00:15:5d:32:16:03)
- Network: Boot VLAN 10.10.50.159
- Target: Unraid 192.168.1.50 (API port 8000, TFTP port 69)
- Test Method: Boot VM via PXE, observe boot sequence

**Results:**
```
✅ Stage 1 (TFTP): undionly.kpxe downloaded (70810 bytes)
✅ Stage 1.5 (iPXE Boot): undionly.kpxe booted successfully
✅ iPXE Ready: Shell accessible via Ctrl+B, confirming iPXE loaded
❌ Stage 2 (HTTP): boot.ipxe chainload to API failed
   Error: "Network unreachable (https://ipxe.org/2808b011)"
```

**Test Log Output:**
```
iPXE 1.21.1+ (q1d23d) — Open Source Network Boot Firmware
netO: 00:15:5d:32:16:03 using undionly on 0000:00:0a.0 (Ethernet) [open]
[Link:up, TX:0, RX:1, RX:0, RXE:01]
TXE: 1 x "Network unreachable (https://ipxe.org/2808b011)"
Configuring (netO 00:15:5d:32:16:03)... ok
netO: 10.10.50.159/255.255.255.0 gw 10.10.50.1
Next server: 192.168.1.50
Filename: undionly.kpxe
tftp://192.168.1.50/undionly.kpxe... ok
undionly.kpxe : 70810 bytes [IPXE-NBP]
PXE->DB1: iPXE at 7BE4:0B40, entry point at 7BE4:0153
[iPXE shell ready - Press Ctrl+B]
```

**Analysis:**
- DHCP still providing filename = `undionly.kpxe` (expected, can't control router)
- TFTP Stage 1 working perfectly (70KB downloaded)
- iPXE initialized correctly within undionly.kpxe
- boot.ipxe likely loaded from TFTP but chainload to HTTP failed
- Error suggests network path from 10.10.50.x to 192.168.1.50:8000 is blocked or API unreachable

**Root Cause Hypothesis:**
The device is on 10.10.50 VLAN, API is on 192.168.1.50. The HTTP chainload attempt in boot.ipxe tried to reach:
```
chain http://192.168.1.50:8000/api/v1/boot/ipxe/menu
```
But got "Network unreachable" error, suggesting either:
1. Inter-VLAN routing to 192.168.1.50:8000 is blocked
2. API service not running or not responding on port 8000
3. Network timeout before connection established

**Feb 15 Update: Improvements Deployed**
- New boot.ipxe script now uses `${next-server}` from DHCP instead of hardcoding IP
- Added 10-second timeout to give network time to route packets across VLANs
- Auto-retry with DHCP renewal if first HTTP chainload attempt fails
- This should handle multi-VLAN timing/routing issues better
- **Status:** Ready for re-test on HyperV

---

### Future Test Checklist

#### Debugging Internet Connectivity (REQUIRED BEFORE NEXT TEST)
- [ ] SSH into HyperV VM (if possible)
- [ ] Run: `ping 192.168.1.50` from 10.10.50.159
- [ ] Check if TCP:8000 is reachable: `telnet 192.168.1.50 8000` or `nc -zv 192.168.1.50 8000`
- [ ] Review network routing table on Unraid
- [ ] Check firewall rules on both VLANs
- [ ] Verify API service responds: `curl http://192.168.1.50:8000/api/v1/boot/ipxe/menu` from Unraid

#### If API Unreachable (Connectivity Issue)
- [ ] Verify inter-VLAN routing is enabled
- [ ] Check Unifi router VLAN configuration
- [ ] Confirm 192.168.1.50 is gateway/router for 10.10.50
- [ ] Test with hardcoded IP instead of hostname
- [ ] May need to modify boot.ipxe to use DHCP variables or fallback

#### If API Reachable and Still Fails
- [ ] Check if chainload syntax is correct
- [ ] Verify API returns valid iPXE script format
- [ ] Check if there's a parse error in API response
- [ ] Test with explicit boot option instead of chainload

---

### HyperV Success Criteria
- **Boot menu appears** → full chain working ✅ GOAL
- **iPXE shell with "No OS installers available"** → API reached but empty ✅ ACCEPTABLE
- **Network unreachable error** → connectivity issue ❌ CURRENT STATE
- **iPXE shell offered (Ctrl+B)** → Stage 1/1.5 complete, Stage 2 failed ✅ PARTIAL

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
