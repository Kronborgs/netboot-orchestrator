# Netboot Orchestrator - Project Guide

**Last Updated:** February 21, 2026  
**Version:** 2026-02-21-V150  
**Status:** Fully operational — PXE boot, iSCSI, WebUI, CI/CD all working  
**Branding:** Designed by Kenneth Kronborg AI Team

---

## Quick Handoff Summary (For Next AI)

**What is this project?**  
A Docker-based PXE/iPXE network boot server running on Unraid NAS. Single all-in-one container (dnsmasq + FastAPI + tgtd + nginx + React SPA). Boots x86 devices over the network into OS installers or iSCSI disk images. Pre-built image pulled from GitHub Container Registry.

**Current state (V3):**
- **Everything working** — PXE boot, interactive iPXE menus, OS installer browsing, iSCSI image create/copy/link/boot, WebUI, boot logging
- **Windows install flow implemented** — iPXE Windows installer select menu, WinPE (`wimboot`) boot, iSCSI system disk attach, installer ISO media attach
- **WinPE autostart implemented** — backend serves `startnet.cmd` that auto-finds installer media and launches `setup.exe`
- **OS installer refresh reliability fixed** — folder/file cache invalidates on background refresh so new files appear in WebUI and menus quickly
- **All-in-one Docker image** published to `ghcr.io/kronborgs/netboot-orchestrator:latest`
- **CI/CD** via GitHub Actions — builds and pushes on every push to `main`
- **Unraid template** (`unraid-template.xml`) for one-click install in Community Applications
- **Proxy DHCP mode** — no conflict with Unifi router (or any primary DHCP)
- **Custom iPXE binary** compiled at Docker build time with embedded boot script
- **Configurable DHCP subnets** via `DHCP_SUBNETS` env var
- **HTTP Range requests** for `sanboot` ISO booting

**Deploy on Unraid (Option A — Template):**
Add `unraid-template.xml` to Unraid Community Applications, or manually add container from `ghcr.io/kronborgs/netboot-orchestrator:latest`.

**Deploy on Unraid (Option B — Manual):**
```bash
docker pull ghcr.io/kronborgs/netboot-orchestrator:latest
# Then add container via Unraid Docker UI with settings from unraid-template.xml
```

**Deploy with Docker Compose:**
```bash
docker-compose up -d
```

---

## Architecture

### Single All-in-One Container
```
netboot-orchestrator (host network, privileged):
├─ dnsmasq v2.90   — Proxy DHCP + TFTP server (UDP 67, 69)
├─ FastAPI/Uvicorn  — REST API + iPXE boot menu generator (TCP 8000)
├─ tgtd             — iSCSI target daemon (TCP 3260)
├─ nginx            — React SPA + API proxy (TCP 30000)
└─ entrypoint-backend.sh orchestrates all services
```

### Network Setup
```
Boot VLAN (10.10.50.x)              Primary VLAN (192.168.1.x)
├─ Test VMs (VirtualBox)            ├─ Unraid NAS (192.168.1.50)
└─ Physical boot devices            └─ Unifi Router (primary DHCP)
```

All services run in a single container on host network. Configure `DHCP_SUBNETS` env var with comma-separated subnets to serve (e.g., `10.10.50.0,192.168.1.0`).

**Key design decisions:**
- **Single container** — all services (dnsmasq, FastAPI, tgtd, nginx) in one Docker image for Unraid simplicity
- **Host network mode** — binds directly to host interfaces (required for DHCP/TFTP/iSCSI)
- **Proxy DHCP** — dnsmasq does NOT assign IPs. Primary router (Unifi) handles IP assignment. dnsmasq only injects PXE boot options
- **Custom iPXE binary** — compiled at Docker build time with embedded boot script (avoids iPXE loop detection problem)
- **HTTP chainload** — iPXE chains to `http://${next-server}:8000/api/v1/boot/ipxe/menu` (TCP, reliable across VLANs)
- **JSON file database** — no SQL database, all data in JSON files under `/data/`
- **`sanboot --no-describe`** — used for booting ISOs/IMGs over HTTP (not `chain`, which treats them as iPXE scripts)

