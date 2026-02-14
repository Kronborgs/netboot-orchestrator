from fastapi import APIRouter, Depends
from ..models import BootCheckIn, DeviceType
from ..database import Database

router = APIRouter(prefix="/api/v1/boot", tags=["boot"])


def get_db() -> Database:
    return Database()


@router.get("/check-in")
async def check_in(mac: str, device_type: str, db: Database = Depends(get_db)):
    """
    Check-in endpoint for unknown devices at boot time.
    Returns action and relevant boot information.
    """
    device = db.get_device(mac)
    
    if device:
        # Known device - return boot image or default kernel
        image_id = device.get("image_id")
        kernel_set = device.get("kernel_set", "default")
        
        if image_id:
            image = db.get_image(image_id)
            return {
                "action": "boot_image",
                "image_id": image_id,
                "image_path": f"/data/iscsi/images/{image_id}.img",
                "kernel_set": kernel_set
            }
        else:
            return {
                "action": "boot_default",
                "kernel_set": kernel_set
            }
    else:
        # Unknown device - show menu
        return {
            "action": "show_menu",
            "device_type": device_type,
            "message": "Unknown device. Please register or select boot option."
        }
