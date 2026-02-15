# Netboot Orchestrator - Project Guide

**Last Updated:** February 15, 2026 (17:41 UTC)  
**Current Focus:** iPXE Bootloaders Missing - Need wget Downloads  
**Status:** 🔧 IN PROGRESS - Boot scripts created but Stage 1 bootloader (undionly.kpxe) NOT FOUND

---

## ⚡ Quick Handoff Summary (For Next AI)

**Situation:**
- Boot scripts (undionly.ipxe, boot-menu.ipxe) successfully created by entrypoint ✅
- BUT device still cannot find undionly.kpxe (BIOS Stage 1 bootloader) ❌
- Error: "PXE-T01: file /data/tftp/undionly.kpxe not found"

**Root Cause:** 
Same volume mount shadowing issue - Dockerfile downloads iPXE binaries but docker-compose volume mount hides them

**One-Line Fix:**
Add wget commands to entrypoint-backend.sh to download undionly.kpxe and ipxe.efi into /data/tftp/

**Exact Code Location:**
- File: `netboot/entrypoint-backend.sh`
- Insert around line 30 (before "Starting services" message)
- See "THE FIX NEEDED" section below with exact wget commands

**Test After Fix:**
```bash
docker-compose down && docker-compose build --no-cache netboot-backend && docker-compose up -d
docker logs netboot-backend | grep -E "TFTP|undionly|ERROR"
# Should show undionly.kpxe and ipxe.efi downloaded successfully
```

**Expected Outcome:** Device boots all 3 stages and displays menu

---

**DISCOVERY:** Boot scripts created successfully ✅ BUT iPXE bootloaders still missing ❌

**Current Status:**
```
✅ undionly.ipxe    (866 bytes) - CREATED BY ENTRYPOINT ✓
✅ boot.ipxe        (65 bytes)  - CREATED BY ENTRYPOINT ✓
✅ boot-menu.ipxe   (276 bytes) - CREATED BY ENTRYPOINT ✓
❌ undionly.kpxe    (70KB)      - NOT FOUND - Device cannot boot Stage 1!
❌ ipxe.efi         (9.2KB)     - NOT FOUND - UEFI variant missing
```

**Device Error (17:41 UTC):**
```
PXE-T01: file /data/tftp/undionly.kpxe not found for 10.10.50.159
PXE-E3B: TFTP Error - File Not Found
```

**Why Still Failing:**
- Device requests `undionly.kpxe` (BIOS Stage 1 bootloader)
- Dockerfile RUN downloads these but volume mount shadows them
- Entrypoint script creates `.ipxe` chainload scripts ✅  
- But entrypoint does NOT download the actual iPXE binaries ❌

**THE FIX NEEDED (Next Session):**

Add to `netboot/entrypoint-backend.sh` right after creating boot scripts:

```bash
# Download iPXE binaries if missing
if [ ! -f /data/tftp/undionly.kpxe ]; then
    echo "[TFTP] Downloading undionly.kpxe..."
    wget -q https://boot.ipxe.org/undionly.kpxe -O /data/tftp/undionly.kpxe || echo "ERROR: Failed to download undionly.kpxe"
fi

if [ ! -f /data/tftp/ipxe.efi ]; then
    echo "[TFTP] Downloading ipxe.efi..."
    wget -q https://boot.ipxe.org/ipxe.efi -O /data/tftp/ipxe.efi || echo "ERROR: Failed to download ipxe.efi"
fi

# Verify files exist
if [ ! -f /data/tftp/undionly.kpxe ] || [ ! -f /data/tftp/ipxe.efi ]; then
    echo "ERROR: iPXE bootloaders not available!"
    exit 1
fi
```

**Why This Works:**
- At runtime, download the actual iPXE binaries
- Files persist on `/data/tftp/` volume
- dnsmasq can serve them to devices
- BIOS devices will boot undionly.kpxe
- UEFI devices can boot ipxe.efi

**File Locations:** 
- Location: `netboot/entrypoint-backend.sh` (around line 30, before "Starting services")
- Add error checking and logging like the boot script creation above
- Should exit with error if files cannot be downloaded

