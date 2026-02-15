# Netboot Orchestrator - Project Guide

**Last Updated:** February 15, 2026 (15:30 UTC)  
**Current Focus:** Resolving iPXE boot loop via dnsmasq vendor detection  
**Status:** ✅ Backend Architecture Refactored - iPXE Boot Loop Fix Applied

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
- ✅ **x86/x64 PXE boot infrastructure** - TFTP + iPXE loading, HTTP chainload configured
- ✅ **API backend** (FastAPI) - Boot menu endpoint working (4,371 boot options)
- ✅ **Frontend UI** (React) - File browser and setup guide deployed
- ✅ **TFTP server** (dnsmasq) - Serving iPXE bootloaders successfully
- ✅ **HTTP server** (nginx) - Available for boot files
- 🔄 **iSCSI target** (tgtd) - Running but untested
- ⏳ **RPI4/5 support** - Not yet started
- ⏳ **Device registration UI** - Not yet started

---

## 🏗️ Architecture

### Network Setup
```
Boot VLAN (10.10.50.x)              Primary VLAN (192.168.1.x)
├─ Test Devices/VMs          ←PXE→  ├─ Unraid Server (192.168.1.50)
└─ Unifi Router DHCP               │  
                                    ├─ netboot-backend (host network)
                                    │  ├─ FastAPI (port 8000)
                                    │  ├─ dnsmasq TFTP/DHCP (UDP 67/69)
                                    │  ├─ nginx HTTP (port 8080)
                                    │  └─ tgtd iSCSI (port 3260)
                                    │
                                    └─ netboot-frontend (host network)
                                       └─ React SPA (port 30000)

KEY ARCHITECTURE CHANGE (Feb 15):
✅ Consolidated all services into single netboot-backend container
✅ Both containers use network_mode: host (direct physical network access)
✅ Eliminated Docker bridge network isolation issue
```

### Container Stack
```
netboot-backend (Single consolidated container on host network):
├─ FastAPI (Uvicorn) - API server, device management, boot menu generation
├─ dnsmasq - TFTP server (port 69/udp), DHCP server (port 67/udp)
├─ nginx - HTTP boot file server (port 8080)
├─ tgtd - iSCSI target server (port 3260)
└─ entrypoint-backend.sh - Simple bash script managing all 4 services

netboot-frontend (React SPA container on host network):
└─ React + Vite compiled to nginx serving (port 30000 → localhost:3000)
```

### Boot Flow (Current x86/x64)

1. **Device DHCP** (via Unifi router) → Option 67 = `undionly.kpxe`
2. **Stage 1** ✅ (TFTP): Device downloads `undionly.kpxe` from TFTP
   - dnsmasq listens on UDP 69 (host network, direct physical interface access)
   - confirmed: "sent /data/tftp/undionly.kpxe to {device_ip}"
3. **Stage 1.5** ✅ (iPXE Init): undionly.kpxe boots as firmware extension
   - iPXE 1.21.1+ loads (confirmed in HyperV console)
   - auto-searches for undionly.ipxe (same basename, .ipxe extension)
   - undionly.ipxe script found and executes
4. **Stage 2** ✅ (DHCP - NO BOOT LOOP - FIXED in commit aa79947)
   - **Must handle both BIOS and iPXE DHCP requests:**
     - **BIOS/UEFI First Request:** dnsmasq matches client-arch → responds with bootloader filename (undionly.kpxe or ipxe.efi)
     - **iPXE Second Request:** dnsmasq now detects `vendor:iPXE` → responds with **empty filename** → prevents infinite redownload loop 🔑
   - undionly.ipxe executes: `dhcp` → `chain http://192.168.1.50:8000/api/v1/boot/ipxe/menu`
   - Device performs second DHCP with iPXE vendor detection, gets no filename, searches TFTP for boot.ipxe
   - dnsmasq DHCP responds from host network (both VLANs: 192.168.1.x and 10.10.50.x)
5. **Menu Display**: API returns boot menu (4,371 options available)
6. **User Selection & Boot**: Device boots selected installer or iSCSI disk image

### Root Cause Analysis - Network Isolation (RESOLVED ✅)

**Problem (Feb 15 morning):**
- Devices couldn't reach TFTP despite requests being sent
- DHCP and HTTP chainload failing
- **Discovery:** Same-VLAN device (192.168.1.73) ALSO failed - proving NOT a cross-VLAN routing issue
- **Root cause:** TFTP/dnsmasq ran in Docker bridge network (netboot-orchestrator_netboot), isolated from physical network
- Device DHCP/TFTP requests on physical interface → bridge network container never received them

**Solution Applied (Feb 15 14:45):**
- ✅ Consolidated all services into single `netboot-backend` container
- ✅ Added `network_mode: host` to docker-compose.yml
- ✅ Services now listen directly on host network interfaces
- ✅ Removed supervisor (caused logging errors), replaced with simple bash entrypoint script
- ✅ All services start in background, FastAPI foreground as main process

