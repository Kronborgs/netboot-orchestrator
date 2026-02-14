from typing import List, Optional, Dict
from ..models import Device
from ..database import Database


class DeviceService:
    """Service for managing device profiles and TFTP configurations."""
    
    def __init__(self, db: Database):
        self.db = db
    
    def register_device(self, device: Device) -> Dict:
        """Register a new device and generate TFTP config."""
        device_data = self.db.create_device(device.mac, device.dict())
        
        # Generate TFTP config for Raspberry Pi
        if device.device_type == "raspi":
            self._generate_raspi_tftp_config(device.mac, device.kernel_set)
        
        return device_data
    
    def _generate_raspi_tftp_config(self, mac: str, kernel_set: str):
        """Generate per-MAC TFTP config for Raspberry Pi."""
        # This would be implemented to write config files to /data/tftp/raspi/01:mac/
        # For now, it's a placeholder
        pass
    
    def get_device_by_mac(self, mac: str) -> Optional[Dict]:
        """Retrieve device profile by MAC address."""
        return self.db.get_device(mac)
    
    def list_all_devices(self) -> List[Dict]:
        """Retrieve all device profiles."""
        return self.db.get_all_devices()
