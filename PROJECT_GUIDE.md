# Netboot Orchestrator - Project Guide

**Last Updated:** February 16, 2026 (11:00 UTC)  
**Current Focus:** Deploy & test the proxy DHCP rewrite  
**Status:** 🔧 Code complete — needs `docker-compose build --no-cache && up -d` on Unraid

---

## ⚡ Quick Handoff Summary (For Next AI)

**What is this project?**
A Docker-based PXE/iPXE network boot server that lets you boot any x86 device over the network into OS installers served from an Unraid NAS.

**Where are we right now?**
- All code changes are done and committed locally  
- The three key files were rewritten on Feb 16:
  1. `netboot/entrypoint-backend.sh` — complete rewrite  
  2. `netboot/Dockerfile.backend` — simplified  
  3. `backend/app/api/v1.py` — iPXE menu endpoint fixed  
- **Needs push to GitHub + rebuild on Unraid to test**

**What changed on Feb 16 (this session)?**

| Change | Why |
|--------|-----|
| Switched dnsmasq to **proxy DHCP** mode | Was running full DHCP and fighting Unifi router for IP assignment |
| iPXE detection via **option 175** with `tag:!ipxe` rules | Old vendor-class detection didn't work; devices with built-in iPXE kept getting `undionly.kpxe` again |
| Entrypoint **downloads iPXE binaries** at runtime | Docker volume mount shadows Dockerfile-baked files — entrypoint runs after mount |
| Boot scripts use **heredoc** instead of printf one-liners | Readable, maintainable, prevents escaping bugs |
| `undionly.ipxe` chains via **HTTP** not TFTP | TFTP (UDP) has cross-VLAN routing issues; HTTP (TCP) works reliably |
| `BOOT_SERVER_IP` env var used everywhere | No more hardcoded 192.168.1.50 in scripts |
| API boot menu uses **menu/item/choose** iPXE syntax | Old code used `echo` + `choose` which doesn't work in iPXE |
| dnsmasq config **generated at runtime** by entrypoint | Supports env vars, no stale baked-in config |

**Deploy & Test:**
```bash
# On your dev machine:
git add -A && git commit -m "Rewrite: proxy DHCP, iPXE detection, HTTP chain" && git push

# On Unraid:
cd /mnt/user/appdata/netboot-orchestrator
git pull origin main
docker-compose down
docker-compose build --no-cache netboot-backend
docker-compose up -d
docker logs -f netboot-backend
```

**Expected log output after deploy:**
```
[TFTP] ✓ undionly.kpxe exists (70810 bytes)
[TFTP] ✓ ipxe.efi exists (1017856 bytes)
[TFTP] ✓ Boot scripts created
[dnsmasq] ✓ Configuration generated (proxy DHCP mode)
[dnsmasq] Started with PID ...
[FastAPI] Starting API server on 0.0.0.0:8000...
All services started successfully
```

**Then boot a test device and expect:**
1. Device DHCP → Unifi assigns IP ✅ + dnsmasq proxy sends PXE boot options ✅
2. Device downloads `undionly.kpxe` via TFTP → iPXE firmware loads
3. iPXE does DHCP again → dnsmasq detects iPXE (option 175) → serves `undionly.ipxe`
4. `undionly.ipxe` chains to `http://192.168.1.50:8000/api/v1/boot/ipxe/menu`
5. Interactive boot menu appears with OS installer list

---

## 🏗️ Architecture

### Network Setup
```
Boot VLAN (10.10.50.x)              Primary VLAN (192.168.1.x)
├─ Test VMs (VirtualBox/HyperV)     ├─ Unraid Server (192.168.1.50)
└─ Physical boot devices            │
                                    ├─ Unifi Router (DHCP for IP assignment)
                                    │
    ┌───────────────────────────────┘
    │
    ├─ netboot-backend container (host network)
    │  ├─ dnsmasq   — Proxy DHCP (PXE options only) + TFTP (UDP 69)
    │  ├─ FastAPI   — REST API + iPXE menu generator (TCP 8000)
    │  ├─ tgtd      — iSCSI target (TCP 3260)
    │  └─ entrypoint-backend.sh manages all services
    │
    └─ netboot-frontend container (host network)
       └─ React SPA (TCP 30000)
```