---

## 📋 Recent Commit History (Last 5)

| Commit | Message | Status |
|--------|---------|--------|
| 89fdea5 | Use printf instead of heredoc for TFTP boot script creation | ✅ Latest |
| bf32c76 | Fix: Create TFTP boot scripts in entrypoint to persist on mounted volume | ✅ |
| c147a9c | Fix rule ordering: iPXE boot rule must come BEFORE BIOS rule | ✅ Deployed |
| 7e1d347 | Fix BIOS rule precedence: exclude iPXE devices with tag negation | ❌ Reverted |
| abca412 | Fix iPXE DHCP boot: serve undionly.ipxe script instead of empty filename | ✅ Deployed |

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
✅ Added entrypoint script to create boot files at runtime (new)
```

### Container Stack
```
netboot-backend (Single consolidated container on host network):
├─ entrypoint-backend.sh
│  ├─ Create /data/tftp boot scripts (printf) ← NEW FIX
│  ├─ Start dnsmasq TFTP/DHCP
│  ├─ Start nginx HTTP server
│  ├─ Start tgtd iSCSI target
│  ├─ Start FastAPI on port 8000
│  └─ Generate boot menu every 5 minutes from API
├─ FastAPI (Uvicorn) - API, device mgmt, boot menu endpoint
├─ dnsmasq - TFTP (UDP 69), DHCP (UDP 67)
├─ nginx - HTTP (port 8080)
└─ tgtd - iSCSI (port 3260)

netboot-frontend (React SPA on host network):
└─ React + Vite served on port 30000
```

### TFTP Boot Files

**Current Status (Feb 15, 17:41):**
```
/data/tftp/
├── undionly.kpxe    (70KB - BIOS Stage 1)       ❌ MISSING - DEVICE CANNOT BOOT
├── ipxe.efi         (9.2KB - UEFI Stage 1)      ❌ MISSING
├── undionly.ipxe    (1.2KB - Stage 1.5 script)  ✅ CREATED BY ENTRYPOINT
│   └─ Chains to: tftp://192.168.1.50/boot-menu.ipxe
├── boot-menu.ipxe   (276 bytes - Boot menu)     ✅ CREATED BY ENTRYPOINT  
└── boot.ipxe        (65 bytes - Backup chain)   ✅ CREATED BY ENTRYPOINT
```

**What's Working:**
- ✅ Entrypoint script successfully creates .ipxe boot scripts
- ✅ Files are created with correct permissions
- ✅ dnsmasq configuration correct (rules, TFTP root)
- ✅ FastAPI generating boot menu

**What's Not Working:**
- ❌ ipxe binaries (undionly.kpxe, ipxe.efi) absent
- ❌ Device can request DHCP → get boot filename
- ❌ Device tries to TFTP undionly.kpxe → FILE NOT FOUND
- ❌ Cannot progress to Stage 1.5 (iPXE firmware)

### Boot Flow (Current Status - Feb 15, 17:41)

**Stage 1: BIOS PXE Load** ❌ BLOCKED
```
Device DHCP → Unifi responds: Option 67 = undionly.kpxe
Device TFTP → 192.168.1.50:69 → Requests undionly.kpxe
Expected: 70KB binary file
Actual: PXE-T01: file /data/tftp/undionly.kpxe not found
Status: ❌ FILE NOT FOUND - Cannot download Stage 1 bootloader
```

**Stage 1.5: iPXE Firmware Init** ⏸️ BLOCKED (waiting for Stage 1)
```
Would receive undionly.kpxe → Loads iPXE 1.21.1+ firmware
Searches for undionly.ipxe via TFTP
Previously captured: Device reaches iPXE shell ✅ (in earlier session)
Current: Cannot reach because Stage 1 binary missing
```

**Stage 2: Boot Menu** ✅ READY TO TEST (once Stage 1 fixed)
```
undionly.ipxe script (created by entrypoint) chains to boot-menu.ipxe
Boot menu displays 279 iPXE options from API
User selects option, device boots installer
Ready to deploy once iPXE binaries available
```

---

## 🔍 Technical Details - The File Missing Issue

### Problem Sequence
1. ✅ Dockerfile RUN layer creates `/data/tftp/undionly.ipxe`
2. ✅ Image builds successfully with files in layer
3. ❌ docker-compose.yml has `volumes: - ./data:/data`
4. ❌ Volume mount overlay REPLACES container's `/data` directory
5. ❌ Files from RUN layer are shadowed (inaccessible)
6. ❌ Device requests undionly.ipxe → dnsmasq looks in `/data/tftp/` → FILE NOT FOUND

### Solution: Runtime File Creation
1. ✅ Moved file creation from Dockerfile RUN to entrypoint script
2. ✅ Entrypoint executes **after** volume mounts are active
3. ✅ Files created in mounted `/data/tftp/` volume
4. ✅ Persist between container restarts
5. ✅ Device requests undionly.ipxe → dnsmasq finds file → SUCCESS

### Why Printf Over Heredoc
- Heredoc syntax can have issues in shell scripts
- `printf` is more portable and reliable
- Single-line format easier to debug in Docker build output

---

## 📊 Service Status (Feb 15, 17:00)

| Service | Status | Purpose |
|---------|--------|---------|
| dnsmasq v2.90 | ✅ Running | TFTP/DHCP server |
| FastAPI | ✅ Running | Boot menu API |
| nginx | ✅ Running | HTTP boot files |
| tgtd | ✅ Running | iSCSI target |
| entrypoint | ✅ Fixed | Creates boot scripts at startup |
| **TFTP Files** | 🔧 Fixing | Boot scripts now created by entrypoint |

---

## 🎯 Boot Process Summary

```
Device Powers On
    ↓
