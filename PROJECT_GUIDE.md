# Netboot Orchestrator - Project Guide

**Last Updated:** February 16, 2026  
**Version:** 2026-02-16-V1  
**Status:** Boot menu working, WebUI fixed, ready for testing

---

## Quick Handoff Summary (For Next AI)

**What is this project?**  
A Docker-based PXE/iPXE network boot server running on Unraid NAS. Boots x86 devices over the network into OS installers. Two containers: backend (dnsmasq + FastAPI + iSCSI) and frontend (React SPA).

**Current state (Feb 16):**
- Boot menu is **working** — devices PXE boot, get iPXE, see interactive OS menu
- WebUI was **broken** (corrupted source code + wrong port) — now fixed
- Custom iPXE binary built at Docker build time with embedded boot script
- Proxy DHCP mode (no conflict with Unifi router)
- Version system: `YYYY-MM-DD-VN` (e.g., `2026-02-16-V1`)

**Deploy commands (Unraid):**
```bash
cd /mnt/user/appdata/netboot-orchestrator
git pull origin main
docker-compose build --no-cache
docker-compose up -d
```

---

## Architecture

### Network Setup
```
Boot VLAN (10.10.50.x)              Primary VLAN (192.168.1.x)
├─ Test VMs (VirtualBox)            ├─ Unraid NAS (192.168.1.50)
└─ Physical boot devices            └─ Unifi Router (primary DHCP)

netboot-backend (host network):
├─ dnsmasq    — Proxy DHCP + TFTP (UDP 67/69)
├─ FastAPI    — REST API + boot menu (TCP 8000)
├─ tgtd       — iSCSI target (TCP 3260)
└─ entrypoint-backend.sh manages all services

netboot-frontend (host network):
└─ Nginx + React SPA (TCP 30000)
    └─ Proxies /api/* to 127.0.0.1:8000
```

**Key design decisions:**
- **Host network mode** — both containers bind directly to host interfaces
- **Proxy DHCP** — dnsmasq does NOT assign IPs. Unifi router handles IP assignment. dnsmasq only injects PXE boot options
- **Custom iPXE binary** — compiled at Docker build time with embedded boot script (avoids "double iPXE" detection problem)
- **HTTP chainload** — iPXE chains to `http://SERVER:8000/api/v1/boot/ipxe/menu` (TCP, reliable across VLANs)

### Boot Flow
```
Device Powers On
    │
    ▼
DHCP Discover (broadcast)
    ├─ Unifi Router: assigns IP
    └─ dnsmasq proxy: injects boot-file=undionly.kpxe, next-server=192.168.1.50
    │
    ▼
TFTP download: undionly.kpxe (custom, ~72KB, has embedded script)
    │
    ▼
Embedded iPXE script runs:
    dhcp → chain http://${next-server}:8000/api/v1/boot/ipxe/menu
    │
    ▼
FastAPI returns interactive iPXE menu (categorized by OS type)
    │
    ▼
User selects OS → iPXE downloads installer via HTTP
```

---

## Key Files

| File | Purpose |
|------|---------|
| `netboot/Dockerfile.backend` | Multi-stage: builds custom iPXE from source, then installs services |
| `netboot/entrypoint-backend.sh` | Installs iPXE binary, creates boot scripts, generates dnsmasq config, starts services |
| `netboot/tftp/scripts/embed.ipxe` | Embedded boot script compiled into undionly.kpxe |
| `backend/app/api/v1.py` | FastAPI routes including `/api/v1/boot/ipxe/menu` |
| `backend/app/services/file_service.py` | Lists OS installer files from /isos volume |
| `frontend/nginx.conf` | Nginx: serves SPA on port 30000, proxies /api to 127.0.0.1:8000 |
| `frontend/src/App.tsx` | Main React app shell |
| `frontend/src/api/client.ts` | API client using `window.location.hostname:8000` |
| `docker-compose.yml` | Two containers, host network, volumes, env vars |
| `VERSION` | Current version (YYYY-MM-DD-VN format) |
| `version-bump.ps1` / `version-bump.sh` | Auto-increment version |

