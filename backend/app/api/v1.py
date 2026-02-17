from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse, Response, StreamingResponse
from typing import List
from pathlib import Path
from ..models import (
    Device, Image, KernelSet, OSInstaller, DeviceType,
    UnknownDevice, DeviceAssignment, OSInstallerFile
)
from ..database import Database
from ..services.file_service import FileService
import os
import re
import logging

logger = logging.getLogger(__name__)


def _env(name: str, default: str) -> str:
    """Get env var, also checking for names with trailing whitespace (Unraid quirk)."""
    val = os.getenv(name)
    if val is not None:
        return val.strip()
    val = os.getenv(name + " ")
    if val is not None:
        return val.strip()
    return default


router = APIRouter(prefix="/api/v1", tags=["v1"])


def get_version() -> str:
    """Read version from VERSION file or return default."""
    try:
        # Try /app/VERSION first (Docker), then relative to project root
        for path in [
            Path("/app/VERSION"),
            Path(__file__).parent.parent.parent.parent / "VERSION",
        ]:
            if path.exists():
                return path.read_text().strip()
    except Exception:
        pass
    return "unknown"


def get_db() -> Database:
    return Database()


def get_file_service() -> FileService:
    return FileService(
        os_installers_path=_env("OS_INSTALLERS_PATH", "/data/os-installers"),
        images_path=_env("IMAGES_PATH", "/data/images")
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


# ==================== BOOT DEVICE REGISTRATION ====================

@router.get("/boot/devices/{mac}")
async def register_boot_device(mac: str, db: Database = Depends(get_db)):
    """Register a device for network boot."""
    device = db.get_device(mac)
    if not device:
        device = {
            "mac": mac,
            "device_type": "unknown",
            "name": f"Unnamed Device ({mac})",
            "image_id": None,
            "installation_target": "http",
        }
        db.create_device(mac, device)
    return {"status": "registered", "mac": mac, "device_info": device}


# ==================== OS INSTALLER DOWNLOAD ====================

def _resolve_installer_path(file_path: str) -> Path:
    """Resolve and validate an OS installer file path."""
    base = Path(_env("OS_INSTALLERS_PATH", "/data/os-installers"))
    full_path = base / file_path
    if not full_path.resolve().is_relative_to(base.resolve()):
        raise HTTPException(status_code=403, detail="Access denied")
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return full_path


@router.head("/os-installers/download/{file_path:path}")
async def head_os_installer(file_path: str):
    """HEAD handler for OS installer files.

    iPXE's sanboot sends HEAD first to discover file size and
    whether the server supports range requests.  Without an explicit
    HEAD that returns Accept-Ranges, sanboot aborts with 4xx.
    """
    full_path = _resolve_installer_path(file_path)
    stat = full_path.stat()
    return Response(
        status_code=200,
        headers={
            "Content-Length": str(stat.st_size),
            "Accept-Ranges": "bytes",
            "Content-Type": "application/octet-stream",
        },
    )


@router.get("/os-installers/download/{file_path:path}")
async def download_os_installer(
    file_path: str,
    request: Request,
    file_service: FileService = Depends(get_file_service),
):
    """Serve OS installer files with HTTP Range support.

    iPXE sanboot reads ISOs as HTTP block devices using Range requests.
    This endpoint handles:
      - Regular GET  -> 200 with full file
      - Range GET    -> 206 with partial content
      - HEAD         -> handled by head_os_installer above
    """
    try:
        full_path = _resolve_installer_path(file_path)
        file_size = full_path.stat().st_size

        # Check for Range header (iPXE sanboot uses this)
        range_header = request.headers.get("range")
        if range_header:
            range_match = re.match(r"bytes=(\d+)-(\d*)", range_header)
            if range_match:
                start = int(range_match.group(1))
                end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
                if start >= file_size:
                    return Response(
                        status_code=416,
                        headers={
                            "Content-Range": f"bytes */{file_size}",
                        },
                    )
                end = min(end, file_size - 1)
                content_length = end - start + 1

                logger.debug(f"Range request: bytes={start}-{end}/{file_size} for {file_path}")

                def iter_file():
                    with open(full_path, "rb") as f:
                        f.seek(start)
                        remaining = content_length
                        while remaining > 0:
                            chunk_size = min(65536, remaining)
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            remaining -= len(chunk)
                            yield chunk

                return StreamingResponse(
                    iter_file(),
                    status_code=206,
                    headers={
                        "Content-Range": f"bytes {start}-{end}/{file_size}",
                        "Content-Length": str(content_length),
                        "Accept-Ranges": "bytes",
                        "Content-Type": "application/octet-stream",
                    },
                )

        # No Range header -> serve full file
        return FileResponse(
            full_path,
            filename=full_path.name,
            headers={"Accept-Ranges": "bytes"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