**Key design decisions:**
- **Host network mode** — both containers bind directly to host interfaces (no Docker bridge isolation)  
- **Proxy DHCP** — dnsmasq does NOT assign IPs. Unifi router handles all IP assignment. dnsmasq only injects PXE boot filename/server into the DHCP conversation  
- **Single backend container** — dnsmasq + FastAPI + tgtd all managed by a bash entrypoint script

### Container Stack
```
netboot-backend:
├─ entrypoint-backend.sh (process manager)
│  ├─ 1. Download iPXE binaries (undionly.kpxe, ipxe.efi) if missing
│  ├─ 2. Create boot scripts (undionly.ipxe, boot.ipxe, boot-menu.ipxe)
│  ├─ 3. Generate dnsmasq proxy DHCP config
│  ├─ 4. Start dnsmasq, tgtd, FastAPI
│  └─ 5. Generate boot menu from API every 5 minutes
├─ dnsmasq v2.90 — Proxy DHCP + TFTP
├─ FastAPI (Uvicorn) — Boot menu API on port 8000
└─ tgtd — iSCSI target on port 3260

netboot-frontend:
└─ React + Vite SPA on port 30000
```

---

## 🎯 Boot Flow

```
Device Powers On
    │
    ▼
DHCP Discover (broadcast)
    │
    ├─ Unifi Router responds: IP=10.10.50.XXX, gateway, DNS
    └─ dnsmasq proxy responds: boot-file=undionly.kpxe, next-server=192.168.1.50
    │
    ▼
Stage 1: TFTP download undionly.kpxe (70KB iPXE binary)
    │
    ▼
iPXE firmware initializes (iPXE 1.21.1+)
    │
    ▼
iPXE DHCP Discover (with option 175 = iPXE encapsulated options)
    │
    ├─ Unifi Router responds: IP (same lease)
    └─ dnsmasq proxy: detects option 175 → boot-file=undionly.ipxe
    │
    ▼
Stage 2: TFTP download undionly.ipxe (boot script)
    │
    ▼
undionly.ipxe executes:
    dhcp
    chain http://192.168.1.50:8000/api/v1/boot/ipxe/menu
    │
    ▼
Stage 3: HTTP → FastAPI returns interactive iPXE menu
    │
    ▼
User selects OS installer → device boots
```

### TFTP Files (created by entrypoint at runtime)
```
/data/tftp/
├── undionly.kpxe    (~70KB)   — iPXE BIOS binary (downloaded from boot.ipxe.org)
├── ipxe.efi         (~1MB)   — iPXE UEFI binary (downloaded from boot.ipxe.org)
├── undionly.ipxe    (~600B)  — Stage 2 script: dhcp + chain to HTTP API menu
├── boot.ipxe        (~80B)   — Backup script: dhcp + chain to HTTP API menu
└── boot-menu.ipxe   (~300B)  — Placeholder menu (replaced by API-generated menu)
```

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `netboot/entrypoint-backend.sh` | **Main orchestrator** — downloads iPXE binaries, creates boot scripts, generates dnsmasq config, starts all services |
| `netboot/Dockerfile.backend` | Simple Dockerfile — installs packages, copies code, pre-downloads iPXE (cache layer) |
| `backend/app/api/v1.py` | FastAPI routes including `/api/v1/boot/ipxe/menu` (generates iPXE menu) |
| `backend/app/services/file_service.py` | Lists OS installer files from /isos volume |
| `docker-compose.yml` | Defines both containers, volumes, env vars |
| `data/tftp/` | TFTP root (mounted volume, populated by entrypoint) |

### dnsmasq Configuration (generated at runtime)

The entrypoint generates `/etc/dnsmasq.d/netboot.conf` with these key settings:

```conf
# Proxy DHCP — no IP assignment
dhcp-range=10.10.50.0,proxy
dhcp-range=192.168.1.0,proxy

# iPXE detection via option 175
dhcp-match=set:ipxe,175

# Architecture detection
dhcp-match=set:bios,93,0
dhcp-match=set:efi64,93,9

# Boot file assignment (iPXE gets script, non-iPXE gets binary)
dhcp-boot=tag:ipxe,undionly.ipxe,,BOOT_IP
dhcp-boot=tag:!ipxe,tag:bios,undionly.kpxe,,BOOT_IP
dhcp-boot=tag:!ipxe,tag:efi64,ipxe.efi,,BOOT_IP
```

