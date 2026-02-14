# Boot Flow Documentation

Detailed explanation of how devices boot through the RPi Netboot Orchestrator.

## Overview

The orchestrator supports different boot paths depending on:
- Device type (Raspberry Pi, x86, x64)
- Device registration status (known vs unknown)
- Available resources (assigned images, kernel sets)

## Raspberry Pi Boot Flow

### Known Device (Registered MAC)

```
┌─────────────────────────────────────────────────────────┐
│ 1. Power On - Network Boot Attempt                      │
│    - Pi sends BOOTP/DHCP request                        │
│    - TFTP client starts                                 │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│ 2. TFTP Server Response                                 │
│    - Server sends bootcode.bin                          │
│    - Client loads: start4.elf, fixup4.dat              │
│    - TFTP retrieves kernel8.img, initramfs8            │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│ 3. Load Per-MAC Config (MAC-specific)                  │
│    - TFTP path: /raspi/01:aa:bb:cc:dd:ee:ff/           │
│    - config.txt points to HTTP kernel                   │
│    - Device MAC is now known                            │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│ 4. Download Kernel via HTTP                            │
│    - If device has assigned image:                      │
│      └─ kernel=http://api/raspi/kernel8.img             │
│    - If no image assigned:                              │
│      └─ kernel=http://api/raspi/default/kernel8.img   │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│ 5. Boot with iSCSI (if image assigned)                 │
│    - cmdline.txt includes iSCSI boot params             │
│    - Device connects to iSCSI target                    │
│    - Mounts assigned disk image as root                │
│    - Full OS runs from iSCSI target                     │
│    - OR local boot if no image assigned                │
└─────────────────────────────────────────────────────────┘
```

### Unknown Device (Unregistered MAC)

```
┌─────────────────────────────────────────────────────────┐
│ 1. Power On - Network Boot Attempt                      │
│    - Pi sends BOOTP/DHCP request                        │
│    - TFTP downloads default bootcode                    │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│ 2. Load Default Config (no MAC in path)                │
│    - TFTP path: /raspi/ (not per-MAC)                  │
│    - Includes special initramfs with menu               │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│ 3. Boot with Menu Initramfs                            │
│    - Kernel + initramfs loaded via HTTP                │
│    - Interactive menu appears at boot                   │
│    - Options: Register, Create Image, Select Boot     │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│ 4. Device Registration                                 │
│    - User selects "Register This Device"               │
│    - Sends check-in request to API:                    │
│      GET /api/v1/boot/check-in?mac=...                │
│    - API creates device profile                        │
│    - TFTP config generated for MAC                     │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│ 5. Next Boot (Device Now Known)                        │
│    - Device recognized as registered                    │
│    - Follows "Known Device" flow above                  │
└─────────────────────────────────────────────────────────┘
```

## x86/x64 Boot Flow

### iPXE Boot Process

```
┌─────────────────────────────────────────────────────────┐
│ 1. PXE Boot                                             │
│    - BIOS/UEFI sends PXE request                        │
│    - DHCP server responds                               │
│    - TFTP sends iPXE bootloader                         │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│ 2. iPXE Chainloader                                     │
│    - iPXE loads and gains control                       │
│    - Network initialized with DHCP                      │
│    - Ready to fetch boot scripts                        │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ Check Device Status
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼ Known MAC                   ▼ Unknown MAC
    ┌────────────┐              ┌──────────────┐
    │ Load MAC-  │              │ Load Menu    │
    │ specific   │              │ Script       │
    │ boot entry │              └──────┬───────┘
    └────────────┘                     │
        │                              │
        └──────────────┬───────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│ 3. Boot Options                                         │
│    - If known MAC + image assigned:                     │
│      └─ Boot from iSCSI target                          │
│    - If unknown MAC:                                    │
│      └─ Show OS installer menu                         │
│    - Interactive selection                              │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│ 4. OS Installation or Image Boot                       │
│    - iPXE downloads kernel/initrd                       │
│    - Or connects to iSCSI for pre-configured image      │
│    - Boot continues from selected option                │
└─────────────────────────────────────────────────────────┘
```