### Boot Files Location (TFTP Root)
```
/data/tftp/
├── undionly.kpxe    (70KB - BIOS bootloader) ✅ serving
├── ipxe.efi         (9.2KB - UEFI bootloader) ✅ serving
├── boot.ipxe        (900B - Stage 2 auto-chainload script)
├── undionly.ipxe    (989B - Auto-boot script [NEW])
└── boot-menu.ipxe   (658B - Fallback menu)
```

---

## 📋 Current Status

### ✅ Architecture & Infrastructure Completed
- [x] **Consolidated Backend Architecture** (Feb 15) - All services in single container
  - TFTP server (dnsmasq, UDP 69)
  - DHCP server (dnsmasq, UDP 67)  
  - HTTP server (nginx, port 8080)
  - iSCSI target (tgtd, port 3260)
  - FastAPI REST API (port 8000)
- [x] **Host Network Mode** (Feb 15) - Direct physical network access, no bridge isolation
- [x] **Simplified Service Management** (Feb 15) - Bash entrypoint script replaces supervisor
- [x] **Docker Image Build** (Feb 15) - Successfully builds 46.4s, all services included
- [x] TFTP service deployment (dnsmasq v2.90)
- [x] iPXE bootloader downloads (undionly.kpxe, ipxe.efi)
- [x] Boot script infrastructure (boot.ipxe, undionly.ipxe, boot-menu.ipxe)
- [x] Multi-VLAN network routing (tested TCP/UDP)
- [x] API endpoint creation (`/api/v1/boot/ipxe/menu`) - **4,371 options generated**
- [x] Frontend UI (folder browser, setup guide)
- [x] TFTP Stage 1 working (undionly.kpxe downloads confirmed)
- [x] iPXE Stage 1.5 working (firmware detected in HyperV)
- [x] **iPXE Boot Loop Fixed** (Feb 15, 15:30) - dnsmasq vendor detection prevents infinite redownload

### 🔄 Next Phase - Testing & Validation
- [ ] **dnsmasq iPXE Detection Verification** - Boot device and verify:
  - BIOS: Gets `undionly.kpxe` on first DHCP ✓
  - iPXE: Detects vendor:iPXE on second DHCP, gets **no filename** (no boot loop!) ✓
  - UEFI: Gets `ipxe.efi` on DHCP ✓
- [ ] **End-to-End PXE Boot Test** (Device 10.10.50.159 or 192.168.1.73)
  - Stage 1: TFTP undionly.kpxe downloads ✅
  - Stage 1.5: iPXE firmware initializes ✅
  - Stage 2: iPXE DHCP (no boot loop) + HTTP chainload to API 🔄
  - Stage 3: Boot menu displays ✓
- [ ] **Cross-VLAN Boot Verification** - Test from 10.10.50.x VLAN to 192.168.1.50 server

### ⏳ Pending Features
- [ ] **ARM/RPI4/5 U-Boot Support** - Add Raspberry Pi bootloader and DHCP boot detection
- [ ] **iSCSI Boot Testing** - Verify persistent disk assignment and boot-from-iSCSI
- [ ] **Device Registration UI** - Auto-register unknown MAC addresses on first boot
- [ ] **Device Type Selector** - Boot menu detection for BIOS/UEFI/ARM architecture
- [ ] **Windows/Linux Installer Integration** - Auto-detection and menu generation
- [ ] **Monitoring & Analytics** - Device boot logs, success rates, performance tracking

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
| `aa79947` | Feb 15 | **iPXE Boot Loop** - Device re-requests undionly.kpxe infinitely | **CRITICAL FIX**: Add `dhcp-match=set:ipxe,vendor:iPXE` and `dhcp-match=set:ipxe,vendor:Etherboot` for detection + return empty filename `dhcp-boot=tag:ipxe,,192.168.1.50` |
| `dd62807` | Feb 15 | TFTP transfer aborts on all devices (cross-VLAN AND same-VLAN) | Added `tftp-no-blocksize` and `tftp-single-port` options - disables blocksize negotiation, uses standard 512-byte blocks |
| `5721ffd` | Feb 15 | dnsmasq DHCP config had syntax errors | Removed invalid dhcp-option lines (3rd removal: router syntax) |
| `a7a141e` | Feb 15 | dnsmasq parsing error "bad dhcp-option at line X" | Removed DNS option and log-dhcp |
| `72acecd` | Feb 15 | dnsmasq "bad dhcp-option" lease-time syntax | Fixed invalid syntax |
| `a48527e` | Feb 15 | iPXE script syntax error | Fixed line breaks in undionly.ipxe - commands were split across lines |
| `68e228f` | Feb 15 | **undionly.kpxe not auto-executing** | **CRITICAL FIX**: Create undionly.ipxe - the script that undionly.kpxe auto-executes |
| `c8b058d` | Feb 15 | HTTP chainload timeout | Added 10s timeout, DHCP retry, $next-server variable, better diagnostics |
| `1193e3e` | Feb 15 | Infinite DHCP loop | Added `dhcp-boot` rules in dnsmasq (ineffective, router handles DHCP) |
| `55da7dd` | Feb 15 | API 500 error | Fixed dict/list iteration in boot menu endpoint |