**Why proxy DHCP?** The Unifi router is the primary DHCP server. Running a second full DHCP server causes IP conflicts and race conditions. Proxy mode lets dnsmasq inject PXE options into the DHCP conversation without touching IP assignment.

**Why option 175?** iPXE sends option 175 (encapsulated options) in every DHCP request. This is the most reliable way to distinguish "this device already has iPXE" from "this device has legacy PXE ROM". The `tag:!ipxe` rules ensure only non-iPXE devices get the binary bootloader.

### iPXE Boot Menu API

`GET /api/v1/boot/ipxe/menu` returns a valid iPXE script using proper `menu`/`item`/`choose` syntax:

```ipxe
#!ipxe
:menu
menu Netboot Orchestrator - OS Installation Menu
item --gap --                        Device Information
item --gap --  MAC: ${net0/mac}
item --gap --
item --gap --                        Available OS Installers
item installer_1    1) ubuntu-22.04.iso (4.20GB)
item installer_2    2) windows-server-2022.iso (5.10GB)
item --gap --
item shell     Drop to iPXE Shell
item reboot    Reboot
choose --timeout 120 --default installer_1 selected || goto shell
goto ${selected}

:installer_1
chain http://192.168.1.50:8000/api/v1/os-installers/download/ubuntu-22.04.iso || goto menu
```

---

## 🐛 Issues Fixed (History)

| Date | Issue | Root Cause | Fix |
|------|-------|-----------|-----|
| Feb 16 | dnsmasq + Unifi DHCP conflict | Two full DHCP servers on same network | Switched to proxy DHCP mode |
| Feb 16 | iPXE devices re-downloading undionly.kpxe | No iPXE client detection | Added option 175 detection + `tag:!ipxe` rules |
| Feb 16 | `timeout 15 chain ...` invalid iPXE syntax | iPXE has no `timeout` command prefix | Removed; use plain `chain ... \|\| goto retry` |
| Feb 16 | TFTP cross-VLAN chainload fails | UDP routing unreliable across VLANs | Switched to HTTP chainload (TCP) |
| Feb 16 | iPXE menu `choose` without `menu`/`item` | `choose` requires `item` declarations | Rewrote API to use `menu`/`item`/`choose` syntax |
| Feb 16 | Hardcoded 192.168.1.50 in scripts | Not configurable | Use `BOOT_SERVER_IP` env var from docker-compose |
| Feb 16 | dnsmasq `port=69` setting | Sets DNS port, not TFTP — conflicts | Changed to `port=0` (DNS disabled) |
| Feb 15 | undionly.kpxe not found on TFTP | Volume mount shadows Dockerfile files | Entrypoint downloads at runtime |
| Feb 15 | Boot scripts missing from container | Volume mount shadows Dockerfile files | Entrypoint creates scripts at runtime |
| Feb 15 | iPXE boot loop (re-downloads binary) | BIOS/iPXE DHCP rule ordering | iPXE rule first; later replaced with tag:!ipxe |
| Feb 15 | API 500 error on boot menu | Dict iteration bug | Fixed dict.get('files', []) |
| Feb 15 | dnsmasq parse errors | Invalid option syntax | Numeric DHCP options (93,0 not option:client-arch) |

---

## 🔄 Current Status & Next Steps

### ✅ Completed
- [x] Consolidated backend container (dnsmasq + FastAPI + tgtd)
- [x] Host network mode (no Docker bridge isolation)
- [x] Proxy DHCP mode (no conflict with Unifi router)
- [x] iPXE binary download in entrypoint (survives volume mount)
- [x] iPXE client detection (option 175)
- [x] HTTP chainload (cross-VLAN reliable)
- [x] Proper iPXE menu syntax (menu/item/choose)
- [x] BOOT_SERVER_IP env var support
- [x] Boot scripts created by entrypoint (heredoc format)
- [x] dnsmasq config generated at runtime
- [x] FastAPI boot menu API endpoint
- [x] React frontend (port 30000)

