# Netboot Orchestrator - Project Guide

**Version:** 2026-02-25-V208  
**Status:** Operational (PXE + iSCSI + WebUI + CI/CD)  
**Repository:** `Kronborgs/netboot-orchestrator`

## Purpose of this document
This guide is the technical handoff and engineering reference.
All deep technical content that used to live in `README.md` is consolidated here.

## 1. Current architecture
Single all-in-one container with these core services:
- `dnsmasq` for PXE/DHCP logic
- `FastAPI` backend for APIs and iPXE scripts
- `tgtd` for iSCSI targets
- `nginx` for frontend static serving
- `supervisord` as process manager

Primary stack:
- Backend: Python + FastAPI
- Frontend: React + TypeScript + Vite
- Persistence: JSON files under `/data`
- Delivery: Docker image via GitHub Actions to GHCR

## 2. Runtime and data flow
1. Client PXE boots and receives iPXE binary/script
2. iPXE chains to backend menu endpoints
3. Device can boot installer media or iSCSI target
4. Backend stores device state, transfer counters, and logs in JSON
5. WebUI reads backend APIs for inventory, metrics, and logs

## 3. Versioning and release truth (important)
Current source-of-truth behavior:
- Runtime version is read from `VERSION`
- Frontend fallback version is in `frontend/src/App.tsx`
- `README.md` and this guide carry matching displayed version

Critical correction already implemented:
- CI must **not** overwrite `/app/VERSION` with build-run-number values
- This fixed prior runtime/version mismatch incidents

Release practice in this repo:
1. Implement code/docs changes
2. Bump version references in:
   - `VERSION`
   - `frontend/src/App.tsx`
   - `README.md`
   - `PROJECT_GUIDE.md`
3. Commit and push to `main`
4. Deploy `ghcr.io/kronborgs/netboot-orchestrator:latest`

## 4. Recent technical changes (V205–V207)
### V205
- Deterministic owner attribution for shared remote IP scenarios
- Stale metrics hidden on non-owner MACs

### V206
- Recent-transfer gate tightened: requires real request activity, not just reset state
- Added fallback disk metric from per-image allocated bytes when socket bytes are unavailable
- Observed progress now accepts one-sided signals (`disk_write_only` / `network_tx_only`)

### V207
- Added debug endpoint for per-MAC source attribution in realtime:
  - `GET /api/v1/boot/devices/metrics/debug`
  - `GET /api/v1/boot/devices/metrics/debug?include_full=true`
- Exposes source fields and confidence to validate fallback decisions during live tests

## 5. Metrics and attribution model
Main endpoint:
- `GET /api/v1/boot/devices/{mac}/metrics`

Important fields:
- `connection`: active/session_count/remote_ips/source
- `network`: rx_bytes/tx_bytes/source
- `disk_io`: read_bytes/write_bytes/source
- `install_progress`: observed_source/observed_total_bytes/attribution_confidence/stall state
- `warning`: attribution and fallback warnings for operator visibility

Fallback strategy (high-level):
1. Use direct iSCSI metrics when available
2. If unavailable, try attributed socket counters where confidence allows
3. For active sessions, use per-image allocated bytes fallback for write-progress
4. Suppress/hide stale or ambiguous data to avoid MAC cross-contamination

## 6. API reference (technical summary)
### Boot and telemetry
- `GET /api/v1/boot/ipxe/menu`
- `GET /api/v1/boot/check-in`
- `GET|POST /api/v1/boot/log`
- `GET /api/v1/boot/logs`
- `GET /api/v1/boot/devices/{mac}/metrics`
- `POST /api/v1/boot/devices/{mac}/transfer/reset`
- `GET /api/v1/boot/devices/metrics/debug`

### WinPE support
- `GET /api/v1/boot/winpe/startnet.cmd`
- `GET /api/v1/boot/winpe/winpeshl.ini`
- `PUT|POST /api/v1/boot/winpe/logs/upload`
- `GET /api/v1/boot/winpe/logs`
- `GET /api/v1/boot/winpe/logs/download`

### iSCSI management
- `GET /api/v1/boot/iscsi/images`
- `POST /api/v1/boot/iscsi/images`
- `DELETE /api/v1/boot/iscsi/images/{name}`
- `POST /api/v1/boot/iscsi/images/{name}/copy`
- `POST /api/v1/boot/iscsi/images/{name}/rename`
- `POST /api/v1/boot/iscsi/images/{name}/link`
- `POST /api/v1/boot/iscsi/images/{name}/unlink`

### Core REST
- `GET /api/v1/version`
- Device, OS installer, profile, and settings endpoints under `/api/v1/...`

## 7. Environment variables (operational)
Required/commonly used:
- `BOOT_SERVER_IP`
- `DHCP_SUBNETS`
- `DHCP_RANGE_START`
- `DHCP_RANGE_END`
- `IMAGES_PATH`
- `OS_INSTALLERS_PATH`
- `WINPE_LOGS_PATH`

Metrics/stall tuning:
- `INSTALL_STALL_THRESHOLD_SECONDS`
- `METRICS_RECENT_TRANSFER_SECONDS`
- `METRICS_IP_OWNER_WINDOW_SECONDS`
- `INSTALL_PROGRESS_LOG_INTERVAL_SECONDS`
- `WINPE_LOG_MISSING_THRESHOLD_SECONDS`

## 8. Key files (engineering map)
- `backend/app/api/boot.py` - iPXE scripts, metrics, logs, WinPE, debug telemetry endpoint
- `backend/app/api/v1.py` - core REST endpoints and transfer attribution path
- `backend/app/database.py` - JSON persistence and transfer/session fields
- `backend/app/services/image_service.py` - iSCSI image operations and metrics collection
- `frontend/src/components/DeviceList.tsx` - device panel, logs, metrics UI
- `frontend/src/App.tsx` - shell and version fallback
- `frontend/nginx.conf` - cache policy for SPA entry handling
- `.github/workflows/docker-build.yml` - build/push pipeline
- `Dockerfile` - image build and runtime setup

## 9. Technical content migrated from README
The following technical topics are intentionally kept in this guide (not the user-facing README):
- Architecture internals and service composition
- Endpoint inventory and telemetry model
- Versioning/release internals and CI behavior
- Environment variable matrix and tuning knobs
- File-level engineering map and ownership hints

## 10. Known constraints and gotchas
- iPXE display is ASCII sensitive; sanitize dynamic display strings
- Shared remote IP scenarios can still reduce attribution confidence
- Fallback metrics are best-effort and intentionally conservative under ambiguity

## 11. Validation checklist after each telemetry change
1. Verify `/api/v1/version` returns expected release version
2. Run one-device Windows install and confirm metrics remain populated
3. Run multi-device scenario and verify no cross-device remote IP leakage
4. Use `/api/v1/boot/devices/metrics/debug` to confirm source transitions
5. Confirm WebUI logs panel and metrics match backend debug output

## 12. Screenshot asset plan for docs
Asset directory recommendation: `docs/screenshots/`

Suggested files:
- `bootmenu-main.png`
- `bootmenu-windows-install.png`
- `webgui-dashboard-overview.png`
- `webgui-inventory-devices.png`
- `webgui-image-management.png`
- `webgui-device-logs-realtime.png`
- `webgui-connection-metrics.png`

README placement guidance is maintained in `README.md`.
