import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from zoneinfo import ZoneInfo


class Database:
    def __init__(self, data_path: str = "/data"):
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        self.profiles_file = self.data_path / "profiles.json"
        self.images_file = self.data_path / "images.json"
        self.os_file = self.data_path / "os.json"
        self.settings_file = self.data_path / "settings.json"
        self.unknown_devices_file = self.data_path / "unknown_devices.json"
        self.boot_logs_file = self.data_path / "boot_logs.json"
        self.device_transfer_file = self.data_path / "device_transfer.json"
        
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
        if not self.unknown_devices_file.exists():
            self._write_json(self.unknown_devices_file, {})
        if not self.boot_logs_file.exists():
            self._write_json(self.boot_logs_file, [])
        if not self.device_transfer_file.exists():
            self._write_json(self.device_transfer_file, {})
    
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

    @staticmethod
    def _now_iso() -> str:
        tz_name = (os.getenv("TZ") or os.getenv("TZ ") or "").strip()
        if tz_name:
            try:
                return datetime.now(ZoneInfo(tz_name)).isoformat()
            except Exception:
                pass
        return datetime.now().astimezone().isoformat()
    
    # Device/Profile operations
    def get_device(self, mac: str) -> Optional[Dict]:
        profiles = self._read_json(self.profiles_file)
        return profiles.get(mac)
    
    def get_all_devices(self) -> List[Dict]:
        profiles = self._read_json(self.profiles_file)
        return list(profiles.values())
    
    def create_device(self, mac: str, device_data: Dict) -> Dict:
        profiles = self._read_json(self.profiles_file)
        profiles[mac] = {**device_data, "mac": mac, "created_at": self._now_iso()}
        self._write_json(self.profiles_file, profiles)
        return profiles[mac]
    
    def update_device(self, mac: str, device_data: Dict) -> Optional[Dict]:
        profiles = self._read_json(self.profiles_file)
        if mac in profiles:
            profiles[mac].update(device_data)
            profiles[mac]["updated_at"] = self._now_iso()
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
        images[image_id] = {**image_data, "id": image_id, "created_at": self._now_iso()}
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
    
    # Unknown device operations
    def record_unknown_device(self, mac: str, device_type: str = None) -> Dict:
        """Record a device that booted but is not registered."""
        unknown = self._read_json(self.unknown_devices_file)
        unknown[mac] = {
            "mac": mac,
            "device_type": device_type,
            "boot_time": self._now_iso(),
            "status": "unknown"
        }
        self._write_json(self.unknown_devices_file, unknown)
        return unknown[mac]
    
    def get_unknown_device(self, mac: str) -> Optional[Dict]:
        """Get an unknown device by MAC address."""
        unknown = self._read_json(self.unknown_devices_file)
        return unknown.get(mac)
    
    def get_all_unknown_devices(self) -> List[Dict]:
        """List all unknown devices."""
        unknown = self._read_json(self.unknown_devices_file)
        return list(unknown.values())
    
    def remove_unknown_device(self, mac: str) -> bool:
        """Remove an unknown device from the list."""
        unknown = self._read_json(self.unknown_devices_file)
        if mac in unknown:
            del unknown[mac]
            self._write_json(self.unknown_devices_file, unknown)
            return True
        return False

    # Boot log operations
    def add_boot_log(self, mac: str, event: str, details: str = "", ip: str = "") -> Dict:
        """Record a boot event."""
        logs = self._read_json(self.boot_logs_file)
        if not isinstance(logs, list):
            logs = []
        entry = {
            "mac": mac,
            "event": event,
            "details": details,
            "ip": ip,
            "timestamp": self._now_iso(),
        }
        logs.append(entry)
        # Keep last 500 log entries
        if len(logs) > 500:
            logs = logs[-500:]
        self._write_json(self.boot_logs_file, logs)
        return entry

    def get_boot_logs(self, mac: str = None, limit: int = 100) -> List[Dict]:
        """Get boot logs, optionally filtered by MAC."""
        logs = self._read_json(self.boot_logs_file)
        if not isinstance(logs, list):
            return []
        if mac:
            logs = [l for l in logs if l.get("mac") == mac]
        return list(reversed(logs[-limit:]))

    @staticmethod
    def _normalize_mac(mac: str) -> str:
        return (mac or "").strip().lower()

    def add_device_transfer(
        self,
        mac: str,
        protocol: str,
        bytes_sent: int,
        path: str = "",
        remote_ip: str = "",
    ) -> Dict:
        """Accumulate per-device transfer counters (best effort telemetry)."""
        key = self._normalize_mac(mac)
        if not key:
            return {}

        data = self._read_json(self.device_transfer_file)
        if not isinstance(data, dict):
            data = {}

        existing = data.get(key, {
            "mac": key,
            "http_tx_bytes": 0,
            "http_requests": 0,
            "iscsi_tx_bytes": 0,
            "iscsi_requests": 0,
            "last_path": "",
            "last_remote_ip": "",
            "last_protocol": "",
            "first_seen": self._now_iso(),
            "last_seen": self._now_iso(),
        })

        proto = (protocol or "").strip().lower()
        if proto == "iscsi":
            existing["iscsi_tx_bytes"] = int(existing.get("iscsi_tx_bytes", 0)) + max(int(bytes_sent or 0), 0)
            existing["iscsi_requests"] = int(existing.get("iscsi_requests", 0)) + 1
        else:
            existing["http_tx_bytes"] = int(existing.get("http_tx_bytes", 0)) + max(int(bytes_sent or 0), 0)
            existing["http_requests"] = int(existing.get("http_requests", 0)) + 1

        existing["last_path"] = path or existing.get("last_path", "")
        existing["last_remote_ip"] = remote_ip or existing.get("last_remote_ip", "")
        existing["last_protocol"] = proto or existing.get("last_protocol", "")
        existing["last_seen"] = self._now_iso()

        data[key] = existing
        self._write_json(self.device_transfer_file, data)
        return existing

    def get_device_transfer(self, mac: str) -> Dict:
        """Get accumulated transfer counters for a specific device MAC."""
        key = self._normalize_mac(mac)
        if not key:
            return {}
        data = self._read_json(self.device_transfer_file)
        if not isinstance(data, dict):
            return {}
        return data.get(key, {})
