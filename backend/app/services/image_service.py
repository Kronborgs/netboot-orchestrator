from typing import Optional, Dict, List
from ..models import Image
from ..database import Database


class ImageService:
    """Service for managing iSCSI images."""
    
    def __init__(self, db: Database):
        self.db = db
    
    def create_image(self, image: Image) -> Dict:
        """Create a new iSCSI image."""
        image_data = self.db.create_image(image.id, image.dict())
        
        # Create empty image file in /data/iscsi/images/
        self._allocate_image_file(image.id, image.size_gb)
        
        return image_data
    
    def _allocate_image_file(self, image_id: str, size_gb: float):
        """Allocate iSCSI image file on disk."""
        # This would create the .img file at /data/iscsi/images/{image_id}.img
        # For now, it's a placeholder
        pass
    
    def assign_image(self, image_id: str, mac: str) -> Dict:
        """Assign image to device and configure iSCSI target."""
        image = self.db.get_image(image_id)
        if not image:
            raise ValueError(f"Image {image_id} not found")
        
        device = self.db.get_device(mac)
        if not device:
            raise ValueError(f"Device {mac} not found")
        
        # Update assignments
        self.db.update_image(image_id, {"assigned_to": mac})
        self.db.update_device(mac, {"image_id": image_id})
        
        # Configure iSCSI target for MAC
        self._configure_iscsi_target(mac, image_id)
        
        return {"status": "assigned"}
    
    def _configure_iscsi_target(self, mac: str, image_id: str):
        """Configure iSCSI target for a specific MAC."""
        # This would use tgtadm to add a new iSCSI target
        # For now, it's a placeholder
        pass
    
    def list_images(self) -> List[Dict]:
        """List all images."""
        return self.db.get_all_images()
    
    def get_image(self, image_id: str) -> Optional[Dict]:
        """Get image by ID."""
        return self.db.get_image(image_id)