## Configuration File Generation

When a device is registered, the orchestrator generates configuration files:

### For Raspberry Pi

**Location**: `/data/tftp/raspi/01:aa:bb:cc:dd:ee:ff/`

**config.txt**:
```
enable_uart=1
kernel_address=0x200000
device_tree_address=0x100000
initramfs initramfs8

# Point to HTTP kernel
kernel=http://api:8000/api/raspi/aa:bb:cc:dd:ee:ff/kernel8.img
```

**cmdline.txt**:
```
console=ttyAMA0,115200 console=tty1 root=/dev/nbd0 nbd.connect=iscsi-target:3260
```

### For x86/x64

**Location**: `/data/http/ipxe/aa:bb:cc:dd:ee:ff.ipxe`

```
#!ipxe
echo Booting device aa:bb:cc:dd:ee:ff
set base http://api:8000

# If image assigned
sanboot iscsi:iscsi-target:3260::1:iqn.2024.local:device.${net0/mac}

# Or show menu
chain ${base}/api/v1/boot/ipxe/menu
```

## API Check-in Endpoint

Devices call this endpoint to determine their boot action:

**Endpoint**: `GET /api/v1/boot/check-in`

**Parameters**:
- `mac`: Device MAC address
- `device_type`: "raspi", "x86", or "x64"

**Response Examples**:

Known device with image:
```json
{
  "action": "boot_image",
  "image_id": "raspi-01",
  "image_path": "/data/iscsi/images/raspi-01.img",
  "kernel_set": "default"
}
```

Unknown device:
```json
{
  "action": "show_menu",
  "device_type": "raspi",
  "message": "Unknown device. Please register or select boot option."
}
```

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Network Boot Client                       │
│  (Raspberry Pi, x86, x64)                                   │
└────────────────────────┬────────────────────────────────────┘
                         │
     ┌───────────────────┼───────────────────┐
     │                   │                   │
     ▼                   ▼                   ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────┐
│ TFTP Server │  │ HTTP Server  │  │ iSCSI Target │
│ Port 69     │  │ Port 80/8080 │  │ Port 3260    │
└──────┬──────┘  └──────┬───────┘  └──────┬───────┘
       │                │                  │
       └────────────────┼──────────────────┘
                        │
                        ▼
            ┌──────────────────────┐
            │   FastAPI Backend    │
            │     (Port 8000)      │
            │                      │
            │ - Device Management  │
            │ - Image Management   │
            │ - Boot Logic         │
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │   JSON Database      │
            │   (/data/*.json)     │
            │                      │
            │ - profiles.json      │
            │ - images.json        │
            │ - os.json            │
            │ - settings.json      │
            └──────────────────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │    React Frontend    │
            │    (Port 3000)       │
            └──────────────────────┘
```

## Error Handling

### TFTP Timeout
- Device retries TFTP request
- After multiple attempts, boot may fail
- Check network connectivity and TFTP service status

### HTTP 404 on Kernel
- Device requested kernel file not found
- Verify config.txt HTTP URL is correct
- Check kernel files exist in `/data/http/`

### iSCSI Connection Failed
- Device couldn't connect to iSCSI target
- Verify iSCSI service is running
- Check network policies and firewall
- Confirm target is properly configured

## Performance Considerations

- **TFTP**: Lightweight, stateless, UDP-based
- **HTTP**: Efficient for large file transfers (kernels, images)
- **iSCSI**: Direct block-level I/O, lowest latency
- **Initramfs Size**: Keep small (<50MB) for fast boot
- **Network**: 1Gbps+ recommended for iSCSI performance

## Security Notes

- Boot check-in endpoint is public (no authentication)
- Consider network isolation or VPN for production
- Generated config files should be protected
- iSCSI traffic should be on trusted network or encrypted
