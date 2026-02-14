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


class BootCheckIn(BaseModel):
    mac: str
    device_type: DeviceType
    action: str  # "boot_default", "show_menu", "boot_image"
    image_id: Optional[str] = None
    kernel_set: str = "default"