### Boot Flow
```
Device Powers On
    │
    ▼
DHCP Discover (broadcast)
    ├─ Primary Router: assigns IP
    └─ dnsmasq proxy: injects boot-file + next-server
    │
    ▼
Architecture Detection by dnsmasq:
    ├─ BIOS (x86)  → undionly.kpxe via TFTP
    ├─ EFI 32-bit  → ipxe.efi via TFTP
    └─ EFI 64-bit  → ipxe.efi via TFTP
    │
    ▼
TFTP download: custom iPXE binary (~72KB, embedded script)
    │
    ▼
Embedded iPXE script (embed.ipxe):
    dhcp → chain http://${next-server}:8000/api/v1/boot/ipxe/menu
    │
    ▼
FastAPI returns interactive iPXE menu:
    ┌─────────────────────────────────────┐
    │  Netboot Orchestrator               │
    │  MAC: aa:bb:cc:dd:ee:ff             │
    │  IP: 10.10.50.100                   │
    ├─────────────────────────────────────┤
    │  [1] OS Installers  →              │
    │  [2] Create iSCSI Image            │
    │  [3] Link iSCSI Image             │
    │  [4] Boot iSCSI Disk              │
    │  [5] Windows Install (WinPE+iSCSI) │
    │  [6] Device Info                   │
    │  [7] iPXE Shell                    │
    │  [8] Reboot                        │
    └─────────────────────────────────────┘
    │
    ├─ OS Installers → folder navigation → sanboot ISO
    ├─ Create iSCSI → pick size → creates image + links to device → OS menu
    ├─ Link iSCSI → pick image → links to device
    ├─ Boot iSCSI → sanboot iscsi:IP::::IQN
    └─ Windows Install → select installer ISO → sanhook system disk + media attach + wimboot + WinPE autostart `setup.exe`
```

### OS Installer Boot Flow
```
OS Installers submenu → folder navigation (breadcrumbs)
    │
    ▼
User selects an ISO/IMG/EFI file
    │
    ▼
File extension detection:
    ├─ .iso / .img → sanboot --no-describe http://SERVER:8000/api/v1/os-installers/download/PATH
    └─ .efi / other → chain http://SERVER:8000/api/v1/os-installers/download/PATH
    │
    ▼
FastAPI serves file with Range request support (206 Partial Content)
    └─ Required by iPXE sanboot (HEAD + Range requests)
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOOT_SERVER_IP` | **Yes** | — | IP address of the host running the container (e.g., `192.168.1.50`) |
| `DHCP_SUBNETS` | **Yes** | — | Comma-separated subnets for proxy DHCP (e.g., `10.10.50.0,192.168.1.0`) |
| `OS_INSTALLERS_PATH` | No | `/isos` | Path inside container where OS installer ISOs are mounted |
| `IMAGES_PATH` | No | `/iscsi-images` | Path inside container where iSCSI disk images are stored |
| `DATA_PATH` | No | `/data` | Path for persistent data (JSON DB, TFTP files, boot scripts) |
| `WINDOWS_WINPE_PATH` | No | `winpe` | Relative folder under `OS_INSTALLERS_PATH` containing `wimboot`, `boot/BCD`, `boot/boot.sdi`, `sources/boot.wim` |
| `WINDOWS_OS_INSTALLER_ISO_PATH` | No | empty | Relative path under `OS_INSTALLERS_PATH` to a full Windows installer ISO; backend exports it as iSCSI CD media for WinPE |
| `WINDOWS_INSTALLER_ISO_SAN_URL` | No | empty | Optional SAN URL for installer media mounted as iPXE drive `0x81` (example: `iscsi:IP::::IQN`) |
| `WINDOWS_INSTALLER_ISO_PATH` | No | empty | Optional fallback relative file path under `OS_INSTALLERS_PATH` to mount as media on `0x81` |
| `TZ` | No | `UTC` | Container/application timezone (e.g., `Europe/Copenhagen`) used for logs and timestamps |
| `API_HOST` | No | `0.0.0.0` | FastAPI listen address |
| `API_PORT` | No | `8000` | FastAPI listen port |
| `LOG_LEVEL` | No | `info` | Uvicorn log level |

### Unraid Env Var Quirk: `_env()` Helper
Unraid's Docker UI sometimes appends trailing spaces to environment variable names (e.g., `BOOT_SERVER_IP ` instead of `BOOT_SERVER_IP`). The `_env(name)` helper function in the Python code checks both the exact name and the space-suffixed variant:

```python
def _env(name: str, default: str = "") -> str:
    return os.getenv(name) or os.getenv(name + " ") or default
```

This is used in `boot.py`, `v1.py`, `image_service.py`, and `main.py`. If you add new env var reads, always use `_env()` instead of `os.getenv()`.

---

## Key Files

### Docker & Deployment

| File | Purpose |
|------|---------|
| `Dockerfile` (root) | All-in-one multi-stage build: iPXE compile → React build → Ubuntu runtime |
| `docker-compose.yml` | Single container using `ghcr.io/kronborgs/netboot-orchestrator:latest` |
| `unraid-template.xml` | Unraid Community Applications template with configurable UI variables |
| `.github/workflows/docker-build.yml` | CI/CD: builds image, pushes to `ghcr.io` on every push to `main` |
| `VERSION` | Current version string (`YYYY-MM-DD-VN` format) |
| `version-bump.ps1` / `version-bump.sh` | Auto-increment the version |

