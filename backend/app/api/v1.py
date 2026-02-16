from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import FileResponse, PlainTextResponse
from typing import List
from pathlib import Path
from ..models import (
    Device, Image, KernelSet, OSInstaller, DeviceType,
    UnknownDevice, DeviceAssignment, OSInstallerFile
)
from ..database import Database
from ..services.file_service import FileService
import os

router = APIRouter(prefix="/api/v1", tags=["v1"])


def get_version() -> str:
    """Read version from VERSION file or return default."""
    try:
        version_file = Path(__file__).parent.parent.parent.parent / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
    except Exception:
        pass
    return "2026-02-15-V1"


def get_db() -> Database:
    return Database()


def get_file_service() -> FileService:
    return FileService(
        os_installers_path=os.getenv("OS_INSTALLERS_PATH", "/data/os-installers"),
        images_path=os.getenv("IMAGES_PATH", "/data/images")
    )


# ==================== VERSION ENDPOINT ====================

@router.get("/version")
async def get_app_version():
    """Get application version."""
    return {
        "version": get_version(),
        "name": "Netboot Orchestrator"
    }


# ==================== DEVICE ENDPOINTS ====================

@router.get("/devices", response_model=List[dict])
async def list_devices(db: Database = Depends(get_db)):
    """List all registered devices."""
    return db.get_all_devices()


@router.post("/devices", response_model=dict)
async def create_device(device: Device, db: Database = Depends(get_db)):
    """Create a new device profile."""
    existing = db.get_device(device.mac)
    if existing:
        raise HTTPException(status_code=409, detail="Device already exists")
    return db.create_device(device.mac, device.dict())


@router.get("/devices/{mac}", response_model=dict)
async def get_device(mac: str, db: Database = Depends(get_db)):
    """Get device profile by MAC address."""
    device = db.get_device(mac)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.put("/devices/{mac}", response_model=dict)
async def update_device(mac: str, device: Device, db: Database = Depends(get_db)):
    """Update device profile."""
    existing = db.get_device(mac)
    if not existing:
        raise HTTPException(status_code=404, detail="Device not found")
    return db.update_device(mac, device.dict())


@router.delete("/devices/{mac}")
async def delete_device(mac: str, db: Database = Depends(get_db)):
    """Delete device profile."""
    if not db.delete_device(mac):
        raise HTTPException(status_code=404, detail="Device not found")
    return {"status": "deleted"}


# ==================== IMAGE ENDPOINTS ====================

@router.get("/images", response_model=List[dict])
async def list_images(db: Database = Depends(get_db)):
    """List all iSCSI images."""
    return db.get_all_images()


@router.post("/images", response_model=dict)
async def create_image(image: Image, db: Database = Depends(get_db)):
    """Create a new iSCSI image."""
    existing = db.get_image(image.id)
    if existing:
        raise HTTPException(status_code=409, detail="Image already exists")
    return db.create_image(image.id, image.dict())


