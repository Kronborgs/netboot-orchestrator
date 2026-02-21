import os
import logging
import threading
import time
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
    WATCHDOG_AVAILABLE = True
except Exception:
    FileSystemEventHandler = object
    Observer = None
    WATCHDOG_AVAILABLE = False

logger = logging.getLogger(__name__)


class FileService:
    """Service for managing OS installer files and iSCSI images."""

    _CACHE: Dict[str, Dict[str, Any]] = {}
    _CACHE_LOCK = threading.Lock()
    _REFRESHING_KEYS = set()
    _SYNC_THREAD = None
    _SYNC_STOP_EVENT = threading.Event()
    _CACHE_TTL_SECONDS = 15
    _WATCHDOG_AVAILABLE = WATCHDOG_AVAILABLE
    _WATCH_OBSERVER = None
    _LAST_EVENT_AT: Dict[str, float] = {}
    _WATCH_DEBOUNCE_SECONDS = 2
    
    def __init__(self, os_installers_path: str = "/data/os-installers", images_path: str = "/data/images"):
        self.os_installers_path = Path(os_installers_path)
        self.images_path = Path(images_path)
        
        logger.info(f"FileService initialized with OS installers path: {self.os_installers_path}")
        logger.info(f"FileService initialized with images path: {self.images_path}")
        
        # Create directories if they don't exist
        self.os_installers_path.mkdir(parents=True, exist_ok=True)
        self.images_path.mkdir(parents=True, exist_ok=True)

    def _cache_key(self) -> str:
        return f"{self.os_installers_path.resolve()}::{self.images_path.resolve()}"

    @classmethod
    def _refresh_cache_for_paths(cls, os_installers_path: Path, images_path: Path, key: str) -> None:
        os_data = cls._scan_os_installer_files(os_installers_path)
        storage_data = cls._scan_storage_info(os_installers_path, images_path)
        with cls._CACHE_LOCK:
            cls._CACHE[key] = {
                "os_installers": os_data,
                "storage": storage_data,
                "updated_at": time.time(),
            }
            folder_prefix_os = f"{key}::os::folder::"
            folder_prefix_images = f"{key}::images::folder::"
            keys_to_remove = [
                cache_key
                for cache_key in cls._CACHE.keys()
                if cache_key.startswith(folder_prefix_os) or cache_key.startswith(folder_prefix_images)
            ]
            for cache_key in keys_to_remove:
                cls._CACHE.pop(cache_key, None)

    def _trigger_async_refresh(self) -> None:
        key = self._cache_key()
        with self._CACHE_LOCK:
            if key in self._REFRESHING_KEYS:
                return
            self._REFRESHING_KEYS.add(key)

        def _worker():
            try:
                self._refresh_cache_for_paths(self.os_installers_path, self.images_path, key)
            finally:
                with self._CACHE_LOCK:
                    self._REFRESHING_KEYS.discard(key)

        threading.Thread(target=_worker, daemon=True).start()

    def invalidate_cache(self) -> None:
        key = self._cache_key()
        with self._CACHE_LOCK:
            self._CACHE.pop(key, None)
            keys_to_remove = [k for k in self._CACHE.keys() if k.startswith(f"{key}::")]
            for k in keys_to_remove:
                self._CACHE.pop(k, None)

    @classmethod
    def start_background_sync(cls, os_installers_path: str, images_path: str, interval_seconds: int = 15) -> None:
        os_path = Path(os_installers_path)
        img_path = Path(images_path)
        key = f"{os_path.resolve()}::{img_path.resolve()}"

        cls._SYNC_STOP_EVENT.clear()
        interval_seconds = max(5, interval_seconds)

        cls._trigger_refresh_for_key(key, os_path, img_path, force=True)
        cls._start_filesystem_watcher(key, os_path, img_path)

        if cls._SYNC_THREAD and cls._SYNC_THREAD.is_alive():
            return

        def _sync_loop():
            while not cls._SYNC_STOP_EVENT.is_set():
                try:
                    cls._trigger_refresh_for_key(key, os_path, img_path, force=True)
                except Exception as e:
                    logger.warning(f"Background file cache sync failed: {e}")
                cls._SYNC_STOP_EVENT.wait(interval_seconds)

        cls._SYNC_THREAD = threading.Thread(target=_sync_loop, daemon=True)
        cls._SYNC_THREAD.start()
        logger.info(f"FileService background sync started (every {interval_seconds}s)")

    @classmethod
    def stop_background_sync(cls) -> None:
        cls._SYNC_STOP_EVENT.set()

        if cls._SYNC_THREAD and cls._SYNC_THREAD.is_alive():
            cls._SYNC_THREAD.join(timeout=2)
        cls._SYNC_THREAD = None

        if cls._WATCH_OBSERVER:
            try:
                cls._WATCH_OBSERVER.stop()
                cls._WATCH_OBSERVER.join(timeout=2)
            except Exception as e:
                logger.warning(f"Failed to stop filesystem watcher cleanly: {e}")
            cls._WATCH_OBSERVER = None

    @classmethod
    def _trigger_refresh_for_key(cls, key: str, os_path: Path, img_path: Path, force: bool = False) -> None:
        now = time.time()
        with cls._CACHE_LOCK:
            if key in cls._REFRESHING_KEYS:
                return
            last_event = cls._LAST_EVENT_AT.get(key, 0)
            if not force and (now - last_event) < cls._WATCH_DEBOUNCE_SECONDS:
                return
            cls._REFRESHING_KEYS.add(key)
            cls._LAST_EVENT_AT[key] = now

        def _worker():
            try:
                cls._refresh_cache_for_paths(os_path, img_path, key)
            except Exception as e:
                logger.warning(f"File cache refresh failed for {key}: {e}")
            finally:
                with cls._CACHE_LOCK:
                    cls._REFRESHING_KEYS.discard(key)

        threading.Thread(target=_worker, daemon=True).start()

    @classmethod
    def _start_filesystem_watcher(cls, key: str, os_path: Path, img_path: Path) -> None:
        if not cls._WATCHDOG_AVAILABLE:
            logger.info("Filesystem watcher unavailable (watchdog not installed); using interval sync only")
            return

        if cls._WATCH_OBSERVER and cls._WATCH_OBSERVER.is_alive():
            return

        for watch_path in (os_path, img_path):
            watch_path.mkdir(parents=True, exist_ok=True)

        class _PathChangeHandler(FileSystemEventHandler):
            def on_any_event(self, event):
                if cls._SYNC_STOP_EVENT.is_set():
                    return
                cls._trigger_refresh_for_key(key, os_path, img_path)

        observer = Observer()
        handler = _PathChangeHandler()
        observer.schedule(handler, str(os_path), recursive=True)
        observer.schedule(handler, str(img_path), recursive=True)
        observer.daemon = True
        observer.start()
        cls._WATCH_OBSERVER = observer
        logger.info("FileService filesystem watcher started")

    @staticmethod
    def _scan_os_installer_files(os_installers_path: Path) -> Dict[str, Any]:
        """Raw filesystem scan of bootable OS installer files."""
        bootable_extensions = {
            '.iso', '.img', '.bin', '.efi', '.exe',
            '.vhd', '.vhdx', '.qcow2', '.vmdk', '.raw',
            '.wim'
        }

        files = []
        total_size = 0

        logger.info(f"Listing bootable OS installer files from: {os_installers_path}")
        logger.info(f"Path exists: {os_installers_path.exists()}")
        logger.info(f"Path is directory: {os_installers_path.is_dir()}")

        try:
            if not os_installers_path.exists():
                logger.warning(f"OS installers path does not exist: {os_installers_path}")
                return {
                    "path": str(os_installers_path),
                    "files": [],
                    "total_size_bytes": 0,
                    "file_count": 0,
                    "warning": f"Path does not exist: {os_installers_path}"
                }

            for file_path in os_installers_path.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in bootable_extensions:
                    size = file_path.stat().st_size
                    total_size += size
                    files.append({
                        "filename": file_path.name,
                        "path": str(file_path.relative_to(os_installers_path)),
                        "size_bytes": size,
                        "size_display": FileService._format_bytes(size),
                        "created_at": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
                        "modified_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    })

            logger.info(f"Found {len(files)} bootable files in {os_installers_path}")
        except Exception as e:
            logger.error(f"Error listing OS installer files: {str(e)}", exc_info=True)
            return {"error": str(e), "files": [], "total_size_bytes": 0}

        return {
            "path": str(os_installers_path),
            "files": sorted(files, key=lambda x: x["filename"]),
            "total_size_bytes": total_size,
            "file_count": len(files)
        }

    @staticmethod
    def _scan_storage_info(os_installers_path: Path, images_path: Path) -> Dict[str, Any]:
        """Raw filesystem scan for storage usage."""
        try:
            os_size = 0
            images_size = 0

            if os_installers_path.exists():
                try:
                    os_size = sum(f.stat().st_size for f in os_installers_path.rglob("*") if f.is_file())
                except Exception as e:
                    logger.warning(f"Failed to calculate OS installers size: {e}")
                    os_size = 0

            if images_path.exists():
                try:
                    images_size = sum(f.stat().st_size for f in images_path.rglob("*") if f.is_file())
                except Exception as e:
                    logger.warning(f"Failed to calculate images size: {e}")
                    images_size = 0

            total_size = os_size + images_size

            return {
                "os_installers": {
                    "size_bytes": os_size,
                    "size_gb": round(os_size / (1024**3), 2) if os_size > 0 else 0,
                    "path": str(os_installers_path)
                },
                "images": {
                    "size_bytes": images_size,
                    "size_gb": round(images_size / (1024**3), 2) if images_size > 0 else 0,
                    "path": str(images_path)
                },
                "total": {
                    "size_bytes": total_size,
                    "size_gb": round(total_size / (1024**3), 2) if total_size > 0 else 0
                }
            }
        except Exception as e:
            logger.error(f"Error getting storage info: {e}")
            return {
                "os_installers": {"size_bytes": 0, "size_gb": 0, "path": str(os_installers_path)},
                "images": {"size_bytes": 0, "size_gb": 0, "path": str(images_path)},
                "total": {"size_bytes": 0, "size_gb": 0}
            }
    
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
        """Get contents of a specific folder (lazy loading + cache)."""
        base_path = self.images_path if is_images else self.os_installers_path

        cache_key = f"{self._cache_key()}::{'images' if is_images else 'os'}::folder::{folder_path}"
        now = time.time()
        with self._CACHE_LOCK:
            cached = self._CACHE.get(cache_key)
            if cached:
                age = now - cached.get("updated_at", 0)
                if age <= self._CACHE_TTL_SECONDS:
                    return cached.get("data", {})
                self._CACHE.pop(cache_key, None)
        
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
                    # Fast directory metrics (non-recursive, avoids expensive rglob scans)
                    dir_size = 0
                    has_children = False
                    try:
                        for child in item.iterdir():
                            has_children = True
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
                        "has_children": has_children
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
            
            result = {
                "path": folder_path,
                "items": items,
                "breadcrumb": breadcrumb,
                "total_size_bytes": total_size,
                "total_size_display": self._format_bytes(total_size),
                "item_count": len(items)
            }
            with self._CACHE_LOCK:
                self._CACHE[cache_key] = {"data": result, "updated_at": time.time()}
            return result
        except Exception as e:
            logger.error(f"Error getting folder contents: {e}")
            return {
                "error": str(e),
                "path": folder_path,
                "items": [],
                "breadcrumb": []
            }
    
    def list_os_installer_files(self) -> Dict[str, Any]:
        """List OS installer files quickly using cache + background sync."""
        key = self._cache_key()
        now = time.time()

        with self._CACHE_LOCK:
            cache_entry = self._CACHE.get(key)

        if cache_entry:
            age = now - cache_entry.get("updated_at", 0)
            if age > self._CACHE_TTL_SECONDS:
                self._trigger_async_refresh()
            return cache_entry.get("os_installers", {"files": [], "file_count": 0})

        self._refresh_cache_for_paths(self.os_installers_path, self.images_path, key)
        with self._CACHE_LOCK:
            return self._CACHE.get(key, {}).get("os_installers", {"files": [], "file_count": 0})
    
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
        """Get storage usage quickly using cache + background sync."""
        key = self._cache_key()
        now = time.time()

        with self._CACHE_LOCK:
            cache_entry = self._CACHE.get(key)

        if cache_entry:
            age = now - cache_entry.get("updated_at", 0)
            if age > self._CACHE_TTL_SECONDS:
                self._trigger_async_refresh()
            return cache_entry.get("storage", {"total": {"size_gb": 0}})

        self._refresh_cache_for_paths(self.os_installers_path, self.images_path, key)
        with self._CACHE_LOCK:
            return self._CACHE.get(key, {}).get("storage", {"total": {"size_gb": 0}})