### Backend (FastAPI + Python)

| File | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI app init, CORS, lifespan hook (restores iSCSI targets on startup) |
| `backend/app/database.py` | JSON file-based database (profiles, images, os, settings, unknown_devices, boot_logs) |
| `backend/app/models.py` | Pydantic models |
| `backend/app/api/boot.py` | iPXE boot menu endpoints + iSCSI REST API + boot log API |
| `backend/app/api/v1.py` | REST API for devices, OS installers (with HEAD + Range support), storage, version |
| `backend/app/services/file_service.py` | OS installer file operations (browse, tree, list, upload, delete) |
| `backend/app/services/image_service.py` | `IscsiService` class — manages tgtd targets, disk images, device links |
| `backend/app/services/device_service.py` | Device management helpers |
| `backend/requirements.txt` | Python deps: fastapi, uvicorn, pydantic, aiofiles, httpx, python-multipart, watchdog |

### Frontend (React + TypeScript + Vite)

| File | Purpose |
|------|---------|
| `frontend/nginx.conf` | Serves SPA on port 30000, proxies `/api` to `127.0.0.1:8000` |
| `frontend/src/App.tsx` | Main shell: 3 pages (Dashboard, Inventory, Setup Guide), dark mode, version display |
| `frontend/src/api/client.ts` | API client using `window.location.hostname:8000` (works from any browser) |
| `frontend/src/pages/Dashboard.tsx` | Stats cards (active devices, iSCSI images, OS installers, storage) + recent devices |
| `frontend/src/pages/Inventory.tsx` | 5 tabs: Devices, iSCSI Images, OS Installers, Boot Logs, Device Wizard |
| `frontend/src/pages/SetupGuide.tsx` | In-app setup documentation |
| `frontend/src/components/DeviceList.tsx` | CRUD for registered devices |
| `frontend/src/components/ImageManagement.tsx` | iSCSI image management (was ImageManagement, now IscsiManagement) |
| `frontend/src/components/OsInstallerList.tsx` | File browser + upload for OS installers |
| `frontend/src/components/UnknownDeviceWizard.tsx` | Auto-register unknown devices that PXE boot |

### Boot Infrastructure

| File | Purpose |
|------|---------|
| `netboot/entrypoint-backend.sh` | Runtime orchestrator: installs iPXE, generates dnsmasq config, starts all services |
| `netboot/tftp/scripts/embed.ipxe` | Boot script embedded into iPXE binary at compile time |
| `netboot/Dockerfile.backend` | Legacy separate backend Dockerfile (superseded by root `Dockerfile`) |

---

## Docker Image Build (3-Stage Dockerfile)

### Stage 1: iPXE Compile
```dockerfile
FROM ubuntu:22.04 AS ipxe-builder
RUN git clone https://github.com/ipxe/ipxe.git --depth 1
COPY netboot/tftp/scripts/embed.ipxe /build/embed.ipxe
RUN cd ipxe/src && make bin/undionly.kpxe EMBED=/build/embed.ipxe
```
Compiles a custom `undionly.kpxe` with `embed.ipxe` baked in. This eliminates the classic problem where stock iPXE does DHCP again and gets `undionly.kpxe` in an infinite loop.

### Stage 2: React Frontend
```dockerfile
FROM node:18-alpine AS frontend-builder
COPY frontend/ .
RUN npm install && npm run build
```
Produces static files in `/app/dist`.

### Stage 3: Runtime
Ubuntu 22.04 with python3, dnsmasq, tgt, nginx, net-tools, iproute2. Combines:
- Custom `undionly.kpxe` → `/opt/ipxe/`
- Frontend dist → `/usr/share/nginx/html`
- Backend app → `/app/backend/`
- `entrypoint-backend.sh` → `/entrypoint.sh`
- nginx config installed as `/etc/nginx/sites-available/netboot` (default site removed)

**Exposed ports:** 69/udp (TFTP), 67/udp (DHCP), 8000 (API), 30000 (WebUI), 3260 (iSCSI)

---

## Entrypoint Startup Sequence

`entrypoint-backend.sh` runs these steps in order:

