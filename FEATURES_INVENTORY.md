# Inventory Management Features

Complete inventory management system for Netboot Orchestrator with image management, OS installer management, and device registration wizard.

## 🎯 Feature Overview

### 1. **Image Management** 💿
Manage iSCSI disk images and assign them to devices for network booting.

#### Features:
- **Create iSCSI Images**: Create new disk images with custom sizes and device type restrictions
- **View Image Details**: See image name, size (GB), device type compatibility, and assignment status
- **Assign to Devices**: Quickly assign images to specific devices by MAC address
- **Unassign Images**: Remove image assignments from devices
- **Delete Images**: Remove unused images from the system
- **Image Inventory**: View all available images with their current assignments

#### API Endpoints:
```
GET    /api/v1/images                    - List all images
POST   /api/v1/images                    - Create new image
GET    /api/v1/images/{image_id}         - Get image details
PUT    /api/v1/images/{image_id}         - Update image
DELETE /api/v1/images/{image_id}         - Delete image
PUT    /api/v1/images/{image_id}/assign  - Assign to device (MAC)
PUT    /api/v1/images/{image_id}/unassign - Unassign from device
```

#### UI Components:
- **Image List**: Shows all iSCSI images with their properties
- **Create Form**: Step-by-step form to create new images
- **Assignment Modal**: Easy device selection and assignment
- **Status Badges**: Visual indicators for assigned/unassigned images

---

### 2. **OS Installers Management** 🖱️
Upload, manage, and organize operating system installer files for PXE boot and cloud installations.

#### Features:
- **Upload Files**: Drag-and-drop or browse file upload for OS installers
- **Progress Tracking**: Real-time progress bar during file uploads
- **File Listing**: View all uploaded OS installer files with details
- **File Information**: See file size, creation date, and modification time
- **Delete Files**: Remove OS installer files when no longer needed
- **Storage Dashboard**: View total storage usage across all components
  - OS Installers total size
  - iSCSI Images total size
  - Combined system storage usage

#### API Endpoints:
```
GET    /api/v1/os-installers/files                 - List OS installer files
POST   /api/v1/os-installers/upload                - Upload OS installer file
GET    /api/v1/os-installers/files/{file_path}    - Get file details
DELETE /api/v1/os-installers/files/{file_path}    - Delete file
POST   /api/v1/images/upload                       - Upload iSCSI image file
GET    /api/v1/storage/info                        - Get storage usage info
```

#### UI Features:
- **Upload Area**: Large drag-and-drop zone with file browse button
- **File Table**: Organized view of all OS installer files
- **Storage Cards**: Dashboard showing storage usage by category
- **Upload Progress**: Visual progress bar with percentage indicator
- **File Management**: Quick delete buttons for each file

---

### 3. **Unknown Device Wizard** 🧙
Interactive setup wizard for registering new devices detected during boot.

#### Features:
- **Device Detection**: Automatically track devices that boot but aren't registered
- **Multi-Step Wizard**: 
  1. **Select Device Type** - Choose between Raspberry Pi, x86, or x64
  2. **Choose Installation Target** - Select iSCSI image or local disk installation
  3. **Select Image/OS** - Pick the appropriate image or OS installer for the device

- **Smart Filtering**: 
  - Images filtered by device type (show only compatible images)
  - OS installers available for local disk installation
  
- **Device Registration**: One-click registration with automatic assignment
- **Unknown Device List**: View all devices waiting for registration
- **Boot-time Detection**: Devices are automatically recorded when they attempt to boot

#### API Endpoints:
```
GET    /api/v1/unknown-devices                - List unknown devices
POST   /api/v1/unknown-devices/register       - Register unknown device
GET    /api/v1/unknown-devices/{mac}          - Get unknown device details
DELETE /api/v1/unknown-devices/{mac}          - Remove from unknown list
POST   /api/v1/unknown-devices/record         - Record device boot event
```

#### UI Components:
- **Unknown Devices List**: Shows all devices detected but not registered
- **Step-by-Step Wizard**: Modal-based multi-step registration process
- **Type Selection**: Visual selection with icons for each device type
- **Target Selection**: Choose between iSCSI image or local disk
- **Image/Installer Selection**: Filtered dropdown based on device type
- **Confirmation**: Review and confirm before registering

---

### 4. **Device Management** 🖥️
Complete device inventory with registration, activation, and management.