DHCP Request (10.10.50.x VLAN)
    ↓
Unifi Router: "Boot file = undionly.kpxe on 192.168.1.50"
    ↓
TFTP to 192.168.1.50:69 → undionly.kpxe ✅ WORKS
    ↓
Device Downloads 70KB binary
    ↓
PXE/BIOS executes undionly.kpxe → iPXE firmware loads
    ↓
iPXE boots → Searches for undionly.ipxe (same filename, .ipxe extension)
    ↓
iPXE DHCP Request (with vendor class = *iPXE*)
    ↓
dnsmasq matches iPXE tag → Responds: "Load undionly.ipxe"
    ↓
iPXE TFTP → 192.168.1.50:69 → undionly.ipxe ✅ NOW FIXED
    ↓
undionly.ipxe script executes:
    - dhcp (get IP again)
    - chain tftp://192.168.1.50/boot-menu.ipxe
    ↓
TFTP → boot-menu.ipxe loaded
    ↓
Boot Menu Displayed (279 options from API) ⏳ Testing
    ↓
User Selects Boot Option
    ↓
Device Boots Installer or iSCSI Image
```

---

## ✅ Completed Tasks

- [x] PXE TFTP infrastructure setup
- [x] iPXE bootloader downloads  
- [x] dnsmasq TFTP/DHCP configuration
- [x] FastAPI boot menu API (279 options)
- [x] Docker containerization
- [x] Host network mode (fixed isolation)
- [x] Consolidated backend services
- [x] TFTP Stage 1 tested (undionly.kpxe serves)
- [x] iPXE Stage 1.5 tested (firmware initializes)
- [x] DHCP boot rule ordering fixed (iPXE before BIOS)
- [x] Boot script runtime creation (entrypoint)

---

## 🔄 Next Steps (CRITICAL - Feb 15, 17:41)

### ⚠️ BLOCKER: iPXE Bootloaders Missing

**Device Error Log (17:41 UTC):**
```
PXE-T01: file /data/tftp/undionly.kpxe not found for 10.10.50.159
PXE-E3B: TFTP Error - File Not Found
```

**What Needs to Happen Next Session:**

1. **ADD iPXE Binary Downloads to entrypoint-backend.sh**
   - Location: `netboot/entrypoint-backend.sh` (lines 30-50, before service startup)
   - Add wget commands to download:
     - `https://boot.ipxe.org/undionly.kpxe` → `/data/tftp/undionly.kpxe`
     - `https://boot.ipxe.org/ipxe.efi` → `/data/tftp/ipxe.efi`
   - Add error checking (exit if download fails)
   - Add verification (check file exists and has content)
   - See "THE FIX NEEDED" section above with exact code