### 🔧 Needs Testing (Feb 16)
- [ ] **Deploy to Unraid** — push code, rebuild, test device boot
- [ ] **Stage 1** — device downloads undionly.kpxe via TFTP
- [ ] **Stage 2** — iPXE loads undionly.ipxe, chains to HTTP API
- [ ] **Stage 3** — interactive boot menu appears, user can select OS
- [ ] **Cross-VLAN** — test from 10.10.50.x VLAN to 192.168.1.50

### ⏳ Future Work
- [ ] ARM/Raspberry Pi boot support (U-Boot)
- [ ] iSCSI boot-from-disk testing
- [ ] Device registration UI (auto-register MAC on first boot)
- [ ] Per-device boot profiles
- [ ] Windows/Linux installer integration (WinPE, preseed, kickstart)
- [ ] Monitoring & boot analytics

---

## 🐳 Running the Project

### Prerequisites
- Docker & Docker Compose
- Network: boot VLAN (10.10.50.x) routable to Unraid (192.168.1.50)
- Unifi router as primary DHCP server

### Quick Start
```bash
cd /mnt/user/appdata/netboot-orchestrator   # on Unraid
# or
cd c:\Users\Kronborgs_LabPC\netboot-orchestrator  # on dev machine

docker-compose build --no-cache netboot-backend
docker-compose up -d
```

### Verify
```bash
# Check logs
docker logs -f netboot-backend

# Test API
curl http://192.168.1.50:8000/api/v1/boot/ipxe/menu

# Check TFTP files
docker exec netboot-backend ls -lh /data/tftp/

# Frontend
curl http://192.168.1.50:30000
```

### Rebuild After Code Changes
```bash
docker-compose down
docker-compose build --no-cache netboot-backend
docker-compose up -d
```

---

## 📝 Project Structure

```
netboot-orchestrator/
├── backend/                          # FastAPI REST API
│   ├── app/
│   │   ├── main.py                  # App init
│   │   ├── api/v1.py                # All API routes (boot menu, devices, etc.)
│   │   └── services/file_service.py # OS installer file listing
│   └── requirements.txt
│
├── frontend/                         # React + TypeScript + Vite
│   ├── src/App.tsx
│   └── package.json
│
├── netboot/
│   ├── Dockerfile.backend           # Container image (packages + iPXE cache)
│   └── entrypoint-backend.sh        # Runtime setup + service manager
│
├── docker-compose.yml               # 2 containers, host network, volumes
│
├── data/                            # Persistent volume
│   └── tftp/                        # TFTP root (populated by entrypoint)
│       ├── undionly.kpxe            # iPXE BIOS binary
│       ├── ipxe.efi                 # iPXE UEFI binary
│       ├── undionly.ipxe            # Boot script (chains to HTTP API)
│       ├── boot.ipxe                # Backup boot script
│       └── boot-menu.ipxe           # API-generated menu
│
└── PROJECT_GUIDE.md                  # ← You are here
```

---

## 🎓 Developer Notes

- **Proxy DHCP is critical** — dnsmasq must NOT assign IPs. The Unifi router does that. dnsmasq only injects PXE boot options.
- **Volume mount shadowing** — `./data:/data` in docker-compose hides any files baked into the image at `/data`. That's why the entrypoint must create/download everything at runtime.
- **option 175 for iPXE detection** — more reliable than vendor class (option 60). All iPXE builds send option 175.
- **`tag:!ipxe`** — the `!` negation in dnsmasq rules means "when the ipxe tag is NOT set". This prevents iPXE devices from re-downloading the binary.
- **HTTP chain over TFTP** — iPXE's `chain http://...` uses TCP, which routes reliably across VLANs. TFTP uses UDP which often gets blocked or has MTU issues.
- **heredoc with 'QUOTED' delimiter** — `<< 'EOF'` prevents bash from expanding `${variables}`, which preserves iPXE's `${mac}`, `${net0/ip}` etc. literally.
- **Boot menu regeneration** — the entrypoint saves the API-generated menu to `/data/tftp/boot-menu.ipxe` every 5 minutes. This is a TFTP fallback; primary path is direct HTTP chain to the API.

---

## 🔗 Quick Links

- **Frontend:** http://192.168.1.50:30000
- **API Docs:** http://192.168.1.50:8000/docs
- **Boot Menu API:** http://192.168.1.50:8000/api/v1/boot/ipxe/menu
- **GitHub:** https://github.com/Kronborgs/netboot-orchestrator (branch: main)