#### Features:
- **Register Devices**: Add devices by MAC address with custom names
- **Device Types**: Support for Raspberry Pi, x86, and x64 architectures
- **Enable/Disable**: Quickly toggle device status without deletion
- **View Assignments**: See which image is assigned to each device
- **Device Status**: Active/Inactive indicator for each device
- **Bulk Operations**: Register multiple devices, disable unused ones

#### API Endpoints:
```
GET    /api/v1/devices              - List all devices
POST   /api/v1/devices              - Create new device
GET    /api/v1/devices/{mac}        - Get device details
PUT    /api/v1/devices/{mac}        - Update device
DELETE /api/v1/devices/{mac}        - Delete device
POST   /api/v1/device-assignment    - Create device assignment
GET    /api/v1/device-assignment/{mac} - Get device assignment
```

#### UI Features:
- **Device Registration Form**: Create new device entries
- **Device Table**: View all devices with images and status
- **Status Badges**: Color-coded indicators (Active/Inactive)
- **Quick Actions**: Enable/Disable/Delete buttons for each device
- **MAC Address Display**: Clear, monospace formatting for MAC addresses

---

## 🎨 UI/UX Features

### Dark Mode (Default)
- **Color Scheme**: 
  - Primary Blue: `#0066cc`
  - Accent Orange: `#FF9500`
  - Dark backgrounds for reduced eye strain
  - High contrast text for readability

### Responsive Design
- Mobile-friendly layout with grid and flexbox
- Touch-friendly button sizes
- Responsive tables and forms
- Adaptive navigation

### Visual Components
- **Cards**: Structured information containers with hover effects
- **Badges**: Status indicators (Active, Inactive, Assigned, etc.)
- **Progress Bars**: Upload and processing indicators
- **Modals**: Focused workflows for assignments and registration
- **Spinners**: Loading states for async operations
- **Empty States**: User-friendly messaging when no data exists

### Navigation
- **Tabbed Interface**: Clean tab switching between sections
- **Header Navigation**: Quick access to Dashboard and Inventory
- **Consistent Styling**: Uniform buttons, forms, and spacing

---

## 📊 Dashboard Features

### Statistics Cards
- **Active Devices**: Count of devices currently enabled
- **iSCSI Images**: Total number of disk images available
- **OS Installers**: Count of uploaded OS installer files
- **Storage Used**: Total GB used by images and installers
- **Real-time Updates**: Dashboard refreshes every 30 seconds

### Visual Features
- Large, easy-to-read numbers
- Color-coded cards (Blue, Orange, Green, Yellow)
- Device count shows active/total ratio
- Emoji icons for quick visual identification

---

## 🔌 API Integration

### RESTful Architecture
- Standard HTTP methods (GET, POST, PUT, DELETE)
- JSON request/response format
- Proper HTTP status codes (200, 201, 204, 400, 404, 409)
- Error messages with details

### File Upload API
- **Multipart form data** support
- **Progress tracking** via XMLHttpRequest
- **Large file support** without timeout issues
- **Multiple file uploads** in sequence

### Data Persistence
- **JSON file storage** for all device/image data
- **Directory-based** file management for OS installers and images
- **Automatic directory creation** on first use
- **Safe concurrent access** with JSON locking

---

## 📁 File Structure

### Backend (FastAPI)
```
backend/
├── app/
│   ├── models.py           # Updated with Device, Image, OSInstaller models
│   ├── database.py         # JSON-based storage with unknown device support
│   ├── main.py             # FastAPI app setup
│   ├── api/
│   │   ├── v1.py          # New comprehensive API endpoints
│   │   └── boot.py        # Boot functionality
│   └── services/
│       └── file_service.py # NEW: File management service
```

### Frontend (React/TypeScript)
```
frontend/src/
├── components/
│   ├── ImageManagement.tsx     # NEW: Complete image management UI
│   ├── OsInstallerList.tsx     # NEW: Enhanced with upload & storage
│   ├── UnknownDeviceWizard.tsx # NEW: Multi-step device registration
│   └── DeviceList.tsx          # Enhanced with registration form
├── pages/
│   ├── Dashboard.tsx           # NEW: Real-time statistics
│   └── Inventory.tsx           # NEW: Tabbed component organization
├── styles/
│   └── index.css              # NEW: Dark mode, branding colors, responsive design
└── App.tsx                     # Updated with dark mode support
```

---

## 🚀 Testing Instructions