2. **Test Locally**
   ```bash
   docker-compose down
   docker-compose build --no-cache netboot-backend
   docker-compose up -d
   docker logs netboot-backend | grep -E "TFTP|undionly|ERROR"
   ```
   Expected output:
   ```
   [TFTP] Downloading undionly.kpxe...
   [TFTP] Downloading ipxe.efi...
   [TFTP] Boot scripts created:
   -rw-r--r-- /data/tftp/undionly.kpxe
   -rw-r--r-- /data/tftp/ipxe.efi
   -rw-r--r-- /data/tftp/undionly.ipxe
   ```

3. **Deploy to Unraid**
   ```bash
   cd /mnt/user/appdata/netboot-orchestrator
   git pull origin main
   docker-compose down
   docker-compose build --no-cache netboot-backend
   docker-compose up -d
   ```

4. **Verify Files Exist on Unraid**
   ```bash
   ls -lah /mnt/user/appdata/netboot-orchestrator/data/tftp/
   # Should show:
   # -rw-r--r-- undionly.kpxe  (70KB)
   # -rw-r--r-- ipxe.efi       (9.2KB)
   # -rw-r--r-- undionly.ipxe  (1.2KB)
   # -rw-r--r-- boot-menu.ipxe (276B)
   ```

5. **Boot Device Test**
   - Device should download undionly.kpxe ✅
   - Device should boot to iPXE firmware ✅
   - Device should load boot menu ✅
   - User can select boot option ✅

**Why This Fix Works:**
- Dockerfile creates files but volume mount shadows them ❌
- Entrypoint creates .ipxe scripts but doesn't download binaries ❌
- **Solution:** Add wget downloads to entrypoint ✅
- Files created at runtime on mounted volume ✅
- Persist between restarts ✅
- Device can access them ✅

---

## ✅ Completed Tasks

- [x] PXE TFTP infrastructure setup
- [x] dnsmasq TFTP/DHCP configuration
- [x] FastAPI boot menu API (279 options)
- [x] Docker containerization (consolidated backend)
- [x] Host network mode (fixed isolation)
- [x] DHCP boot rule ordering (iPXE before BIOS)
- [x] Boot scripts created by entrypoint (undionly.ipxe, boot-menu.ipxe)
- [ ] **iPXE bootloaders downloaded by entrypoint (undionly.kpxe, ipxe.efi)** ← NEXT

---

## 🎯 Handoff for Next Session (Feb 16)

**Current Exact Problem:**
Device cannot find `undionly.kpxe` - Stage 1 bootloader missing from `/data/tftp/`

**Root Cause:**
Docker volume mount shadows Dockerfile files → entrypoint needed for runtime creation

**Partial Solution Deployed (Commits bf32c76, 89fdea5):**
- ✅ Boot scripts (.ipxe files) created by entrypoint
- ❌ iPXE binaries still not downloaded

**What Was Discovered (Feb 15, 17:41 UTC):**
```
Container logs show:
✅ [TFTP] undionly.ipxe created (866 bytes)
✅ [TFTP] boot.ipxe created (65 bytes)  
✅ [TFTP] boot-menu.ipxe created (276 bytes)
❌ Device error: PXE-T01: file /data/tftp/undionly.kpxe not found
```

**Code Change Needed:**
- File: `netboot/entrypoint-backend.sh`
- Add 12-15 lines of wget + error checking around line 30
- Download undionly.kpxe and ipxe.efi from boot.ipxe.org
- Verify files exist before starting services
- See code example in "THE FIX NEEDED" section above

**Expected Timeline After Fix:**
1. Add wget commands to entrypoint (~10 minutes coding)
2. Test locally (~2 minutes)
3. Push to GitHub
4. Deploy to Unraid (`git pull && docker-compose up -d`)
5. Boot device and verify all stages work
6. **Success:** Device boots to menu → selects OS → installs

