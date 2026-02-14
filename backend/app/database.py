import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


class Database:
    def __init__(self, data_path: str = "/data"):
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        self.profiles_file = self.data_path / "profiles.json"
        self.images_file = self.data_path / "images.json"
        self.os_file = self.data_path / "os.json"
        self.settings_file = self.data_path / "settings.json"
        
        # Initialize files if they don't exist
        self._init_files()
    
    def _init_files(self):
        """Initialize JSON files with empty structures if they don't exist."""
        if not self.profiles_file.exists():
            self._write_json(self.profiles_file, {})
        if not self.images_file.exists():
            self._write_json(self.images_file, {})
        if not self.os_file.exists():
            self._write_json(self.os_file, {})
        if not self.settings_file.exists():
            self._write_json(self.settings_file, {"kernel_sets": {"default": {"kernel_url": "", "initramfs_url": ""}}})
    
    def _read_json(self, file_path: Path) -> Dict[str, Any]:
        """Read JSON file safely."""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _write_json(self, file_path: Path, data: Dict[str, Any]):
        """Write JSON file safely."""
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    # Device/Profile operations
    def get_device(self, mac: str) -> Optional[Dict]:
        profiles = self._read_json(self.profiles_file)
        return profiles.get(mac)
    
    def get_all_devices(self) -> List[Dict]:
        profiles = self._read_json(self.profiles_file)
        return list(profiles.values())
    
    def create_device(self, mac: str, device_data: Dict) -> Dict:
        profiles = self._read_json(self.profiles_file)
        profiles[mac] = {**device_data, "mac": mac, "created_at": datetime.now().isoformat()}
        self._write_json(self.profiles_file, profiles)
        return profiles[mac]
    
    def update_device(self, mac: str, device_data: Dict) -> Optional[Dict]:
        profiles = self._read_json(self.profiles_file)
        if mac in profiles:
            profiles[mac].update(device_data)
            profiles[mac]["updated_at"] = datetime.now().isoformat()
            self._write_json(self.profiles_file, profiles)
            return profiles[mac]
        return None
    
    def delete_device(self, mac: str) -> bool:
        profiles = self._read_json(self.profiles_file)
        if mac in profiles:
            del profiles[mac]
            self._write_json(self.profiles_file, profiles)
            return True
        return False
    
    # Image operations
    def get_image(self, image_id: str) -> Optional[Dict]:
        images = self._read_json(self.images_file)
        return images.get(image_id)
    
    def get_all_images(self) -> List[Dict]:
        images = self._read_json(self.images_file)
        return list(images.values())
    
    def create_image(self, image_id: str, image_data: Dict) -> Dict:
        images = self._read_json(self.images_file)
        images[image_id] = {**image_data, "id": image_id, "created_at": datetime.now().isoformat()}
        self._write_json(self.images_file, images)
        return images[image_id]
    
    def update_image(self, image_id: str, image_data: Dict) -> Optional[Dict]:
        images = self._read_json(self.images_file)
        if image_id in images:
            images[image_id].update(image_data)
            self._write_json(self.images_file, images)
            return images[image_id]
        return None
    
    def delete_image(self, image_id: str) -> bool:
        images = self._read_json(self.images_file)
        if image_id in images:
            del images[image_id]
            self._write_json(self.images_file, images)
            return True
        return False
    
    # OS Installer operations
    def get_os_installer(self, name: str) -> Optional[Dict]:
        os_data = self._read_json(self.os_file)
        return os_data.get(name)
    
    def get_all_os_installers(self) -> List[Dict]:
        os_data = self._read_json(self.os_file)
        return list(os_data.values())
    
    def create_os_installer(self, name: str, installer_data: Dict) -> Dict:
        os_data = self._read_json(self.os_file)
        os_data[name] = {**installer_data, "name": name}
        self._write_json(self.os_file, os_data)
        return os_data[name]
    
    # Settings/Kernel sets
    def get_kernel_set(self, name: str) -> Optional[Dict]:
        settings = self._read_json(self.settings_file)
        kernel_sets = settings.get("kernel_sets", {})
        return kernel_sets.get(name)
    
    def get_all_kernel_sets(self) -> Dict:
        settings = self._read_json(self.settings_file)
        return settings.get("kernel_sets", {})
    
    def create_kernel_set(self, name: str, kernel_data: Dict):
        settings = self._read_json(self.settings_file)
        if "kernel_sets" not in settings:
            settings["kernel_sets"] = {}
        settings["kernel_sets"][name] = kernel_data
        self._write_json(self.settings_file, settings)
        return settings["kernel_sets"][name]