### Local Development (Docker Desktop)
```bash
# Navigate to project directory
cd /path/to/netboot-orchestrator

# Build Docker images
docker-compose -f docker-compose.local.yml build --no-cache

# Start services (API + Frontend only, no boot services)
docker-compose -f docker-compose.local.yml up -d

# Check status
docker-compose -f docker-compose.local.yml ps

# View logs
docker-compose logs -f netboot-orchestrator-api
docker-compose logs -f netboot-orchestrator-frontend
```

### Access Web UI
- **Frontend**: http://localhost:30000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Test Endpoints
```bash
# List devices
curl http://localhost:8000/api/v1/devices

# Create image
curl -X POST http://localhost:8000/api/v1/images \
  -H "Content-Type: application/json" \
  -d '{"id":"ubuntu-22-raspi","name":"Ubuntu 22.04 LTS","size_gb":4.5,"device_type":"raspi","created_at":"2026-02-14T00:00:00"}'

# Get OS installer files
curl http://localhost:8000/api/v1/os-installers/files

# Get storage info
curl http://localhost:8000/api/v1/storage/info
```

---

## 🔄 Workflow Examples

### Example 1: Setup a New Raspberry Pi
1. Raspberry Pi boots and attempts netboot
2. Device appears in "Unknown Devices" list
3. Click "Setup Device" button
4. Select "Raspberry Pi" device type
5. Choose "iSCSI Image" as installation target
6. Select "Ubuntu 22.04 LTS" image
7. Device is registered and image is assigned
8. Next boot: Pi automatically boots from iSCSI

### Example 2: Add OS Installer
1. Upload ISO or installer file via drag-and-drop
2. Watch real-time progress bar
3. File appears in OS Installers list
4. Select when setting up unknown devices
5. File is available for network boot

### Example 3: Manage Device Images
1. Create new iSCSI image (5 GB)
2. Give it a name: "CentOS 7 for x64"
3. Image appears in Image Management
4. Click "Assign"
5. Select device from dropdown
6. Image is now assigned to that device

---

## 📈 Data Models

### Image
```json
{
  "id": "ubuntu-22-raspi",
  "name": "Ubuntu 22.04 LTS",
  "size_gb": 4.5,
  "device_type": "raspi",
  "assigned_to": "AA:BB:CC:DD:EE:FF",
  "created_at": "2026-02-14T10:30:00"
}
```

### Device
```json
{
  "mac": "AA:BB:CC:DD:EE:FF",
  "device_type": "raspi",
  "name": "RaspberryPi-01",
  "enabled": true,
  "image_id": "ubuntu-22-raspi",
  "kernel_set": "default",
  "created_at": "2026-02-14T10:00:00",
  "updated_at": "2026-02-14T10:30:00"
}
```

### OSInstallerFile
```json
{
  "filename": "ubuntu-22.04-live-server-amd64.iso",
  "path": "ubuntu/22.04/server/amd64.iso",
  "size_bytes": 1234567890,
  "created_at": "2026-02-14T09:00:00",
  "modified_at": "2026-02-14T09:00:00"
}
```

### UnknownDevice
```json
{
  "mac": "AA:BB:CC:DD:EE:FF",
  "device_type": null,
  "boot_time": "2026-02-14T09:15:00",
  "status": "unknown"
}
```

---

## ✅ Completion Checklist

- [x] Backend API endpoints for image management
- [x] Backend API endpoints for OS file management
- [x] Backend API endpoints for unknown device wizard
- [x] File service for managing files and storage
- [x] Frontend: Image Management component with CRUD operations
- [x] Frontend: OS Installers with file upload and progress bar
- [x] Frontend: Unknown Device Wizard with multi-step flow
- [x] Frontend: Device Management with registration
- [x] Dark mode styling (default)
- [x] Netboot Orchestrator branding (Blue #0066cc, Orange #FF9500)
- [x] Responsive design for mobile and desktop
- [x] Status badges and visual indicators
- [x] Real-time data updates
- [x] Error handling and user feedback
- [x] Git commits and documentation

---

## 🔄 Version

**Netboot Orchestrator v2026-02-14-V1**

Latest commit: `feat: complete inventory management with Image Management, OS Installers, and Device Wizard components`

---

## 📝 Next Steps

1. **Deploy to Unraid** using full `docker-compose.yml` (includes TFTP, HTTP, iSCSI)
2. **Test boot workflows** with actual Raspberry Pi devices
3. **Monitor system logs** for any issues during boot
4. **Optimize storage** usage for large disk images
5. **Add TLS/HTTPS** support for production
6. **Implement authentication** for multi-user environments
7. **Add advanced features**: Device groups, custom boot scripts, etc.
