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
    
    def _build_folder_tree(self, folder_path: Path, base_path: Path) -> Dict[str, Any]:
        """Recursively build folder tree structure."""
        tree = {
            "name": folder_path.name or folder_path.as_posix(),
            "type": "folder",
            "path": str(folder_path.relative_to(base_path)) if folder_path != base_path else "",
            "children": [],
            "size_bytes": 0
        }
        
        try:
            for item in sorted(folder_path.iterdir(), key=lambda x: (x.is_file(), x.name)):
                if item.is_dir():
                    subtree = self._build_folder_tree(item, base_path)
                    tree["children"].append(subtree)
                    tree["size_bytes"] += subtree["size_bytes"]
                elif item.is_file():
                    stat = item.stat()
                    size = stat.st_size
                    tree["children"].append({
                        "name": item.name,
                        "type": "file",
                        "path": str(item.relative_to(base_path)),
                        "size_bytes": size,
                        "size_display": self._format_bytes(size),
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
                    tree["size_bytes"] += size
        except PermissionError:
            logger.warning(f"Permission denied accessing folder: {folder_path}")
        
        return tree
    
    @staticmethod
    def _format_bytes(bytes_value: int) -> str:
        """Format bytes to human readable format."""
        for size_name in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {size_name}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
    
    def get_folder_tree(self, is_images: bool = False) -> Dict[str, Any]:
        """Get folder structure as a tree."""
        base_path = self.images_path if is_images else self.os_installers_path
        
        if not base_path.exists():
            return {
                "error": f"Path does not exist: {base_path}",
                "path": str(base_path),
                "tree": None
            }
        
        try:
            tree = self._build_folder_tree(base_path, base_path)
            return {
                "path": str(base_path),
                "tree": tree,
                "total_size_bytes": tree["size_bytes"],
                "total_size_display": self._format_bytes(tree["size_bytes"])
            }
        except Exception as e:
            logger.error(f"Error building folder tree: {e}")
            return {
                "error": str(e),
                "path": str(base_path),
                "tree": None
            }
    
    def get_folder_contents(self, folder_path: str = "", is_images: bool = False) -> Dict[str, Any]:
        """Get contents of a specific folder (lazy loading)."""
        base_path = self.images_path if is_images else self.os_installers_path
        
        if folder_path:
            full_path = base_path / folder_path
        else:
            full_path = base_path
        
        if not full_path.exists() or not full_path.is_dir():
            return {
                "error": f"Folder not found: {full_path}",
                "path": folder_path,
                "items": [],
                "breadcrumb": []
            }
        
        try:
            items = []
            total_size = 0
            
            for item in sorted(full_path.iterdir(), key=lambda x: (x.is_file(), x.name)):
                stat = item.stat()
                size = stat.st_size
                rel_path = str(item.relative_to(base_path))
                
                if item.is_dir():
                    # For directories, only count immediate children
                    dir_size = 0
                    try:
                        for child in item.rglob("*"):
                            if child.is_file():
                                dir_size += child.stat().st_size
                    except PermissionError:
                        pass
                    
                    items.append({
                        "name": item.name,
                        "type": "folder",
                        "path": rel_path,
                        "size_bytes": dir_size,
                        "size_display": self._format_bytes(dir_size),
                        "has_children": len(list(item.iterdir())) > 0
                    })
                    total_size += dir_size
                else:
                    items.append({
                        "name": item.name,
                        "type": "file",
                        "path": rel_path,
                        "size_bytes": size,
                        "size_display": self._format_bytes(size),
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
                    total_size += size
            
            # Build breadcrumb
            breadcrumb = []
            if folder_path:
                breadcrumb.append({"name": "📁 Root", "path": ""})
                parts = folder_path.split("/")
                for i, part in enumerate(parts):
                    breadcrumb.append({
                        "name": part,
                        "path": "/".join(parts[:i+1])
                    })
            else:
                breadcrumb.append({"name": "📁 Root", "path": ""})
            
            return {
                "path": folder_path,
                "items": items,
                "breadcrumb": breadcrumb,
                "total_size_bytes": total_size,
                "total_size_display": self._format_bytes(total_size),
                "item_count": len(items)
            }
        except Exception as e:
            logger.error(f"Error getting folder contents: {e}")
            return {
                "error": str(e),
                "path": folder_path,
                "items": [],
                "breadcrumb": []
            }
    
    def list_os_installer_files(self) -> Dict[str, Any]:
        """List OS installer files that are bootable (ISO, IMG, BIN, EFI, etc.)."""
        # Only show bootable file extensions
        bootable_extensions = {
            '.iso', '.img', '.bin', '.efi', '.exe',
            '.vhd', '.vhdx', '.qcow2', '.vmdk', '.raw',
            '.wim'  # Windows Imaging Format
        }
        
        files = []
        total_size = 0
        
        logger.info(f"Listing bootable OS installer files from: {self.os_installers_path}")
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
                if file_path.is_file() and file_path.suffix.lower() in bootable_extensions:
                    size = file_path.stat().st_size
                    total_size += size
                    files.append({
                        "filename": file_path.name,
                        "path": str(file_path.relative_to(self.os_installers_path)),
                        "size_bytes": size,
                        "size_display": self._format_bytes(size),
                        "created_at": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
                        "modified_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    })
            
            logger.info(f"Found {len(files)} bootable files in {self.os_installers_path}")
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
        try:
            # Quick size calculation with timeout handling
            os_size = 0
            images_size = 0
            
            # Count files and estimate size (don't block on network I/O)
            if self.os_installers_path.exists():
                try:
                    os_size = sum(f.stat().st_size for f in self.os_installers_path.rglob("*") if f.is_file())
                except Exception as e:
                    logger.warning(f"Failed to calculate OS installers size: {e}")
                    os_size = 0
            
            if self.images_path.exists():
                try:
                    images_size = sum(f.stat().st_size for f in self.images_path.rglob("*") if f.is_file())
                except Exception as e:
                    logger.warning(f"Failed to calculate images size: {e}")
                    images_size = 0
            
            total_size = os_size + images_size
            
            return {
                "os_installers": {
                    "size_bytes": os_size,
                    "size_gb": round(os_size / (1024**3), 2) if os_size > 0 else 0,
                    "path": str(self.os_installers_path)
                },
                "images": {
                    "size_bytes": images_size,
                    "size_gb": round(images_size / (1024**3), 2) if images_size > 0 else 0,
                    "path": str(self.images_path)
                },
                "total": {
                    "size_bytes": total_size,
                    "size_gb": round(total_size / (1024**3), 2) if total_size > 0 else 0
                }
            }
        except Exception as e:
            logger.error(f"Error getting storage info: {e}")
            # Return minimal response to avoid blocking UI
            return {
                "os_installers": {"size_bytes": 0, "size_gb": 0, "path": str(self.os_installers_path)},
                "images": {"size_bytes": 0, "size_gb": 0, "path": str(self.images_path)},
                "total": {"size_bytes": 0, "size_gb": 0}
            }