---

## 📝 Code References

### Entrypoint Script (entrypoint-backend.sh)
- **Location:** `netboot/entrypoint-backend.sh` (lines 1-43)
- **Key Change:** Now creates boot scripts using printf before starting services
- **Files Created:**
  - /data/tftp/undionly.ipxe (chains to TFTP boot menu)
  - /data/tftp/boot.ipxe (HTTP chainload backup)
  - /data/tftp/boot-menu.ipxe (menu placeholder)

### dnsmasq Configuration (Dockerfile.backend)
- **Location:** `netboot/Dockerfile.backend` (lines 50+)
- **DHCP Boot Rules:**
  ```
  dhcp-boot=tag:ipxe,undionly.ipxe,192.168.1.50,192.168.1.50    ← FIRST (iPXE)
  dhcp-boot=tag:bios,undionly.kpxe,192.168.1.50,192.168.1.50    ← SECOND (BIOS)
  ```
  - PXE/BIOS sends "bios" tag → gets undionly.kpxe
  - iPXE firmware sends "bios" AND "ipxe" tags → dnsmasq checks first rule → gets undionly.ipxe

### Docker Volumes (docker-compose.yml)
- **Issue:** `./data:/data` shadows container files
- **Solution:** entrypoint script creates files after mount is active
- **Files Persist:** Mounted volume guarantees persistence

---

## 🐛 Known Issues & Workarounds

| Issue | Cause | Workaround | Status |
|-------|-------|-----------|--------|
| "Can't find file" error | Boot scripts not in /data/tftp | Rebuild with cache bust | ✅ Fixed |
| Infinite undionly.kpxe loop | BIOS rule matched twice | Rule ordering (iPXE first) | ✅ Fixed |
| Network isolation | Docker bridge mode | Use host network mode | ✅ Fixed |
| DHCP vendor not matching | Syntax issue | Corrected dhcp-match rules | ✅ Fixed |

---

## 🚀 End-to-End Test Plan (When Ready)

**Prerequisites:**
- Boot VLAN device (10.10.50.x) or 192.168.1.x device configured
- Unraid server running latest code (commit 89fdea5+)

**Test Sequence:**
1. Power on device
2. Watch PXE boot process:
   - [ ] Device gets DHCP IP (10.10.50.x or 192.168.1.x)
   - [ ] "Searching for TFTP server..."
   - [ ] "Contacting TFTP server..."
   - [ ] "Downloading undionly.kpxe..."
   - [ ] "75810 bytes [.....OK]"
   - [ ] iPXE 1.21.1+ banner appears
   - [ ] "Searching for undionly.ipxe..."
   - [ ] undionly.ipxe script loads
   - [ ] "chain tftp://192.168.1.50/boot-menu.ipxe"
   - [ ] Boot menu appears with options
3. Select option (e.g., "Windows Server 2022")
4. Device boots installer or iSCSI image

**Success Criteria:**
- ✅ All stages complete without errors
- ✅ Boot menu displays properly formatted options
- ✅ User selection and boot works
- ✅ Device boots to OS installer/disk

---

