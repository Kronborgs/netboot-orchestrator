import os
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class FileService:
    """Service for managing OS installer files and iSCSI images."""
    
    def __init__(self, os_installers_path: str = "/data/os-installers", images_path: str = "/data/images"):
        self.os_installers_path = Path(os_installers_path)
        self.images_path = Path(images_path)
        
        logger.info(f"FileService initialized with OS installers path: {self.os_installers_path}")
        logger.info(f"FileService initialized with images path: {self.images_path}")
        
        # Create directories if they don't exist
        self.os_installers_path.mkdir(parents=True, exist_ok=True)
        self.images_path.mkdir(parents=True, exist_ok=True)
    
    def list_os_installer_files(self) -> Dict[str, Any]:
        """List all OS installer files in the directory."""
        files = []
        total_size = 0
        
        logger.info(f"Listing OS installer files from: {self.os_installers_path}")
        logger.info(f"Path exists: {self.os_installers_path.exists()}")
        logger.info(f"Path is directory: {self.os_installers_path.is_dir()}")
        
        try:
            if not self.os_installers_path.exists():
                logger.warning(f"OS installers path does not exist: {self.os_installers_path}")
                return {
                    "path": str(self.os_installers_path),
                    "files": [],
                    "total_size_bytes": 0,
                    "file_count": 0,
                    "warning": f"Path does not exist: {self.os_installers_path}"
                }
            
            for file_path in self.os_installers_path.rglob("*"):
                if file_path.is_file():
                    size = file_path.stat().st_size
                    total_size += size
                    files.append({
                        "filename": file_path.name,
                        "path": str(file_path.relative_to(self.os_installers_path)),
                        "size_bytes": size,
                        "created_at": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
                        "modified_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    })
            
            logger.info(f"Found {len(files)} files in {self.os_installers_path}")
        except Exception as e:
            logger.error(f"Error listing OS installer files: {str(e)}", exc_info=True)
            return {"error": str(e), "files": [], "total_size_bytes": 0}
        
        return {
            "path": str(self.os_installers_path),
            "files": sorted(files, key=lambda x: x["filename"]),
            "total_size_bytes": total_size,
            "file_count": len(files)
        }
    
    def list_images(self) -> Dict[str, Any]:
        """List all iSCSI disk images."""
        images = []
        total_size = 0
        
        try:
            for file_path in self.images_path.rglob("*"):
                if file_path.is_file():
                    size = file_path.stat().st_size
                    total_size += size
                    images.append({
                        "filename": file_path.name,
                        "path": str(file_path.relative_to(self.images_path)),
                        "size_bytes": size,
                        "size_gb": round(size / (1024**3), 2),
                        "created_at": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
                        "modified_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    })
        except Exception as e:
            return {"error": str(e), "images": [], "total_size_bytes": 0}
        
        return {
            "path": str(self.images_path),
            "images": sorted(images, key=lambda x: x["filename"]),
            "total_size_bytes": total_size,
            "total_size_gb": round(total_size / (1024**3), 2),
            "image_count": len(images)
        }
    
    def get_file_info(self, file_path: str, is_image: bool = False) -> Dict[str, Any]:
        """Get information about a specific file."""
        base_path = self.images_path if is_image else self.os_installers_path
        full_path = base_path / file_path
        
        if not full_path.exists() or not full_path.is_file():
            return {"error": "File not found"}
        
        try:
            stat = full_path.stat()
            return {
                "filename": full_path.name,
                "path": str(full_path.relative_to(base_path)),
                "size_bytes": stat.st_size,
                "size_gb": round(stat.st_size / (1024**3), 2),
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
        except Exception as e:
            return {"error": str(e)}
    
    def delete_file(self, file_path: str, is_image: bool = False) -> Dict[str, Any]:
        """Delete a file from the filesystem."""
        base_path = self.images_path if is_image else self.os_installers_path
        full_path = base_path / file_path
        
        if not full_path.exists():
            return {"error": "File not found", "success": False}
        
        if not full_path.is_file():
            return {"error": "Path is not a file", "success": False}
        
        try:
            full_path.unlink()
            return {"success": True, "message": f"File {file_path} deleted"}
        except Exception as e:
            return {"error": str(e), "success": False}
    
    def create_image_directory(self, image_name: str) -> Dict[str, Any]:
        """Create a new directory for an iSCSI image."""
        image_dir = self.images_path / image_name
        
        if image_dir.exists():
            return {"error": f"Image directory {image_name} already exists", "success": False}
        
        try:
            image_dir.mkdir(parents=True, exist_ok=True)
            return {
                "success": True,
                "path": str(image_dir.relative_to(self.images_path)),
                "created_at": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e), "success": False}
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage usage information."""
        os_size = sum(f.stat().st_size for f in self.os_installers_path.rglob("*") if f.is_file())
        images_size = sum(f.stat().st_size for f in self.images_path.rglob("*") if f.is_file())
        total_size = os_size + images_size
        
        return {
            "os_installers": {
                "size_bytes": os_size,
                "size_gb": round(os_size / (1024**3), 2),
                "path": str(self.os_installers_path)
            },
            "images": {
                "size_bytes": images_size,
                "size_gb": round(images_size / (1024**3), 2),
                "path": str(self.images_path)
            },
            "total": {
                "size_bytes": total_size,
                "size_gb": round(total_size / (1024**3), 2)
            }
        }