@router.get("/images/{image_id}", response_model=dict)
async def get_image(image_id: str, db: Database = Depends(get_db)):
    """Get image by ID."""
    image = db.get_image(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    return image


@router.put("/images/{image_id}", response_model=dict)
async def update_image(image_id: str, image: Image, db: Database = Depends(get_db)):
    """Update image details."""
    existing = db.get_image(image_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Image not found")
    return db.update_image(image_id, image.dict())


@router.delete("/images/{image_id}")
async def delete_image(image_id: str, db: Database = Depends(get_db)):
    """Delete an image."""
    image = db.get_image(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Unassign from any device
    assigned_to = image.get("assigned_to")
    if assigned_to:
        db.update_device(assigned_to, {"image_id": None})
    
    if not db.delete_image(image_id):
        raise HTTPException(status_code=500, detail="Failed to delete image")
    return {"status": "deleted"}


@router.put("/images/{image_id}/assign")
async def assign_image(image_id: str, mac: str = Query(...), db: Database = Depends(get_db)):
    """Assign image to a device by MAC address."""
    image = db.get_image(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    device = db.get_device(mac)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Update image assignment
    db.update_image(image_id, {"assigned_to": mac})
    
    # Update device image reference
    db.update_device(mac, {"image_id": image_id})
    
    return {"status": "assigned", "image_id": image_id, "mac": mac}


@router.put("/images/{image_id}/unassign")
async def unassign_image(image_id: str, db: Database = Depends(get_db)):
    """Unassign image from device."""
    image = db.get_image(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    assigned_to = image.get("assigned_to")
    if assigned_to:
        db.update_device(assigned_to, {"image_id": None})
    
    db.update_image(image_id, {"assigned_to": None})
    return {"status": "unassigned", "image_id": image_id}


# ==================== OS INSTALLER ENDPOINTS ====================

@router.get("/os-installers/tree")
async def get_os_installers_tree(file_service: FileService = Depends(get_file_service)):
    """Get OS installer files as a folder tree structure."""
    result = file_service.get_folder_tree(is_images=False)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@router.get("/os-installers/browse")
async def browse_os_installers_folder(
    folder_path: str = Query("", description="Folder path relative to OS installers root"),
    file_service: FileService = Depends(get_file_service)
):
    """Browse OS installer folder contents (lazy loading)."""
    result = file_service.get_folder_contents(folder_path, is_images=False)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@router.get("/os-installers/files")
async def list_os_installer_files(file_service: FileService = Depends(get_file_service)):
    """List all OS installer files in the directory."""
    result = file_service.list_os_installer_files()
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@router.get("/os-installers/files/{file_path:path}")
async def get_os_installer_file_info(
    file_path: str,
    file_service: FileService = Depends(get_file_service)
):
    """Get information about a specific OS installer file."""
    result = file_service.get_file_info(file_path, is_image=False)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.delete("/os-installers/files/{file_path:path}")
async def delete_os_installer_file(
    file_path: str,
    file_service: FileService = Depends(get_file_service)
):
    """Delete an OS installer file."""
    result = file_service.delete_file(file_path, is_image=False)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to delete file"))
    return result


@router.post("/os-installers/upload")
async def upload_os_installer(
    file: UploadFile = File(...),
    file_service: FileService = Depends(get_file_service)
):
    """Upload an OS installer file."""
    try:
        import shutil
        from pathlib import Path
        
        file_service.os_installers_path.mkdir(parents=True, exist_ok=True)
        file_path = file_service.os_installers_path / file.filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        stat = file_path.stat()
        return {
            "success": True,
            "filename": file.filename,
            "size_bytes": stat.st_size,
            "created_at": os.path.getmtime(file_path)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/os-installers/metadata", response_model=List[dict])
async def list_os_installers_metadata(db: Database = Depends(get_db)):
    """List OS installer metadata from database."""
    return db.get_all_os_installers()


@router.post("/os-installers/metadata", response_model=dict)
async def create_os_installer_metadata(installer: OSInstaller, db: Database = Depends(get_db)):
    """Create OS installer metadata."""
    return db.create_os_installer(installer.name, installer.dict())


# ==================== IMAGE FILES ENDPOINTS ====================

@router.get("/images/files")
async def list_image_files(file_service: FileService = Depends(get_file_service)):
    """List all iSCSI disk image files."""
    result = file_service.list_images()
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@router.post("/images/create-directory")
async def create_image_directory(
    image_name: str = Query(...),
    file_service: FileService = Depends(get_file_service)
):
    """Create a new directory for an iSCSI image."""
    result = file_service.create_image_directory(image_name)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to create directory"))
    return result


@router.post("/images/upload")
async def upload_image_file(
    image_name: str = Query(...),
    file: UploadFile = File(...),
    file_service: FileService = Depends(get_file_service)
):
    """Upload an iSCSI disk image file."""
    try:
        import shutil
        
        image_dir = file_service.images_path / image_name
        image_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = image_dir / file.filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        stat = file_path.stat()
        return {
            "success": True,
            "filename": file.filename,
            "image_name": image_name,
            "size_bytes": stat.st_size,
            "size_gb": round(stat.st_size / (1024**3), 2),
            "created_at": os.path.getmtime(file_path)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== UNKNOWN DEVICE ENDPOINTS ====================

@router.get("/unknown-devices", response_model=List[dict])
async def list_unknown_devices(db: Database = Depends(get_db)):
    """List all unknown devices that have booted."""
    return db.get_all_unknown_devices()


@router.post("/unknown-devices/register", response_model=dict)
async def register_unknown_device(
    mac: str = Query(...),
    device_type: DeviceType = Query(...),
    db: Database = Depends(get_db)
):
    """Register an unknown device and create a device profile."""
    # Check if already known
    device = db.get_device(mac)
    if device:
        return {"status": "already_registered", "device": device}
    
    # Create new device
    new_device = Device(
        mac=mac,
        device_type=device_type,
        name=f"{device_type.value.upper()}-{mac[-6:]}",
        enabled=True
    )
    
    created = db.create_device(mac, new_device.dict())
    
    # Remove from unknown devices
    db.remove_unknown_device(mac)
    
    return {"status": "registered", "device": created}


@router.post("/unknown-devices/record")
async def record_unknown_device(
    mac: str = Query(...),
    device_type: DeviceType = Query(None),
    db: Database = Depends(get_db)
):
    """Record a device that booted but is unknown."""
    return db.record_unknown_device(mac, device_type)


@router.get("/unknown-devices/{mac}")
async def get_unknown_device(mac: str, db: Database = Depends(get_db)):
    """Get unknown device details."""
    device = db.get_unknown_device(mac)
    if not device:
        raise HTTPException(status_code=404, detail="Unknown device not found")
    return device


@router.delete("/unknown-devices/{mac}")
async def remove_unknown_device(mac: str, db: Database = Depends(get_db)):
    """Remove an unknown device from the list."""
    if not db.remove_unknown_device(mac):
        raise HTTPException(status_code=404, detail="Unknown device not found")
    return {"status": "removed"}


# ==================== DEVICE ASSIGNMENT ENDPOINTS ====================

@router.post("/device-assignment")
async def create_device_assignment(
    assignment: DeviceAssignment,
    db: Database = Depends(get_db)
):
    """Create or update device assignment (iSCSI image + OS installer)."""
    device = db.get_device(assignment.mac)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Update device with assignment
    update_data = {
        "image_id": assignment.image_id,
        "installation_target": assignment.installation_target
    }
    
    if assignment.image_id:
        image = db.get_image(assignment.image_id)
        if not image:
            raise HTTPException(status_code=404, detail="Image not found")
        # Assign image to device
        db.update_image(assignment.image_id, {"assigned_to": assignment.mac})
    
    updated = db.update_device(assignment.mac, update_data)
    return {"status": "assigned", "device": updated}


@router.get("/device-assignment/{mac}")
async def get_device_assignment(mac: str, db: Database = Depends(get_db)):
    """Get device assignment details."""
    device = db.get_device(mac)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    assignment = {
        "mac": mac,
        "image_id": device.get("image_id"),
        "installation_target": device.get("installation_target", "iscsi"),
        "device_type": device.get("device_type"),
        "name": device.get("name")
    }
    
    if device.get("image_id"):
        image = db.get_image(device["image_id"])
        if image:
            assignment["image_details"] = image
    
    return assignment


# ==================== KERNEL SETS ENDPOINTS ====================

@router.get("/kernel-sets")
async def list_kernel_sets(db: Database = Depends(get_db)):
    """List all kernel sets."""
    return db.get_all_kernel_sets()


@router.post("/kernel-sets", response_model=dict)
async def create_kernel_set(kernel_set: KernelSet, db: Database = Depends(get_db)):
    """Create a new kernel set."""
    return db.create_kernel_set(kernel_set.name, kernel_set.dict())


# ==================== STORAGE ENDPOINTS ====================

@router.get("/storage/info")
async def get_storage_info(file_service: FileService = Depends(get_file_service)):
    """Get storage usage information."""
    return file_service.get_storage_info()


# ==================== BOOT MENU ENDPOINTS ====================

@router.get("/boot/ipxe/menu")
async def boot_ipxe_menu(file_service: FileService = Depends(get_file_service)):
    """
    Generate iPXE boot menu script with available OS installers.
    This endpoint is called by iPXE clients to get the boot menu.
    
    Uses iPXE menu/item/choose system for proper interactive menus.
    """
    # Get list of available OS installers
    try:
        result = file_service.list_os_installer_files()
        installers = result.get('files', [])
    except Exception as e:
        installers = []
    
    boot_server_ip = os.getenv("BOOT_SERVER_IP", "192.168.1.50")
    version = get_version()
    
    # Categorize installers by OS type
    def categorize(filename: str) -> str:
        fl = filename.lower()
        if any(w in fl for w in ['windows', 'win10', 'win11', 'winpe', 'server2']):
            return 'Windows'
        elif any(w in fl for w in ['ubuntu', 'debian', 'fedora', 'centos', 'rhel', 'rocky', 'alma', 'arch', 'mint', 'opensuse', 'suse', 'linux']):
            return 'Linux'
        elif any(w in fl for w in ['proxmox', 'esxi', 'vmware', 'truenas', 'freenas', 'opnsense', 'pfsense', 'unraid']):
            return 'Infrastructure'
        else:
            return 'Other'
    
    def format_size(size_bytes: int) -> str:
        if size_bytes <= 0:
            return "N/A"
        gb = size_bytes / (1024**3)
        if gb >= 1:
            return f"{gb:.1f} GB"
        mb = size_bytes / (1024**2)
        return f"{mb:.0f} MB"
    
    # Build iPXE menu script
    menu_script = f"""#!ipxe
# Netboot Orchestrator v{version}
# Boot menu generated dynamically by API

:menu
menu ========== Netboot Orchestrator v{version} ==========
item --gap --
item --gap --  MAC: ${{net0/mac}}  |  IP: ${{net0/ip}}
item --gap --  Gateway: ${{net0/gateway}}
item --gap --
"""
    
    if installers:
        # Group by category
        categories: dict = {}
        for inst in installers:
            cat = categorize(inst['filename'])
            categories.setdefault(cat, []).append(inst)
        
        # Preferred category order
        cat_order = ['Windows', 'Linux', 'Infrastructure', 'Other']
        idx = 0
        
        for cat in cat_order:
            if cat not in categories:
                continue
            menu_script += f"item --gap --  --- {cat} ---\n"
            for inst in categories[cat]:
                idx += 1
                label = f"os_{idx}"
                name = inst['filename'][:45]
                size = format_size(inst.get('size_bytes', 0))
                menu_script += f"item {label}    {name}  [{size}]\n"
            menu_script += "item --gap --\n"
        
        menu_script += "item --gap --  --- Tools ---\n"
        menu_script += "item shell     iPXE Shell\n"
        menu_script += "item reboot    Reboot\n"
        menu_script += "item --gap --\n"
        menu_script += "choose selected || goto shell\n"
        menu_script += "goto ${selected}\n\n"
        
        # Add goto targets for each installer
        idx = 0
        for cat in cat_order:
            if cat not in categories:
                continue
            for inst in categories[cat]:
                idx += 1
                label = f"os_{idx}"
                name = inst['filename'][:50]
                path = inst['path']
                url = f"http://{boot_server_ip}:8000/api/v1/os-installers/download/{path}"
                
                menu_script += f""":{label}
echo
echo ================================================
echo  Loading: {name}
echo  Source:  {url}
echo ================================================
echo
chain {url} || goto failed
goto menu

"""
    else:
        menu_script += """item --gap --  No OS installers found
item --gap --
item --gap --  Upload ISOs via the Web UI or place
item --gap --  them in the /isos directory
item --gap --
item shell     iPXE Shell
item reboot    Reboot
item --gap --
choose selected || goto shell
goto ${selected}

"""
    
    menu_script += """:failed
echo
echo !! Download failed - returning to menu in 5s...
sleep 5
goto menu

:shell
echo
echo Type 'exit' to return to menu
echo
shell
goto menu

:reboot
reboot
"""
    
    return PlainTextResponse(menu_script)



@router.get("/boot/devices/{mac}")
async def register_boot_device(mac: str, db: Database = Depends(get_db)):
    """
    Register a device for network boot.
    This endpoint is called by iPXE to register the booting device.
    """
    device = db.get_device(mac)
    
    if not device:
        # Create new device record if it doesn't exist
        device = {
            "mac": mac,
            "device_type": "unknown",
            "name": f"Unnamed Device ({mac})",
            "image_id": None,
            "installation_target": "http"
        }
        db.create_device(mac, device)
    
    return {
        "status": "registered",
        "mac": mac,
        "device_info": device
    }

@router.get("/os-installers/download/{file_path:path}")
async def download_os_installer(file_path: str, file_service: FileService = Depends(get_file_service)):
    """
    Download an OS installer file.
    This endpoint serves OS installer files to iPXE clients.
    """
    try:
        # Construct full path
        full_path = Path(os.getenv("OS_INSTALLERS_PATH", "/data/os-installers")) / file_path
        
        # Security check - prevent path traversal
        if not full_path.resolve().is_relative_to(Path(os.getenv("OS_INSTALLERS_PATH", "/data/os-installers")).resolve()):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if file exists
        if not full_path.exists() or not full_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(full_path, filename=full_path.name)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