**Document maintained for AI handoff. All recent fixes documented in commit history on GitHub (Kronborgs/netboot-orchestrator).**

  - Stage 1.5: iPXE firmware initializes ✅
  - **Stage 2 (NEW FIX - commit abca412):** iPXE DHCP detection → load undionly.ipxe script 🔄
    - **Issue Fixed:** DHCP was serving empty boot filename to iPXE devices → device redownloaded undionly.kpxe in a loop
    - **Solution:** dnsmasq now serves `undionly.ipxe` to iPXE devices (detected via vendor class ID option 60)
    - **Result:** iPXE loads plaintext script that chains to TFTP boot menu
  - Stage 3: TFTP menu displays ✓
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
│   └── requirements.txt
│
├── frontend/                # React + TypeScript + Vite
│   ├── src/
│   │   ├── App.tsx
│   │   └── components/
│   ├── package.json
│   └── vite.config.ts
│
├── netboot/
│   ├── Dockerfile.backend      # 🔑 Consolidated backend: TFTP + DHCP + HTTP + iSCSI + API
│   ├── entrypoint-backend.sh   # Service manager for all backend services
│   ├── tftp/
│   │   └── scripts/
│   │       └── embed.ipxe      # Legacy custom build (deprecated)
│   └── http/
│       └── conf/
│           └── nginx.conf      # (nginx now managed by entrypoint script)
│
├── docker-compose.yml      # Orchestrates 2 containers:
│                          #   - netboot-backend (all services, host network)
│                          #   - netboot-frontend (React SPA, host network)
│
├── data/                   # Persistent volume (created at runtime)
│   ├── tftp/              # TFTP root
│   │   ├── undionly.kpxe  # BIOS bootloader (auto-downloaded)
│   │   ├── ipxe.efi       # UEFI bootloader (auto-downloaded)
│   │   ├── boot.ipxe      # Stage 2 chainload script
│   │   ├── undionly.ipxe  # Auto-boot script (runs after undionly.kpxe)
│   │   └── boot-menu.ipxe # Fallback menu
│   ├── http/              # HTTP boot files
│   └── iscsi/images/      # iSCSI disk images
│
└── PROJECT_GUIDE.md        # ← You are here
```

### Architecture Simplification (Feb 15, 2026)

**Before (Multi-container):**
- netboot-tftp container (dnsmasq TFTP/DHCP)
- netboot-http container (nginx HTTP server)
- netboot-iscsi container (tgtd iSCSI target)
- netboot-api container (FastAPI)
- netboot-frontend container (React)
- ❌ All isolated in Docker bridge network
- ❌ Supervisor complexity for process management

**After (Consolidated - Current):**
- **netboot-backend** container (single, host network):
  - dnsmasq (TFTP + DHCP on UDP 67/69)
  - nginx (HTTP on port 8080)
  - tgtd (iSCSI on port 3260)
  - FastAPI (API on port 8000)
  - ✅ Managed by simple bash entrypoint script
- **netboot-frontend** container (React SPA on port 30000)
- ✅ Both on host network = direct physical network access
- ✅ No bridge isolation issues

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
# Should show exactly 2 containers:
#   - netboot-backend (consolidated services)
#   - netboot-frontend (React SPA)
```

### Check Logs
```bash
# All backend services (dnsmasq, tgtd, FastAPI)
docker logs netboot-backend --tail 50

# Frontend React app
docker logs netboot-frontend --tail 20

# Test API endpoint
curl http://192.168.1.50:8000/api/v1/boot/ipxe/menu

# Test Frontend
curl http://192.168.1.50:30000
```

---

## 🔧 Recent Fixes (Key Commits)

| Commit | Date | Issue | Fix |
|--------|------|-------|-----|
| `abca412` | Feb 15, 16:40 | **iPXE DHCP Returns Empty Filename** - Device doesn't load undionly.ipxe, reboots | Changed `dhcp-boot=tag:ipxe,,192.168.1.50` → `dhcp-boot=tag:ipxe,undionly.ipxe,192.168.1.50` - Now iPXE devices are explicitly told to load the plaintext boot script |
| `c1759df` | Feb 15 | dnsmasq parse error with `option:` prefix in numeric options | Removed `option:` prefix: `option:93` → `93` (numeric syntax required by dnsmasq 2.90) |
| `3b29df0` | Feb 15 | dnsmasq parse error on DHCP Client Architecture detection | Changed `option:client-arch,N` to `93,N` (numeric DHCP option code, removed non-standard `option:175`) |
| `d734a0a` | Feb 15 | Old dnsmasq config file conflicting with inline config | Removed `COPY netboot/tftp/config` and `COPY netboot/tftp/scripts` - now only inline printf config used |
| `46a81a9` | Feb 15 | dnsmasq syntax error: 'inappropriate vendor:' | Changed `vendor:iPXE` to `option:60,iPXE*` (DHCP Vendor Class ID with wildcard) - correct dnsmasq syntax |
| `aa79947` | Feb 15 | **iPXE Boot Loop** - Device re-requests undionly.kpxe infinitely | Added `dhcp-match=set:ipxe,option:60,iPXE*` detection + return empty filename `dhcp-boot=tag:ipxe,,192.168.1.50` |
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

