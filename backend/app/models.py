from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class DeviceType(str, Enum):
    RASPI = "raspi"
    X86 = "x86"
    X64 = "x64"


class Device(BaseModel):
    mac: str
    device_type: DeviceType
    name: str
    enabled: bool = True
    image_id: Optional[str] = None
    kernel_set: str = "default"


class Image(BaseModel):
    id: str
    name: str
    size_gb: float
    device_type: DeviceType
    assigned_to: Optional[str] = None
    created_at: str


class KernelSet(BaseModel):
    name: str
    kernel_url: str
    initramfs_url: Optional[str] = None
    is_default: bool = False


class OSInstaller(BaseModel):
    name: str
    path: str
    kernel: str
    initrd: str
    kernel_cmdline: str
    device_type: DeviceType


class OSInstallerFile(BaseModel):
    """Represents an OS installer file in the filesystem."""
    filename: str
    path: str
    size_bytes: int
    device_type: DeviceType
    created_at: str


class OSInstallerDirectory(BaseModel):
    """Represents available OS installer directory contents."""
    path: str
    files: List[OSInstallerFile]
    total_size_bytes: int


class FileUploadProgress(BaseModel):
    """Track file upload progress."""
    filename: str
    progress_percent: int
    uploaded_bytes: int
    total_bytes: int
    status: str  # "uploading", "completed", "failed"


class UnknownDevice(BaseModel):
    """Represents a device detected during boot but not registered."""
    mac: str
    device_type: Optional[DeviceType] = None
    boot_time: str
    status: str  # "unknown", "registered", "assigned"


class DeviceAssignment(BaseModel):
    """Assignment of iSCSI image and OS to a device."""
    mac: str
    image_id: Optional[str] = None
    os_installer: Optional[str] = None
    installation_target: str  # "iscsi" or "local"
    status: str  # "pending", "installing", "completed"


class BootCheckIn(BaseModel):
    mac: str
    device_type: DeviceType
    action: str  # "boot_default", "show_menu", "boot_image"
    image_id: Optional[str] = None
    kernel_set: str = "default"
