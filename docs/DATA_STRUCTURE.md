# Data Structure Documentation

This document describes the data models and storage format for the RPi Netboot Orchestrator.

## JSON File Structure

The orchestrator uses JSON files for persistence. All data is stored in `/data` directory.

### profiles.json

Contains device profiles and registrations.

```json
{
  "aa:bb:cc:dd:ee:ff": {
    "mac": "aa:bb:cc:dd:ee:ff",
    "device_type": "raspi",
    "name": "lab-pi-01",
    "enabled": true,
    "image_id": "raspi-01",
    "kernel_set": "default",
    "created_at": "2024-02-14T10:30:00",
    "updated_at": "2024-02-14T10:35:00"
  },
  "11:22:33:44:55:66": {
    "mac": "11:22:33:44:55:66",
    "device_type": "x86",
    "name": "desktop-01",
    "enabled": true,
    "image_id": null,
    "kernel_set": "default",
    "created_at": "2024-02-14T11:00:00"
  }
}
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `mac` | string | MAC address (unique key) |
| `device_type` | enum | Device type: "raspi", "x86", "x64" |
| `name` | string | Human-readable device name |
| `enabled` | boolean | Whether device can boot |
| `image_id` | string\|null | Assigned iSCSI image ID |
| `kernel_set` | string | Kernel set to use |
| `created_at` | ISO8601 | Creation timestamp |
| `updated_at` | ISO8601 | Last update timestamp |

### images.json

Contains iSCSI disk image inventory and assignments.

```json
{
  "raspi-01": {
    "id": "raspi-01",
    "name": "Raspberry Pi Lab Node 01",
    "size_gb": 32,
    "device_type": "raspi",
    "assigned_to": "aa:bb:cc:dd:ee:ff",
    "created_at": "2024-02-14T10:25:00",
    "image_path": "/data/iscsi/images/raspi-01.img"
  },
  "ubuntu-desktop": {
    "id": "ubuntu-desktop",
    "name": "Ubuntu 22.04 Desktop",
    "size_gb": 64,
    "device_type": "x86",
    "assigned_to": null,
    "created_at": "2024-02-14T10:26:00",
    "image_path": "/data/iscsi/images/ubuntu-desktop.img"
  }
}
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique image identifier (key) |
| `name` | string | Human-readable image name |
| `size_gb` | number | Disk size in GB |
| `device_type` | enum | Compatible device type |
| `assigned_to` | string\|null | MAC address of assigned device |
| `created_at` | ISO8601 | Creation timestamp |
| `image_path` | string | Path to .img file |

### os.json

Contains OS installer metadata for PXE boot.

```json
{
  "ubuntu-22-netboot": {
    "name": "Ubuntu 22.04 Netboot",
    "path": "ubuntu-22-netboot",
    "kernel": "kernel",
    "initrd": "initrd",
    "kernel_cmdline": "root=/dev/nfs nfsroot=api:/data/http/os/ubuntu-22-netboot ip=dhcp",
    "device_type": "x86"
  },
  "debian-12-netboot": {
    "name": "Debian 12 Netboot",
    "path": "debian-12-netboot",
    "kernel": "kernel",
    "initrd": "initrd",
    "kernel_cmdline": "root=/dev/nfs nfsroot=api:/data/http/os/debian-12-netboot ip=dhcp",
    "device_type": "x64"
  }
}
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Display name |
| `path` | string | Path under `/data/http/os/` |
| `kernel` | string | Kernel filename |
| `initrd` | string | Initramfs filename |
| `kernel_cmdline` | string | Kernel command line parameters |
| `device_type` | enum | Compatible device type |

### settings.json

Contains global configuration and kernel sets.

```json
{
  "kernel_sets": {
    "default": {
      "name": "default",
      "kernel_url": "/http/raspi/kernels/default/kernel8.img",
      "initramfs_url": "/http/raspi/kernels/default/initramfs8",
      "is_default": true
    },
    "custom": {
      "name": "custom",
      "kernel_url": "/http/raspi/kernels/custom/kernel8.img",
      "initramfs_url": "/http/raspi/kernels/custom/initramfs8",
      "is_default": false
    }
  }
}
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `kernel_sets` | object | Map of kernel set configurations |
| `name` | string | Kernel set identifier |
| `kernel_url` | string | HTTP path to kernel |
| `initramfs_url` | string | HTTP path to initramfs |
| `is_default` | boolean | Default set for new devices |

## File System Structure

Complete `/data` directory structure:

