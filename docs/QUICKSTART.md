# Quick Start Guide

Get the RPi Netboot Orchestrator up and running in 5 minutes!

## Prerequisites

- Docker and Docker Compose installed
- 4GB free disk space
- Network connectivity

## Step 1: Clone and Setup

```bash
git clone https://github.com/Kronborgs/netboot-orchestrator.git
cd netboot-orchestrator

# Linux/Mac
bash setup.sh

# Windows PowerShell
.\setup.ps1
```

## Step 2: Start Services

```bash
docker-compose up -d

# Wait for services to start (30-60 seconds)
docker-compose ps
```

## Step 3: Access the Web UI

Open your browser and navigate to:
- **Web UI**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Step 4: Register Your First Device

### Via Web UI
1. Go to Inventory > Device Wizard
2. Enter device MAC address
3. Select device type (Raspberry Pi, x86, x64)
4. Click Register

### Via API
```bash
curl -X POST http://localhost:8000/api/v1/devices \
  -H 'Content-Type: application/json' \
  -d '{
    "mac": "aa:bb:cc:dd:ee:ff",
    "device_type": "raspi",
    "name": "my-device",
    "enabled": true
  }'
```

## Step 5: Create an Image

### Via Web UI
1. Go to Inventory > Images
2. Click "Create Image"
3. Enter image details (name, size, device type)
4. Click Create

### Via API
```bash
curl -X POST http://localhost:8000/api/v1/images \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "my-image-01",
    "name": "My Disk Image",
    "size_gb": 32,
    "device_type": "raspi"
  }'
```

## Step 6: Assign Image to Device

```bash
curl -X PUT http://localhost:8000/api/v1/images/my-image-01/assign?mac=aa:bb:cc:dd:ee:ff
```

## Checking Status

### List all devices
```bash
curl http://localhost:8000/api/v1/devices
```

### List all images
```bash
curl http://localhost:8000/api/v1/images
```

### Check boot status
```bash
curl "http://localhost:8000/api/v1/boot/check-in?mac=aa:bb:cc:dd:ee:ff&device_type=raspi"
```

## Common Tasks

### View Logs
```bash
# API logs
docker-compose logs api -f

# All services
docker-compose logs -f
```

### Stop Services
```bash
docker-compose down
```

### Restart a Service
```bash
docker-compose restart api
```

### Reset Everything
```bash
# WARNING: This deletes all data
docker-compose down -v
rm -rf data/
docker-compose up -d
```

## Network Boot on Raspberry Pi

1. Power on Pi with network cable connected
2. Pi will attempt PXE boot
3. Unknown devices show boot menu
4. Follow on-screen prompts to register

## Troubleshooting

### Can't Access Web UI
```bash
# Check if container is running
docker-compose ps

# Check API logs
docker-compose logs api
```

### Devices Not Showing
```bash
# Verify data directory
ls -la data/

# Check API health
curl http://localhost:8000/health
```

### TFTP Issues
```bash
# Check TFTP logs
docker-compose logs tftp

# Verify port availability
netstat -an | grep 69
```

## Next Steps

- Read [DEPLOYMENT.md](DEPLOYMENT.md) for production setup
- Check [BOOT_FLOW.md](BOOT_FLOW.md) for detailed boot process
- Review API documentation at http://localhost:8000/docs

## Need Help?

Check the main [README.md](../README.md) for more information and troubleshooting tips.
