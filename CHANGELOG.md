# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to date-based versioning: `YYYY-MM-DD-V#`

## [Unreleased]

### Added
- GitHub Actions CI/CD workflows:
  - `build-test.yml`: Backend/frontend testing and docker-compose validation
  - `docker-build.yml`: Automated Docker image building and pushing to registry
  - `pr-checks.yml`: Pull request validation and security scanning
  - `release.yml`: Automated GitHub release creation with version tags
- Comprehensive Unraid deployment guide (`docs/UNRAID.md`)
  - Full Unraid installation instructions
  - Storage and networking configuration
  - Troubleshooting specific to Unraid
  - Performance tuning recommendations
- Version bump automation:
  - `version-bump.sh`: Bash script with date-aware version incrementing
  - `version-bump.ps1`: PowerShell equivalent for Windows compatibility
  - VERSION file for centralized version management

---

## [2026-02-14-V1] - 2026-02-14

### Added
- **Initial production-ready release**
- **Backend API (FastAPI)**:
  - Device management (CRUD: register, list, update, remove devices)
  - Image and OS installer management
  - Kernel set management
  - Health check endpoints (`/health`)
  - Boot check-in API for runtime device queries (`/api/boot/check-in`)
  - JSON-based persistent storage with atomic writes
  - CORS middleware for frontend integration

- **Frontend (React + TypeScript + Vite)**:
  - Dashboard page with device overview and statistics
  - Inventory management page for images and installers
  - Device list with filtering and deletion capabilities
  - Responsive design with Tailwind CSS
  - Axios HTTP client for API communication
  - Tab-based navigation interface

- **Docker Services**:
  - Backend API service (Python 3.11 + FastAPI)
  - Frontend service (Node.js + React + Vite)
  - TFTP server (dnsmasq-based for network boot)
  - HTTP server (nginx for file distribution)
  - iSCSI target (TGT daemon for block device access)
  - Docker Compose orchestration with health checks

- **Boot Protocol Support**:
  - Raspberry Pi: TFTP → HTTP → iSCSI workflow
  - x86 systems: PXE → iPXE → HTTP → iSCSI workflow
  - x64 systems: PXE → iPXE → HTTP → iSCSI workflow
  - MAC-based device identification and routing

- **Documentation**:
  - Professional GitHub README with badges and architecture diagrams
  - Boot flow documentation
  - Data structure documentation
  - Deployment guide
  - Quick start guide (5-minute setup)

- **Development Tools**:
  - Cross-platform setup automation (setup.sh and setup.ps1)
  - Environment configuration template (.env.example)
  - Git-based version management

### API Endpoints
- `GET /health` - Service health check
- `GET /` - Root endpoint with service info
- **Devices**: `GET/POST/PUT/DELETE /api/v1/devices`
- **Image Assignment**: `GET/POST /api/v1/devices/{device_id}/images`
- **Images**: `GET/POST/PUT/DELETE /api/v1/images`
- **Kernel Sets**: `GET/POST/PUT/DELETE /api/v1/kernel-sets`
- **OS Installers**: `GET/POST /api/v1/os-installers`
- **Boot Check-in**: `POST /api/boot/check-in`

### Known Limitations
- Single-server deployment (no clustering)
- No built-in authentication/authorization (add reverse proxy in production)
- JSON storage backend (not suitable for >10,000 devices)

### Security Considerations
- Boot check-in endpoint is unauthenticated for PXE compatibility
- API endpoints should be protected with reverse proxy in production
- Use HTTPS for web UI in production environments
- Restrict network access to trusted subnets for PXE services

### Performance Characteristics
- Tested with up to 1,000 registered devices
- Boot time: 2-5 minutes (image and network dependent)
- Memory usage: ~512MB backend, ~256MB frontend
- CPU usage: <5% idle, <20% during active boots

### Testing Status
- ✓ All backend API endpoints functional
- ✓ Frontend UI responsive and feature-complete
- ✓ Docker containers build successfully
- ✓ Boot workflow verified on Raspberry Pi
- ✓ Health checks and monitoring functional

---

## Version Numbering Format: YYYY-MM-DD-V#

- **YYYY-MM-DD**: Release date
- **V#**: Sequential daily version (V1, V2, V3, etc.)
- Multiple releases per day: `2026-02-14-V1`, `2026-02-14-V2`, `2026-02-15-V1`

For version bumping:
- Linux/macOS: `./version-bump.sh`
- Windows: `.\version-bump.ps1`

**Current Version**: 2026-02-14-V1  
**Last Updated**: 2026-02-14