### iPXE Binary Build (Dockerfile Stage 1)
```dockerfile
FROM ubuntu:22.04 AS ipxe-builder
RUN git clone https://github.com/ipxe/ipxe.git --depth 1
COPY netboot/tftp/scripts/embed.ipxe /build/embed.ipxe
RUN cd ipxe/src && make bin/undionly.kpxe EMBED=/build/embed.ipxe
```
The embedded script (`embed.ipxe`) does `dhcp` then `chain http://${next-server}:8000/api/v1/boot/ipxe/menu`. This eliminates the classic problem where stock iPXE does DHCP again and gets `undionly.kpxe` in a loop.

### dnsmasq Configuration (generated at runtime)
```conf
port=0                           # Disable DNS
dhcp-range=10.10.50.0,proxy      # Proxy DHCP (no IP assignment)
dhcp-range=192.168.1.0,proxy
dhcp-userclass=set:ipxe,iPXE     # iPXE detection (user class)
dhcp-match=set:ipxe,175          # iPXE detection (option 175)
dhcp-boot=tag:ipxe,http://IP:8000/api/v1/boot/ipxe/menu  # iPXE → HTTP menu
dhcp-boot=tag:!ipxe,tag:bios,undionly.kpxe,,IP            # Legacy PXE → iPXE binary
```

### Boot Menu API
`GET /api/v1/boot/ipxe/menu` returns an iPXE script with:
- Device info (MAC, IP, gateway)
- OS installers categorized by type (Windows / Linux / Infrastructure / Other)
- File sizes displayed
- Error handling with retry
- No auto-select timeout (waits for user input)

---

## Issues Fixed (History)

| Date | Issue | Fix |
|------|-------|-----|
| Feb 16 | WebUI broken — App.tsx had terminal command pasted into variable name | Fixed corrupted line |
| Feb 16 | WebUI port wrong — nginx on 3000, expected 30000 | Changed to listen 30000 |
| Feb 16 | nginx proxy used Docker DNS (`http://api:8000`) | Changed to `127.0.0.1:8000` |
| Feb 16 | ImageManagement used hardcoded `localhost:8000` | Changed to `apiFetch()` |
| Feb 16 | Boot menu auto-selected before user could choose | Removed timeout from `choose` |
| Feb 16 | Stock undionly.kpxe had no embedded script → infinite loop | Multi-stage Docker build compiles custom iPXE |
| Feb 16 | boot.ipxe.org URLs return 404 | Build iPXE from source instead of downloading |
| Feb 16 | dnsmasq + Unifi DHCP conflict | Switched to proxy DHCP |
| Feb 16 | No iPXE client detection | Added option 175 + userclass detection |
| Feb 16 | TFTP cross-VLAN unreliable | Switched to HTTP chainload |
| Feb 16 | iPXE menu used broken `echo`+`choose` | Rewrote with `menu`/`item`/`choose` |
| Feb 15 | Volume mount shadows Dockerfile files | Entrypoint creates everything at runtime |

---

## Version System

Format: `YYYY-MM-DD-VN` where N increments per build on the same day.

```
2026-02-15-V1  ← First version
2026-02-16-V1  ← New day, reset to V1
2026-02-16-V2  ← Second build same day
```

**Bump version:**
```powershell
# Windows
.\version-bump.ps1

# Linux/Unraid
./version-bump.sh
```

The version is:
- Stored in `VERSION` file
- Read by FastAPI via `get_version()` in v1.py
- Displayed in WebUI footer
- Displayed in iPXE boot menu header

---

## Running the Project

### Prerequisites
- Docker & Docker Compose on Unraid
- Boot VLAN (10.10.50.x) routable to Unraid (192.168.1.50)
- Unifi router as primary DHCP server
- Optional: Unifi DHCP Option 66 (next-server) set to 192.168.1.50
- Optional: Unifi DHCP Option 67 (boot-file) set to undionly.kpxe

### Quick Start
```bash
cd /mnt/user/appdata/netboot-orchestrator
docker-compose build --no-cache
docker-compose up -d
```

