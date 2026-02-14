from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..models import Device, Image, KernelSet, OSInstaller, DeviceType
from ..database import Database

router = APIRouter(prefix="/api/v1", tags=["v1"])


def get_db() -> Database:
    return Database()


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


@router.put("/images/{image_id}/assign")
async def assign_image(image_id: str, mac: str, db: Database = Depends(get_db)):
    """Assign image to a device."""
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
    
    return {"status": "assigned"}


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
    return {"status": "unassigned"}


@router.get("/kernel-sets", response_model=dict)
async def list_kernel_sets(db: Database = Depends(get_db)):
    """List all kernel sets."""
    return db.get_all_kernel_sets()


@router.post("/kernel-sets", response_model=dict)
async def create_kernel_set(kernel_set: KernelSet, db: Database = Depends(get_db)):
    """Create a new kernel set."""
    return db.create_kernel_set(kernel_set.name, kernel_set.dict())


@router.get("/os-installers", response_model=List[dict])
async def list_os_installers(db: Database = Depends(get_db)):
    """List all OS installers."""
    return db.get_all_os_installers()


@router.post("/os-installers", response_model=dict)
async def create_os_installer(installer: OSInstaller, db: Database = Depends(get_db)):
    """Create OS installer metadata."""
    return db.create_os_installer(installer.name, installer.dict())