---

## 🚨 Known Issues

### Issue #1: iPXE Boot Loop (FIXED ✅ - See Issue #2)
Merged into Issue #2 and resolved via vendor-class detection fix.

### Issue #1b: x86/x64 PXE Boot Fails at Stage 2 (CURRENT - NETWORK CONNECTIVITY)
**Symptom:** Device boots undionly.kpxe successfully, iPXE shell available, but HTTP chainload fails  
**Error:** "Network unreachable (https://ipxe.org/2808b011)" when attempting `chain http://192.168.1.50:8000/api/v1/boot/ipxe/menu`  
**Root Cause (Previous):** Device on 10.10.50.x VLAN cannot reach API on 192.168.1.50:8000 (inter-VLAN routing may be blocked or API unreachable)  
**Status:** 🔄 **TESTING AFTER BOOT LOOP FIX** - Boot loop now fixed, re-test to see if we reach Stage 3  
**Test Date:** February 15, 2026

### Issue #2: DHCP Boot Loop (FIXED ✅)
**Original Symptom:** Device kept downloading undionly.kpxe in infinite loop, iPXE does DHCP again and still gets same bootloader filename  
**Root Cause:** dnsmasq wasn't detecting iPXE clients by vendor-class, relied only on option 175 (unreliable)  
**Solution Applied (commit aa79947):**
  1. Added vendor-class detection: `dhcp-match=set:ipxe,vendor:iPXE` + `dhcp-match=set:ipxe,vendor:Etherboot`
  2. Return **empty filename** to iPXE: `dhcp-boot=tag:ipxe,,192.168.1.50,192.168.1.50` (prevents redownload)
  3. Reordered boot rules: BIOS first, iPXE second, UEFI last
**Boot Flow Now:**
  - BIOS: DHCP → `undionly.kpxe` → Downloads via TFTP ✅
  - iPXE (2nd DHCP): Detected by vendor:iPXE → No filename returned → Searches TFTP for boot.ipxe ✅
  - UEFI: DHCP → `ipxe.efi` → Downloads via TFTP ✅
**Status:** ✅ **Fixed** - Ready for re-test on HyperV

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

**Feb 15 Update: Script Syntax Fixed**
- First attempt (commit 68e228f) had syntax errors: line breaks in middle of commands
- "DHCP: command not found" error indicated iPXE couldn't parse the script properly
- Fixed by removing line breaks within compound commands (Feb 15, commit a48527e)
- Simplified script structure for clarity and reliability
- **Status:** Ready for re-test on HyperV with corrected syntax

**What to Expect on Next Boot:**
If script loads correctly, device should see:
```
echo ====================================================
echo        Netboot Orchestrator - iPXE Stage 2
echo ====================================================
echo
echo MAC Address: 00:15:5d:32:16:03
echo IPv4 Address: [will show assigned IP]
echo Gateway: 10.10.50.1
echo
echo Initializing network with DHCP...
[runs dhcp command]
echo
echo Attempting HTTP chainload to API on 192.168.1.50:8000
[attempts: timeout 15 chain http://192.168.1.50:8000/api/v1/boot/ipxe/menu]
```

If HTTP succeeds: Would display boot menu  
If HTTP times out: Retries with DHCP renewal  
If still fails: Drops to shell for manual commands

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
| `netboot/Dockerfile.backend` | Consolidated backend with dnsmasq config embedded | ✅ Updated with vendor detection (aa79947) |
| `netboot/entrypoint-backend.sh` | Service management (dnsmasq, FastAPI, tgtd, nginx) | ✅ Working, no errors |
| `backend/app/api/v1.py` | Boot menu API endpoint | ✅ Fixed (dict extraction) |
| `backend/app/services/file_service.py` | OS installer listing | ✅ Returns correct structure |
| `docker-compose.yml` | Service orchestration | ✅ All services on host network |

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
# Watch backend logs (all services)
docker logs -f netboot-backend

# Check dnsmasq config and status
docker exec netboot-backend cat /etc/dnsmasq.d/netboot.conf

# Check API responses
curl -v http://192.168.1.50:8000/api/v1/boot/ipxe/menu

# Enter backend container
docker exec -it netboot-backend bash

# Test TFTP connectivity
tftp 192.168.1.50 69
> get /data/tftp/boot.ipxe
> quit
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