### Verify
```bash
docker logs -f netboot-backend          # Should show "Custom undionly.kpxe installed"
curl http://192.168.1.50:8000/api/v1/boot/ipxe/menu   # Should return iPXE script
curl http://192.168.1.50:30000          # Should return HTML
docker exec netboot-backend ls -lh /data/tftp/         # Should show boot files
```

### Access
- **WebUI:** http://192.168.1.50:30000
- **API Docs:** http://192.168.1.50:8000/docs
- **Boot Menu API:** http://192.168.1.50:8000/api/v1/boot/ipxe/menu

---

## Project Structure

```
netboot-orchestrator/
├── backend/                          # FastAPI REST API
│   ├── app/
│   │   ├── main.py                  # App init, CORS
│   │   ├── database.py              # JSON file database
│   │   ├── models.py                # Pydantic models
│   │   ├── api/v1.py                # All API routes + boot menu
│   │   └── services/
│   │       ├── file_service.py      # OS installer file operations
│   │       ├── device_service.py    # Device management
│   │       └── image_service.py     # iSCSI image management
│   └── requirements.txt
│
├── frontend/                         # React + TypeScript + Vite
│   ├── Dockerfile                   # Build SPA + serve with Nginx on port 30000
│   ├── nginx.conf                   # Port 30000, proxy /api → 127.0.0.1:8000
│   ├── src/
│   │   ├── App.tsx                  # Main shell + navigation
│   │   ├── api/client.ts            # API helper (uses window.location.hostname)
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx        # Stats + recent devices
│   │   │   ├── Inventory.tsx        # Devices, images, installers, wizard tabs
│   │   │   └── SetupGuide.tsx       # Setup documentation
│   │   └── components/
│   │       ├── DeviceList.tsx        # CRUD for registered devices
│   │       ├── ImageManagement.tsx   # iSCSI image management
│   │       ├── OsInstallerList.tsx   # File browser + upload
│   │       └── UnknownDeviceWizard.tsx # Auto-register new devices
│   └── styles/index.css             # Dark theme CSS
│
├── netboot/
│   ├── Dockerfile.backend           # Multi-stage: iPXE build + services
│   ├── entrypoint-backend.sh        # Runtime orchestrator
│   └── tftp/scripts/embed.ipxe      # Embedded boot script
│
├── docker-compose.yml               # 2 containers, host network
├── data/                            # Persistent volume (mounted as /data)
├── VERSION                          # Current version (YYYY-MM-DD-VN)
├── version-bump.ps1                 # Version bump (Windows)
├── version-bump.sh                  # Version bump (Linux)
└── PROJECT_GUIDE.md                 # ← You are here
```

---

## Developer Notes

- **Proxy DHCP is critical** — dnsmasq must NOT assign IPs. The Unifi router does that.
- **Volume mount shadowing** — `./data:/data` hides Dockerfile files. Entrypoint must create/copy everything at runtime.
- **Custom iPXE build** — multi-stage Docker build compiles iPXE from source with embed.ipxe. Takes ~2 min on first build, cached after that.
- **`${next-server}` in embed.ipxe** — this iPXE variable is set by DHCP. It points to the TFTP server (Unraid). The embedded script uses it to chain to the HTTP API on the same host.
- **Host network mode** — both containers see all host interfaces. No port mapping needed. Frontend on 30000, API on 8000, TFTP on 69, iSCSI on 3260.
- **API client pattern** — frontend uses `window.location.hostname:8000` for API calls. This works from any browser regardless of server IP.
- **Boot menu categorization** — installers are auto-categorized by filename keywords (windows, ubuntu, proxmox, etc.)

---

## Next Steps

- [ ] Test WebUI on 192.168.1.50:30000 after rebuild
- [ ] iSCSI boot-from-disk testing
- [ ] Per-device boot profiles (assign specific OS per MAC)
- [ ] WinPE/Linux installer integration (not just ISO chain)
- [ ] ARM/Raspberry Pi boot support
- [ ] Boot analytics and logging
- [ ] Automatic device registration on first boot