### Issue #1: x86/x64 PXE Boot - Stage 2 HTTP Chainload (ACTIVE - TESTING 🔄)
**Status:** ✅ TFTP Stage 1 FIXED and WORKING - Device successfully downloads undionly.kpxe and boots iPXE firmware  
**Current Test:** Device at 10.10.50.159 now needs to chainload HTTP menu from FastAPI  
**Test Date:** February 15, 2026 16:25 UTC  
**Next Steps:** Verify iPXE can reach API at 192.168.1.50:8000 for boot menu download
**Previous Symptom:** Device boots undionly.kpxe successfully, iPXE shell available, but HTTP chainload failed  
**Previous Error:** "Network unreachable (https://ipxe.org/2808b011)" when attempting `chain http://192.168.1.50:8000/api/v1/boot/ipxe/menu`  
**Previous Root Cause:** Device on 10.10.50.x VLAN cannot reach API on 192.168.1.50:8000 (inter-VLAN routing blocked or API unreachable)  
**Status:** ✅ **TFTP Stage 1 Fixed (commits 3b29df0, c1759df, d734a0a, 46a81a9)** - Numeric DHCP options, no vendor: syntax, inline-only config  
**Next:** Test Stage 2 (HTTP) - may need to debug inter-VLAN TCP routing or API accessibility

### Issue #2: DHCP Boot Loop (FIXED ✅)
**Original Symptom:** Device kept downloading undionly.kpxe in infinite loop, iPXE does DHCP again and still gets same bootloader filename  
**Root Cause:** dnsmasq wasn't properly detecting iPXE clients (syntax error in config)  
**Solution Applied (commits aa79947, 46a81a9, d734a0a):**
  1. Fixed dnsmasq config syntax: `option:60,iPXE*` instead of invalid `vendor:iPXE`
  2. Removed old config file copies that were conflicting with inline-generated config
  3. Return **empty filename** to iPXE: `dhcp-boot=tag:ipxe,,192.168.1.50,192.168.1.50` (prevents redownload)
  4. Reordered boot rules: BIOS first, iPXE second, UEFI last
**Boot Flow Now (Target):**
  - BIOS: DHCP → `undionly.kpxe` → Downloads via TFTP ✅
  - iPXE (2nd DHCP): Detected by `option:60,iPXE*` → No filename returned → Searches TFTP for boot.ipxe ✅
  - UEFI: DHCP → `ipxe.efi` → Downloads via TFTP ✅
**Status:** ✅ **Fixed in code** - Deployed to Unraid, awaiting test results

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

**Results (Updated Feb 15, 16:25 UTC):**
```
✅ Stage 1 (TFTP): undionly.kpxe downloaded (70810 bytes) - CONFIRMED ON REAL DEVICE
✅ Stage 1.5 (iPXE Boot): undionly.kpxe booted successfully - CONFIRMED
✅ iPXE Ready: Shell accessible via Ctrl+B, confirming iPXE 1.21.1+ loaded - CONFIRMED
✅ DHCP Detection: Device properly detected as iPXE (vendor class matching working)
🔄 Stage 2 (HTTP): boot.ipxe chainload to API - PENDING TEST
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
1. Read `netboot/Dockerfile.backend` (dnsmasq config + boot script generation)
2. Read `netboot/entrypoint-backend.sh` (service startup order)
3. Read `backend/app/api/v1.py` (boot menu endpoint logic)
4. Check `/data/tftp/boot.ipxe` inside container (actual script served)
5. Check DHCP logs: `docker logs netboot-backend 2>&1 | grep -i dhcp`

---

## 🎓 Developer Notes

- **2-Container Architecture** - netboot-backend (all services) + netboot-frontend (React)
- **Host Network Mode** - Both containers use `network_mode: host` for direct physical network access
- **No Bridge Isolation** - TFTP/DHCP/HTTP requests reach containers directly on host interfaces
- **Simplified Process Management** - Bash entrypoint script (no supervisor complexity)
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