| Step | Action |
|------|--------|
| 1 | Copies custom `undionly.kpxe` from `/opt/ipxe/` to `/data/tftp/` (falls back to download if missing) |
| 2 | Generates `undionly.ipxe` (stage 2 script), `boot.ipxe`, `boot-menu.ipxe` placeholder |
| 3 | Creates Raspberry Pi TFTP directories (`/data/tftp/raspi/`) with README |
| 4 | Generates `/etc/dnsmasq.d/netboot.conf` with proxy DHCP for each subnet in `DHCP_SUBNETS` |
| 5 | Starts **dnsmasq** (background) |
| 6 | Starts **nginx** on port 30000 (background) |
| 7 | Starts **tgtd** iSCSI daemon (background) |
| 8 | Starts **FastAPI** via uvicorn on port 8000 (background) |
| 9 | Curls `/api/v1/boot/ipxe/menu` → saves to `/data/tftp/boot-menu.ipxe` |
| 10 | Starts background loop: regenerates boot menu every 5 minutes |
| 11 | Waits on FastAPI PID (keeps container alive) |

---

## dnsmasq Configuration (Generated at Runtime)

```conf
port=0                                    # Disable DNS
log-dhcp                                  # Log DHCP transactions
dhcp-range=10.10.50.0,proxy               # Proxy DHCP per subnet (from DHCP_SUBNETS)
dhcp-range=192.168.1.0,proxy
dhcp-userclass=set:ipxe,iPXE              # iPXE detection (user class)
dhcp-match=set:ipxe,175                   # iPXE detection (option 175)
dhcp-match=set:bios,93,0                       # BIOS detection
dhcp-match=set:efi32,93,6                      # EFI 32-bit
dhcp-match=set:efibc,93,7                      # EFI BC
dhcp-match=set:efi64,93,9                      # EFI 64-bit
dhcp-boot=tag:ipxe,http://IP:8000/api/v1/boot/ipxe/menu   # iPXE → HTTP menu
dhcp-boot=tag:!ipxe,tag:bios,undionly.kpxe,,IP              # BIOS PXE → iPXE
dhcp-boot=tag:!ipxe,tag:efi32,ipxe.efi,,IP                 # EFI 32 → iPXE EFI
dhcp-boot=tag:!ipxe,tag:efi64,ipxe.efi,,IP                 # EFI 64 → iPXE EFI
enable-tftp                               # Enable built-in TFTP
tftp-root=/data/tftp                      # TFTP root directory
```

The `DHCP_SUBNETS` env var is parsed at startup — each comma-separated subnet gets its own `dhcp-range=SUBNET,proxy` line.

---

## API Endpoints Reference

### Boot Endpoints (`/api/v1/boot/...`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/ipxe/menu` | Main iPXE boot menu (entry point for PXE clients) |
| GET | `/ipxe/os-menu` | OS installer folder browser (with `?path=` navigation) |
| GET | `/ipxe/iscsi-create` | iSCSI image creation: pick size (4/32/64/128/256 GB) |
| GET | `/ipxe/iscsi-do-create` | Action: create iSCSI image + auto-link to device → redirect to OS menu |
| GET | `/ipxe/iscsi-link` | Show available iSCSI images for linking |
| GET | `/ipxe/iscsi-do-link` | Action: link device to image |
| GET | `/ipxe/iscsi-do-unlink` | Action: unlink device from image |
| GET | `/ipxe/iscsi-boot` | Boot device from linked iSCSI target (`sanboot iscsi:...`) |
| GET | `/check-in` | Device check-in at boot time (records boot event) |
| POST | `/log` | Record a boot event |
| GET | `/logs` | Get boot logs (optional `?mac=` filter) |

### iSCSI REST Endpoints (`/api/v1/boot/iscsi/...`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/images` | List all iSCSI images (used by WebUI dashboard) |
| POST | `/images` | Create iSCSI image (query params: `name`, `size_gb`) |
| DELETE | `/images/{name}` | Delete iSCSI image + tgtd target |
| POST | `/images/{name}/copy` | Copy iSCSI image (query param: `dest_name`) |
| POST | `/images/{name}/link` | Link image to device (query param: `mac`) |
| POST | `/images/{name}/unlink` | Unlink image from device |