```
/data/
│
├── http/                              # HTTP-served files (nginx root)
│   ├── raspi/
│   │   ├── kernels/
│   │   │   ├── default/
│   │   │   │   ├── kernel8.img       # Default kernel binary
│   │   │   │   └── initramfs8        # Default initramfs
│   │   │   ├── test/
│   │   │   │   ├── kernel8.img
│   │   │   │   └── initramfs8
│   │   │   └── [kernel-set-name]/     # Additional kernel sets
│   │   │
│   │   └── aa:bb:cc:dd:ee:ff/        # Per-MAC kernel (device-specific)
│   │       ├── kernel8.img           # Symlink or copy
│   │       └── initramfs8
│   │
│   ├── os/                            # OS installer netboot files
│   │   ├── ubuntu-22-netboot/
│   │   │   ├── kernel
│   │   │   ├── initrd
│   │   │   └── [boot files]
│   │   ├── debian-12-netboot/
│   │   │   ├── kernel
│   │   │   ├── initrd
│   │   │   └── [boot files]
│   │   └── [other-installer]/
│   │
│   └── ipxe/                          # Generated iPXE scripts
│       ├── menu.ipxe                  # Default menu (unknown devices)
│       └── aa:bb:cc:dd:ee:ff.ipxe     # Per-MAC boot script
│
├── tftp/                              # TFTP-served files
│   ├── raspi/
│   │   ├── bootcode.bin               # Raspberry Pi bootcode
│   │   ├── start4.elf
│   │   ├── fixup4.dat
│   │   ├── kernel8.img                # Default kernel
│   │   ├── initramfs8                 # Default initramfs
│   │   ├── config.txt                 # Default config
│   │   ├── cmdline.txt                # Default command line
│   │   │
│   │   └── 01:aa:bb:cc:dd:ee:ff/      # Per-MAC directory (generated)
│   │       ├── config.txt             # Device-specific config
│   │       └── cmdline.txt            # Device-specific cmdline
│   │
│   └── pxe/                           # x86 PXE bootloaders
│       ├── ipxe.efi                   # UEFI bootloader
│       ├── undionly.kpxe              # BIOS bootloader
│       └── [other-bootloaders]
│
├── iscsi/                             # iSCSI target data
│   ├── images/
│   │   ├── raspi-01.img               # Disk image files (raw or qcow2)
│   │   ├── raspi-02.img
│   │   ├── ubuntu-desktop.img
│   │   └── [other-images].img
│   │
│   └── targets.tgt                    # TGT daemon configuration
│
├── profiles.json                      # Device registry
├── images.json                        # Image inventory
├── os.json                            # OS installer metadata
└── settings.json                      # Global settings & kernel sets
```

## Device Type Compatibility

| Device Type | Default Bootloader | Boot Protocol | iSCSI Support |
|-------------|-------------------|---------------|---------------|
| `raspi` | bootcode.bin | TFTP → HTTP | Yes |
| `x86` | undionly.kpxe | DHCP → iPXE → HTTP | Yes |
| `x64` | ipxe.efi | DHCP → iPXE → HTTP | Yes |

## API Response Models

### Device Model

```typescript
interface Device {
  mac: string;                    // "aa:bb:cc:dd:ee:ff"
  device_type: "raspi" | "x86" | "x64";
  name: string;                   // "lab-pi-01"
  enabled: boolean;               // true
  image_id?: string;              // "raspi-01" | null
  kernel_set?: string;            // "default"
  created_at?: string;            // ISO8601
  updated_at?: string;            // ISO8601
}
```

### Image Model

```typescript
interface Image {
  id: string;                     // "raspi-01"
  name: string;                   // "Raspberry Pi Lab Node 01"
  size_gb: number;                // 32
  device_type: "raspi" | "x86" | "x64";
  assigned_to?: string;           // MAC address | null
  created_at?: string;            // ISO8601
  image_path?: string;            // "/data/iscsi/images/raspi-01.img"
}
```

### Boot Check-in Response

```typescript
interface BootCheckInResponse {
  action: "boot_image" | "boot_default" | "show_menu";
  image_id?: string;              // For boot_image
  image_path?: string;            // For boot_image
  kernel_set?: string;
  device_type?: string;           // For show_menu
  message?: string;
}
```

## Database Operations

### Creating a Device

1. Load `profiles.json`
2. Check MAC doesn't exist
3. Add entry with new data
4. Save `profiles.json`
5. Generate TFTP config files
6. Write to `/data/tftp/raspi/01:MAC/`

### Assigning an Image

1. Load `profiles.json` and `images.json`
2. Update device: set `image_id`
3. Update image: set `assigned_to`
4. Save both files
5. Create/update iSCSI target configuration
6. Reload tgtd service

### Creating Kernel Set

1. Load `settings.json`
2. Add entry to `kernel_sets`
3. Save `settings.json`
4. Available for new device assignments

## Migration and Backup

Recommended backup strategy:

```bash
# Daily backup
rsync -av /data/ /backup/netboot-$(date +%Y%m%d)/

# Backup before major changes
cp /data/profiles.json /data/profiles.json.bak
cp /data/images.json /data/images.json.bak
```

Restoration:

```bash
# Restore single file
cp /backup/netboot-20240214/profiles.json /data/

# Restore entire data directory
rsync -av /backup/netboot-20240214/ /data/
```

## Constraints and Limits

- **MAC Address Format**: `xx:xx:xx:xx:xx:xx` (lowercase)
- **Device Name**: Max 64 characters, alphanumeric + hyphens
- **Image ID**: Max 64 characters, no special characters
- **Disk Size**: Limited by filesystem (typically 10TB+)
- **Concurrent Devices**: Depends on hardware (100+ typical)
- **JSON File Size**: Typically <10MB per file

## Data Consistency

The orchestrator uses atomic writes (write to temp file, then rename) to maintain data integrity. In case of power loss:

1. JSON files are recovered on next startup
2. Any incomplete writes are discarded
3. Last-known-good state is used

For production, consider:
- Regular backups
- Read-only filesystem fallback
- Database replication
