# 🚀 RPi Netboot Orchestrator

> **Netboot Without SD Cards for Raspberry Pi, x86 & x64**
>
> Production-ready web orchestrator for SD-card-less network boot, disk image management, and automatic device provisioning

[![GitHub Release](https://img.shields.io/badge/Release-2026--02--14--V1-blue?style=flat-square)](https://github.com/Kronborgs/netboot-orchestrator/releases)
[![Docker](https://img.shields.io/badge/Docker%20Compose-Ready-2496ED?style=flat-square&logo=docker)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18%2B-61DAFB?style=flat-square&logo=react)](https://react.dev/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

**RPi Netboot Orchestrator** enables you to boot Raspberry Pi, x86, and x64 systems entirely from the network without SD cards or local storage. Perfect for **labs**, **schools**, **datacenters**, and **embedded deployments** where you need centralized control over boot, storage, and OS installations.

## ✨ Key Features

### 🎯 Core Capabilities
- **Multi-Platform Support**: Raspberry Pi, x86, x64 (easily extensible)
- **Web Dashboard**: Modern React UI for managing devices and disk images
- **iSCSI Disk Targets**: Dynamically create and assign persistent storage to devices
- **PXE Network Boot**: Full x86/x64 support via iPXE bootloader
- **Smart Device Wizard**: Auto-register unknown devices on first boot
- **RESTful API**: Complete API for automation and third-party integration
- **Docker Native**: Production-ready containerized deployment

### 📊 Management Features
- Per-MAC device profiles with status tracking
- Image assignment, versioning, and lifecycle management
- Multi-kernel set support for different boot configurations
- OS installer catalogs and boot menu generation
- Device boot flow monitoring and logging

### 🔧 Technical Stack
| Component | Technology |
|-----------|-----------|
| **Backend** | FastAPI (Python 3.11) |
| **Frontend** | React 18, TypeScript, Vite |
| **Boot Services** | TFTP (dnsmasq), HTTP (nginx), iSCSI (TGT) |
| **Container Orchestration** | Docker Compose |
| **Database** | JSON (easily migrate to PostgreSQL) |

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- Docker & Docker Compose
- 4GB RAM minimum
- 50GB free storage

### Installation

```bash
# 1. Clone repository
git clone https://github.com/Kronborgs/netboot-orchestrator.git
cd netboot-orchestrator

# 2. Run setup (creates /data directories and .env)
bash setup.sh                    # Linux/Mac
.\setup.ps1                      # Windows (PowerShell)

# 3. Start all services
docker-compose up -d

# 4. Verify services are running
docker-compose ps
```

### Access the Console

| Interface | URL | Purpose |
|-----------|-----|---------|
| **Web Dashboard** | http://localhost:30000 | Device & image management |
| **API Documentation** | http://localhost:8000/docs | Interactive API explorer |
| **API Health** | http://localhost:8000/health | Service status check |

## 🏗️ Architecture

### Service Topology

```
┌─────────────────────────────────────────────────────┐
│           Network Boot Clients                      │
│     (Raspberry Pi, x86, x64 devices)               │
└────────────────────┬────────────────────────────────┘
                     │ PXE/Network Boot
     ┌───────────────┼────────────────────┬──────────┐
     │               │                    │          │
     ▼               ▼                    ▼          ▼
  TFTP         HTTP Server          iSCSI Target   ...
(Port 69)   (Port 8080)            (Port 3260)
     │               │                    │
     └───────────────┼────────────────────┘
                     │
        ┌────────────▼─────────────┐
        │    FastAPI Backend       │
        │    (Port 8000)           │
        │  ✅ Device CRUD          │
        │  ✅ Image Management     │
        │  ✅ Boot Logic           │
        │  ✅ Config Generation    │
        └────────────┬─────────────┘
                     │
        ┌────────────▼─────────────┐
        │  React Web Dashboard     │
        │  (Port 30000)            │
        │  ✅ Device List          │
        │  ✅ Image Management     │
        │  ✅ Boot Configuration   │
        └──────────────────────────┘
```

### Data Flow

1. **Device Powers On** → Sends PXE request to TFTP
2. **TFTP Server** → Returns bootloader (bootcode.bin for RPi, ipxe.efi for x86)
3. **Bootloader** → Downloads kernel via HTTP
4. **API Check-in** → Device queries `/api/v1/boot/check-in` to determine action
5. **iSCSI Boot** → If image assigned, mounts persistent storage block device
6. **Full OS** → System boots with assigned disk image or runs default

## 📚 Documentation

| Document | Content |
|----------|---------|
| **[🎬 QUICKSTART.md](docs/QUICKSTART.md)** | 5-minute getting started guide |
| **[🔄 BOOT_FLOW.md](docs/BOOT_FLOW.md)** | Detailed boot process and data flow |
| **[💾 DATA_STRUCTURE.md](docs/DATA_STRUCTURE.md)** | Data models, JSON schema, storage |
| **[🚢 DEPLOYMENT.md](docs/DEPLOYMENT.md)** | Production setup, HA, monitoring, security |
| **[🐧 UNRAID.md](docs/UNRAID.md)** | Unraid server integration guide |

## 💻 API Quick Reference

### REST Endpoints

**Devices**
```bash
GET  /api/v1/devices              # List all devices
POST /api/v1/devices              # Register new device
GET  /api/v1/devices/{mac}        # Get device details
PUT  /api/v1/devices/{mac}        # Update device
DELETE /api/v1/devices/{mac}      # Delete device
```

**Images**
```bash
GET  /api/v1/images               # List all images
POST /api/v1/images               # Create new image
PUT  /api/v1/images/{id}/assign   # Assign image to device
PUT  /api/v1/images/{id}/unassign # Unassign image
```

**Boot (Public API)**
```bash
GET /api/v1/boot/check-in?mac=X&device_type=Y  # Device boot check-in
```

**Configuration**
```bash
GET  /api/v1/kernel-sets          # List available kernel sets
POST /api/v1/kernel-sets          # Create new kernel set
GET  /api/v1/os-installers        # List OS installers
POST /api/v1/os-installers        # Register OS installer
```

**System**
```bash
GET /health                        # API health check
GET /docs                          # Swagger UI documentation
```

### Example: Register Device and Assign Image

```bash
# Step 1: Create device
curl -X POST http://localhost:8000/api/v1/devices \
  -H 'Content-Type: application/json' \
  -d '{
    "mac": "aa:bb:cc:dd:ee:ff",
    "device_type": "raspi",
    "name": "lab-pi-01",
    "enabled": true
  }'

# Step 2: Create disk image
curl -X POST http://localhost:8000/api/v1/images \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "raspi-prod-01",
    "name": "Raspberry Pi Production",
    "size_gb": 64,
    "device_type": "raspi"
  }'

# Step 3: Assign image to device
curl -X PUT "http://localhost:8000/api/v1/images/raspi-prod-01/assign?mac=aa:bb:cc:dd:ee:ff"

# Step 4: Verify
curl http://localhost:8000/api/v1/devices/aa:bb:cc:dd:ee:ff | jq
```

## 🖥️ Web Dashboard

### Dashboard Tab
- ✅ Active device count
- ✅ Total images managed
- ✅ Available OS installers
- ✅ Device list with status

### Inventory Tab
- **Images**: Create, list, manage disk images
- **OS Installers**: Configuration and version management
- **Device Wizard**: Auto-register new devices

### Device Management
- Register devices (MAC-based)
- Assign images to devices
- Select kernel sets
- Enable/disable devices

## � Project Structure

```
netboot-orchestrator/
├── backend/                           # FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI application
│   │   ├── models.py                 # Pydantic data models
│   │   ├── database.py               # JSON persistence layer
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── v1.py                 # Device/Image/Kernel endpoints
│   │   │   └── boot.py               # Boot check-in endpoint
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── device_service.py     # Device management logic
│   │       └── image_service.py      # Image management logic
│   ├── Dockerfile
│   ├── requirements.txt
│   └── run.sh
│
├── frontend/                          # React + Vite frontend
│   ├── src/
│   │   ├── components/               # React components
│   │   │   ├── DeviceList.tsx
│   │   │   ├── ImageManagement.tsx
│   │   │   ├── OsInstallerList.tsx
│   │   │   └── UnknownDeviceWizard.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   └── Inventory.tsx
│   │   ├── styles/
│   │   │   └── index.css
│   │   ├── api.ts                    # Axios API client
│   │   ├── types.ts                  # TypeScript interfaces
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   └── index.html
│
├── netboot/                           # Boot service containers
│   ├── tftp/                          # TFTP server
│   │   ├── Dockerfile
│   │   ├── config/
│   │   │   └── dnsmasq.conf
│   │   └── entrypoint.sh
│   ├── http/                          # HTTP server
│   │   ├── Dockerfile
│   │   ├── conf/
│   │   │   └── nginx.conf
│   │   └── entrypoint.sh
│   └── iscsi/                         # iSCSI target
│       ├── Dockerfile
│       ├── entrypoint.sh
│       └── init_iscsi.sh
│
├── docs/                              # Documentation
│   ├── QUICKSTART.md
│   ├── BOOT_FLOW.md
│   ├── DATA_STRUCTURE.md
│   ├── DEPLOYMENT.md
│   └── UNRAID.md
│
├── docker-compose.yml                 # Docker Compose orchestration
├── .env.example                       # Environment variables template
├── .gitignore
├── CHANGELOG.md
├── setup.sh                           # Linux/Mac setup script
├── setup.ps1                          # Windows setup script
└── README.md                          # This file
```

## 🔧 Configuration

### Environment Variables

Create `.env` from template:

```bash
cp .env.example .env
# Edit .env with your settings
```

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | FastAPI bind address |
| `API_PORT` | `8000` | FastAPI port |
| `DATA_PATH` | `/data` | Persistent data directory |
| `VITE_API_URL` | `http://localhost:8000` | Frontend API endpoint |
| `LOG_LEVEL` | `INFO` | Python logging level |

### Data Directory Structure

```
/data/
├── http/                              # HTTP-served files
│   ├── raspi/kernels/default/         # Default RPi kernel
│   ├── raspi/kernels/test/            # Alternative kernel
│   ├── raspi/aa:bb:cc:dd:ee:ff/       # Per-MAC kernel
│   ├── os/                            # OS installer files
│   └── ipxe/                          # iPXE boot scripts
├── tftp/                              # TFTP-served files
│   ├── raspi/                         # RPi bootloaders
│   └── pxe/                           # x86 bootloaders
├── iscsi/                             # iSCSI storage
│   └── images/                        # Disk image files
├── profiles.json                      # Device registry
├── images.json                        # Image inventory
├── os.json                            # OS installer metadata
└── settings.json                      # Global configuration
```

## 🧪 Development

### Backend Development

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate              # Linux/Mac
# or: .\venv\Scripts\activate          # Windows

# Install dependencies
pip install -r requirements.txt

# Run development server
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start development server (http://localhost:30000)
npm run dev

# Build for production
npm run build
```

### Testing Services Locally

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f api
docker-compose logs -f tftp
docker-compose logs -f http-server

# Stop services
docker-compose down

# Full reset (WARNING: deletes data)
docker-compose down -v
rm -rf data/
```

## 🤝 Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Workflow

- Each PR must include proper testing
- Document your changes in commit messages
- Update README/docs if needed
- Use semantic commit messages

## 🐛 Troubleshooting

### Services Won't Start

```bash
# Check Docker daemon
docker ps

# View service logs
docker-compose logs api
docker-compose logs tftp
docker-compose logs http-server
docker-compose logs iscsi-target

# Rebuild containers
docker-compose build --no-cache
```

### Network Boot Issues

- ✅ Verify network connectivity
- ✅ Check TFTP port 69 is accessible
- ✅ Ensure HTTP server responds on port 8080
- ✅ Verify iSCSI port 3260 is open
- ✅ Check device is on same network

### Permission Issues

```bash
# Fix data directory permissions
sudo chown -R 1000:1000 ./data
```

### Slow Boot

- Check network bandwidth utilization
- Verify HTTP server performance
- Monitor iSCSI target latency
- Review kernel/initramfs sizes

## 📊 Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Boot Time | < 60s | From PXE to OS loaded |
| Device Capacity | 100+ | Per orchestrator instance |
| Image Transfer | 100MB/s | 1Gbps network |
| API Response | < 100ms | Average response time |

## 🔐 Security Considerations

- Boot check-in endpoint is public (by design for unknown devices)
- Run on isolated network or behind VPN in production
- Use SSL/TLS for HTTPS (guides in DEPLOYMENT.md)
- Implement access control on Dashboard
- Regularly backup `/data` directory

## 📄 License

This project is licensed under the **MIT License** - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Raspberry Pi Foundation** - For amazing SBC platform
- **iPXE Project** - For flexible network boot
- **dnsmasq** - For TFTP and DHCP
- **nginx** - For reliable HTTP serving
- **TGT (SCSI Target Utils)** - For iSCSI target management
- **FastAPI** - For excellent Python web framework
- **React** - For modern UI framework

## 📞 Support & Community

**Report Issues**: [GitHub Issues](https://github.com/Kronborgs/netboot-orchestrator/issues)

**Documentation**: Check [docs/](docs/) directory for detailed guides

**Questions**: Open a GitHub Discussion

## 🗺️ Roadmap

### v2.0 (Planned)
- [ ] Persistent user authentication
- [ ] Advanced image templating & cloning
- [ ] Prometheus metrics & Grafana integration
- [ ] Kubernetes deployment manifests
- [ ] Cloud provider integration (AWS, Azure, GCP)

### v3.0 (Future)
- [ ] Web-based BIOS/firmware management
- [ ] Advanced scheduling & auto-provisioning
- [ ] Machine learning-based optimization
- [ ] Multi-tenant support

---

## ⭐ Show Your Support

If you find this project useful, please consider giving it a star! It helps others discover the project.

```
 _______________
< Happy Netbooting! 🚀 >
 ¯¯¯¯¯¯¯¯¯¯¯¯¯
```

---

**Repository**: [Kronborgs/netboot-orchestrator](https://github.com/Kronborgs/netboot-orchestrator)

**Version**: 2026-02-14-V1

**Last Updated**: February 14, 2026