### REST API Endpoints (`/api/v1/...`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/version` | App version from VERSION file |
| GET/POST | `/devices` | List / create devices |
| GET/PUT/DELETE | `/devices/{mac}` | Get / update / delete device |
| GET/POST | `/images` | List / create images (DB records) |
| GET/PUT/DELETE | `/images/{image_id}` | Get / update / delete image (DB records) |
| PUT | `/images/{image_id}/assign` | Assign image to device |
| PUT | `/images/{image_id}/unassign` | Unassign image |
| GET | `/os-installers/tree` | Full folder tree of OS installers |
| GET | `/os-installers/browse` | Browse folder contents (lazy) |
| GET | `/os-installers/files` | List all bootable OS installer files |
| GET | `/os-installers/files/{path}` | File info for specific installer |
| DELETE | `/os-installers/files/{path}` | Delete installer file |
| POST | `/os-installers/upload` | Upload OS installer |
| GET | `/os-installers/metadata` | List OS installer metadata |
| POST | `/os-installers/metadata` | Create OS installer metadata |
| **HEAD** | `/os-installers/download/{path}` | **HEAD for iPXE sanboot** (returns Accept-Ranges + Content-Length) |
| **GET** | `/os-installers/download/{path}` | **Serve installer with HTTP Range (206) support** |
| GET | `/storage/info` | Storage usage info (total size in GB) |
| GET | `/unknown-devices` | List unknown devices |
| POST | `/unknown-devices/record` | Record unknown booting device |
| GET/DELETE | `/unknown-devices/{mac}` | Get / remove unknown device |
| POST | `/unknown-devices/register` | Register unknown device → create profile |
| GET | `/kernel-sets` | List kernel sets |
| POST | `/kernel-sets` | Create kernel set |

### Utility Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Root info (name, version, branding, docs link) |
| GET | `/health` | Health check (`{"status": "healthy"}`) |

---

## iSCSI Management

### How It Works
- **tgtd** (Linux SCSI target daemon) runs inside the container
- Disk images are sparse files created with `truncate` (don't consume full size until written)
- Each image is registered as a tgtd target with IQN `iqn.2024.netboot:IMAGENAME`
- Devices are linked to images via the JSON database
- On container restart, `IscsiService.restore_targets()` re-registers all known images

### From iPXE Boot Menu
1. **Create iSCSI Image** → pick size (4/32/64/128/256 GB) → image created + auto-linked to booting device → redirects to OS Installers menu (so user can install an OS onto the iSCSI disk)
2. **Link iSCSI Image** → pick from existing images → linked to booting device
3. **Boot iSCSI Disk** → `sanboot iscsi:SERVER::::IQN` — boots from linked image
4. **Unlink iSCSI Image** → removes device link

### From WebUI
The Inventory → iSCSI Images tab provides full management: create, delete, copy, link/unlink devices.

### File Layout
```
/iscsi-images/
├── windows-pc01.img     # Sparse file, e.g., 64GB
├── linux-dev.img        # Sparse file
└── ...
```

### tgtd Commands Used Internally
```bash
tgtadm --lld iscsi --op new --mode target --tid N --targetname iqn.2024.netboot:NAME
tgtadm --lld iscsi --op new --mode logicalunit --tid N --lun 1 --backing-store /iscsi-images/NAME.img
tgtadm --lld iscsi --op bind --mode target --tid N -I ALL
tgtadm --lld iscsi --op delete --mode target --tid N --force
```

---

## iPXE Gotchas & Workarounds

### ASCII Only
iPXE cannot render Unicode characters. Smart quotes (`'` U+2019), em dashes, etc. cause garbled output like `%FFFFFFE2%FFFFFF80%FFFFFF99`. The `_ascii_safe()` function strips non-ASCII characters from display names:

```python
def _ascii_safe(text: str) -> str:
    return text.encode('ascii', 'replace').decode('ascii')
```

All iPXE menu item labels are processed through `_ascii_safe()`. File download URLs use `urllib.parse.quote()` to URL-encode special characters.

### sanboot vs chain
- **`chain`** — treats the downloaded file as an iPXE script and tries to execute it. Works for `.efi` and `.ipxe` files. Fails with "Exec format error" on ISOs.
- **`sanboot --no-describe`** — treats the URL as a SAN (Storage Area Network) device and boots from it. Required for `.iso` and `.img` files. The `--no-describe` flag disables SCSI DESCRIBE which causes HTTP errors with some servers.

### HTTP Range Requests for sanboot
iPXE's `sanboot` over HTTP requires the server to support:
1. **HEAD requests** — must return `Accept-Ranges: bytes` and `Content-Length`
2. **Range requests** — must return `206 Partial Content` with the requested byte range

Both are implemented in `v1.py` at the `/os-installers/download/{path}` endpoint using `StreamingResponse` for memory-efficient streaming of large ISOs.

---

## WebUI Structure

### Pages
1. **Dashboard** — 4 stat cards (Active Devices, iSCSI Images, OS Installers, Storage Used) + Recent Devices list. Auto-refreshes every 30 seconds.
2. **Inventory** — 5 tabs:
   - **Devices** — CRUD for registered boot devices
   - **iSCSI Images** — Create/delete/copy/link/unlink iSCSI disk images
   - **OS Installers** — File browser + upload for ISO/IMG/EFI files
   - **Boot Logs** — Live boot event log viewer (last 500 entries, filterable by MAC)
   - **Device Wizard** — Auto-register unknown devices that PXE boot
3. **Setup Guide** — In-app documentation

### Branding
Footer displays: version string + "Designed by Kenneth Kronborg AI Team"

### API Client
`frontend/src/api/client.ts` uses `window.location.hostname:8000` for API calls — works from any browser on any network, since the hostname resolves to the server.

---

## CI/CD Pipeline

### GitHub Actions (`.github/workflows/docker-build.yml`)
- **Triggers:** push to `main`, tags `v*` / `*-V*`, PRs to `main`
- **Registry:** `ghcr.io` (GitHub Container Registry)
- **Image:** `ghcr.io/kronborgs/netboot-orchestrator`
- **Tags:** `latest` (on default branch), VERSION value, branch name, SHA

### Build Process
1. Checkout repo
2. Setup Docker Buildx
3. Login to GHCR (skipped on PRs)
4. Resolve build version safely:
    - Read `VERSION` if valid (`YYYY-MM-DD-VN`)
    - Fallback to `YYYY-MM-DD-V1` if missing/invalid
    - Always generate unique build version: `YYYY-MM-DD-V${GITHUB_RUN_NUMBER}`
5. Build all-in-one image from root `Dockerfile` with `BUILD_VERSION` build-arg
6. Push to GHCR with tags: source version + unique build version + sha + latest

### Version System
Format: `YYYY-MM-DD-VN` where N increments per build on the same day.

```
2026-02-16-V1  ← Previous day
2026-02-16-V3  ← Multiple builds same day
2026-02-18-V1  ← New day, reset to V1
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
- Overridden in CI at image build time with a unique per-build value (`BUILD_VERSION`)
- Read by FastAPI and exposed at `/api/v1/version`
- Displayed in WebUI footer
- Displayed in iPXE boot menu header

### Build Reliability Rule (Must Not Fail)
- Every CI build must produce a unique version tag and image version, even if `VERSION` is not manually bumped.
- CI now enforces this by generating `YYYY-MM-DD-V${GITHUB_RUN_NUMBER}` and injecting it into `/app/VERSION` during Docker build.
- Result: version collisions are avoided, and build/tag steps do not fail due to stale or invalid manual versioning.

---

## Running the Project

### Prerequisites
- Docker on Unraid (or any Linux host)
- Host network access (DHCP/TFTP needs raw network access)
- Primary DHCP server on the network (e.g., Unifi router)
- ISOs/installer files accessible on the host
- Optional: Unifi DHCP Option 66 (next-server) → host IP, Option 67 (boot-file) → `undionly.kpxe`

### Quick Start (Docker Compose)
```bash
docker-compose up -d
```

### Quick Start (Unraid)
1. Add container from `ghcr.io/kronborgs/netboot-orchestrator:latest`
2. Set Network Type to `host`
3. Enable Privileged mode
4. Add environment variables: `BOOT_SERVER_IP`, `DHCP_SUBNETS`
5. Add volume mounts:
   - Host path for data → `/data`
   - Host path for ISOs → `/isos` (read-only)
   - Host path for iSCSI images → `/iscsi-images`

### Verify
```bash
docker logs -f netboot-orchestrator      # Check startup sequence
curl http://HOST:8000/api/v1/boot/ipxe/menu   # Should return iPXE script
curl http://HOST:30000                    # Should return WebUI HTML
curl http://HOST:8000/api/v1/version      # Should return version string
```

### Access
- **WebUI:** `http://HOST:30000`
- **API Docs:** `http://HOST:8000/docs`
- **Boot Menu API:** `http://HOST:8000/api/v1/boot/ipxe/menu`

---

## Data & Persistence

### Volume Mounts

| Container Path | Purpose | Mode |
|----------------|---------|------|
| `/data` | JSON database, TFTP boot files, generated configs | rw |
| `/isos` | OS installer ISOs/IMGs | ro |
| `/iscsi-images` | iSCSI disk image files (sparse) | rw |

### JSON Database Files (under `/data/`)

| File | Contents |
|------|----------|
| `profiles.json` | Registered devices (MAC, name, boot config) |
| `images.json` | iSCSI image metadata (name, size, linked device) |
| `os.json` | OS installer metadata |
| `settings.json` | Application settings |
| `unknown_devices.json` | Auto-detected devices that booted but aren't registered |
| `boot_logs.json` | Boot event log (last 500 entries) |

### TFTP Files (under `/data/tftp/`)

| File | Purpose |
|------|---------|
| `undionly.kpxe` | Custom iPXE binary for BIOS (compiled with embedded script) |
| `ipxe.efi` | iPXE binary for UEFI boot |
| `undionly.ipxe` | Stage 2 chainload script |
| `boot.ipxe` | Backup boot script |
| `boot-menu.ipxe` | Cached copy of dynamic boot menu (regenerated every 5 min) |
| `raspi/` | Raspberry Pi boot files (prepared, not yet active) |

---

## Project Structure

```
netboot-orchestrator/
├── Dockerfile                        # All-in-one multi-stage Docker build
├── docker-compose.yml                # Single container, ghcr.io image
├── unraid-template.xml               # Unraid Community Applications template
├── VERSION                           # Current version (YYYY-MM-DD-VN)
├── version-bump.ps1 / .sh            # Version bump scripts
├── PROJECT_GUIDE.md                  # ← You are here
│
├── .github/workflows/
│   └── docker-build.yml              # CI/CD: build + push to ghcr.io
│
├── backend/                          # FastAPI REST API
│   ├── Dockerfile                    # Legacy standalone backend Dockerfile
│   ├── requirements.txt              # Python dependencies
│   └── app/
│       ├── __init__.py
│       ├── main.py                   # FastAPI app init, CORS, lifespan (iSCSI restore)
│       ├── database.py               # JSON file database (6 collections + boot logs)
│       ├── models.py                 # Pydantic models
│       └── api/
│           ├── boot.py               # iPXE menu + iSCSI + boot log endpoints
│           └── v1.py                 # REST API (devices, images, OS installers, storage)
│       └── services/
│           ├── file_service.py       # OS installer file operations
│           ├── device_service.py     # Device management
│           └── image_service.py      # IscsiService: tgtd + disk images + device links
│
├── frontend/                         # React + TypeScript + Vite
│   ├── Dockerfile                    # Legacy standalone frontend Dockerfile
│   ├── nginx.conf                    # Port 30000, SPA fallback, /api proxy
│   ├── package.json                  # npm dependencies
│   ├── vite.config.ts                # Vite build config
│   └── src/
│       ├── App.tsx                   # Main shell: Dashboard/Inventory/Setup pages
│       ├── main.tsx                  # React entry point
│       ├── types.ts                  # TypeScript types
│       ├── api/client.ts             # API client (hostname:8000)
│       ├── pages/
│       │   ├── Dashboard.tsx         # Stats cards + recent devices
│       │   ├── Inventory.tsx         # 5-tab inventory (Devices/iSCSI/OS/Logs/Wizard)
│       │   └── SetupGuide.tsx        # In-app docs
│       ├── components/
│       │   ├── DeviceList.tsx        # Device CRUD
│       │   ├── ImageManagement.tsx   # iSCSI image management (create/copy/link)
│       │   ├── OsInstallerList.tsx   # OS installer browser + upload
│       │   ├── UnknownDeviceWizard.tsx # Auto-register unknown devices
│       │   └── BootLogs.tsx          # Boot event log viewer
│       └── styles/index.css          # Dark theme CSS
│
├── netboot/
│   ├── entrypoint-backend.sh         # Runtime orchestrator (starts all services)
│   ├── Dockerfile.backend            # Legacy multi-service Dockerfile
│   └── tftp/scripts/embed.ipxe       # Boot script compiled into iPXE binary
│
├── data/                             # Persistent data (JSON DB, TFTP, boot scripts)
│   ├── *.json                        # Database files
│   ├── tftp/                         # TFTP-served boot files
│   └── iscsi/                        # iSCSI target config
│
└── docs/                             # Additional documentation
    ├── logo.png                      # Project logo (used in Unraid template)
    ├── BOOT_FLOW.md
    ├── DATA_STRUCTURE.md
    ├── DEPLOYMENT.md
    ├── QUICKSTART.md
    └── UNRAID.md
```

---

## Issues Fixed (Full History)

| Version | Issue | Fix |
|---------|-------|-----|
| V3 | Unraid adds trailing spaces to env var names | `_env()` helper checks both exact and space-suffixed names |
| V3 | nginx showed "Welcome to nginx!" instead of React app | Frontend goes to `/usr/share/nginx/html`, install as `netboot` site, remove default |
| V3 | sanboot HTTP 4xx Client Error on ISOs | Added HEAD endpoint with `Accept-Ranges` + Range request (206) support |
| V3 | ISO boot "Exec format error" | Switched from `chain` to `sanboot --no-describe` for .iso/.img files |
| V3 | Unicode smart quotes in filenames mangled iPXE URLs | URL-encode paths with `urllib.parse.quote()`, `_ascii_safe()` for display |
| V2 | iPXE menu showed garbled Unicode box-drawing | Replaced all Unicode with ASCII-only characters |
| V2 | Various WebUI bugs and missing features | Added iSCSI management, boot logs, device wizard, branding |
| V1 | WebUI broken — corrupted source code | Fixed App.tsx corrupted line |
| V1 | WebUI port wrong — nginx on 3000 | Changed to listen 30000 |
| V1 | nginx proxy used Docker DNS | Changed to `127.0.0.1:8000` |
| V1 | ImageManagement used hardcoded `localhost:8000` | Changed to `apiFetch()` |
| V1 | Boot menu auto-selected before user could choose | Removed timeout from `choose` |
| V1 | Stock undionly.kpxe → infinite iPXE loop | Multi-stage Docker build compiles custom iPXE |
| V1 | dnsmasq + Unifi DHCP conflict | Switched to proxy DHCP mode |
| V1 | No iPXE client detection | Added option 175 + userclass detection |
| V1 | TFTP unreliable across VLANs | Switched to HTTP chainload |
| V1 | iPXE menu rendering broken | Rewrote with proper `menu`/`item`/`choose` |
| V1 | Volume mount shadows Dockerfile files | Entrypoint creates everything at runtime |

---

## Developer Notes & Gotchas

- **Proxy DHCP is critical** — dnsmasq must NEVER assign IPs. The primary router handles that. `dhcp-range=SUBNET,proxy` is the correct format.
- **Volume mount shadowing** — `./data:/data` hides anything the Dockerfile put there. The entrypoint must create/copy all boot files at runtime.
- **Custom iPXE build** — the multi-stage Docker build compiles iPXE from source with `embed.ipxe`. Takes ~2 min on first build, cached after. If the embedded script breaks, devices won't boot.
- **`${next-server}` in embed.ipxe** — this iPXE variable comes from DHCP (Option 66 or dnsmasq proxy). The embedded script uses it to chain to the HTTP API. Don't hardcode an IP in embed.ipxe.
- **Host network + privileged mode** — required because dnsmasq needs raw DHCP access, TFTP needs UDP port 69, tgtd needs iSCSI port 3260. No port mapping, everything binds directly.
- **Always use `_env()`** — never use `os.getenv()` directly for environment variables due to the Unraid trailing-space bug.
- **sanboot for ISOs, chain for scripts** — `.iso` and `.img` files must use `sanboot --no-describe`. `.efi`, `.ipxe`, and kernel files use `chain`.
- **Range requests are required** — iPXE's `sanboot` over HTTP sends HEAD then Range requests. Without 206 support, it fails with "HTTP 4xx Client Error".
- **iPXE is ASCII-only** — all text displayed in iPXE menus must be pure ASCII. Use `_ascii_safe()` for display names. Use `urllib.parse.quote()` for URLs.
- **iSCSI sparse files** — `truncate -s SIZE` creates sparse files that only consume disk space as data is written. A "64GB" image starts at 0 bytes disk usage.
- **iSCSI restore on startup** — `IscsiService.restore_targets()` runs on FastAPI lifespan startup. It re-registers all known images with tgtd. If tgtd isn't ready yet, this will fail silently.
- **Boot menu cache** — the entrypoint saves a static copy of the boot menu to `/data/tftp/boot-menu.ipxe` and refreshes it every 5 minutes. This is a fallback; live clients always get the dynamic menu from FastAPI.
- **nginx site config** — uses Ubuntu's `sites-available/sites-enabled` pattern. The default site must be removed or it will serve "Welcome to nginx!" instead of the React app. Config is installed as `/etc/nginx/sites-available/netboot`.
- **Supported boot file types** — `.iso`, `.img`, `.bin`, `.efi`, `.exe`, `.vhd`, `.vhdx`, `.qcow2`, `.vmdk`, `.raw`, `.wim`
- **Raspberry Pi prep** — TFTP directories and README are created but Pi boot is not yet functional. Needs further work for Pi 4/5 UEFI/netboot.

---

## Potential Future Work

- [ ] Raspberry Pi 4/5 network boot (UEFI → iPXE → menu)
- [ ] Per-device boot profiles (assign specific OS/action per MAC)
- [ ] WinPE integration for Windows deployment (unattend.xml, driver injection)
- [ ] Linux preseed/kickstart/autoinstall for automated installs
- [ ] Multi-architecture iPXE builds (ipxe.efi compiled from source like undionly.kpxe)
- [ ] WebSocket-based live boot log streaming
- [ ] Image templates (pre-built OS images for quick deployment)
- [ ] HTTPS/TLS for boot traffic (iPXE supports HTTPS with compiled-in certs)
- [ ] Authentication for WebUI and API
- [ ] Backup/restore of iSCSI images and configuration
