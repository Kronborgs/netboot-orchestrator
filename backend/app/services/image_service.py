import subprocess
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from ..database import Database

logger = logging.getLogger(__name__)


class IscsiService:
    """Service for managing iSCSI images and targets using tgtd."""

    def __init__(self, images_path: str = "/iscsi-images"):
        self.images_path = Path(images_path)
        self.images_path.mkdir(parents=True, exist_ok=True)
        # Handle trailing spaces in env var names (Unraid quirk)
        self.boot_server_ip = (os.getenv("BOOT_SERVER_IP") or os.getenv("BOOT_SERVER_IP ") or "192.168.1.50").strip()
        self.iqn_prefix = "iqn.2024.netboot"
        self.db = Database()

    # ── helpers ──────────────────────────────────────────────

    def _run_cmd(self, cmd: list, timeout: int = 60) -> tuple:
        """Run a shell command and return (success, stdout, stderr)."""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)

    def _get_next_tid(self) -> int:
        """Get the next available target ID."""
        success, stdout, _ = self._run_cmd(
            ["tgtadm", "--lld", "iscsi", "--op", "show", "--mode", "target"]
        )
        if not success:
            return 1
        tids = []
        for line in stdout.splitlines():
            if line.startswith("Target "):
                try:
                    tid = int(line.split(":")[0].replace("Target ", ""))
                    tids.append(tid)
                except ValueError:
                    pass
        return max(tids) + 1 if tids else 1

    def _register_target(self, name: str, file_path: Path) -> tuple:
        """Register a file as a tgtd iSCSI target. Returns (tid, target_name, error)."""
        tid = self._get_next_tid()
        target_name = f"{self.iqn_prefix}:{name}"

        ok, _, err = self._run_cmd([
            "tgtadm", "--lld", "iscsi", "--op", "new",
            "--mode", "target", "--tid", str(tid),
            "--targetname", target_name,
        ])
        if not ok:
            return None, None, f"tgtadm new target failed: {err}"

        ok, _, err = self._run_cmd([
            "tgtadm", "--lld", "iscsi", "--op", "new",
            "--mode", "logicalunit", "--tid", str(tid),
            "--lun", "1", "--backing-store", str(file_path),
        ])
        if not ok:
            return None, None, f"tgtadm add LUN failed: {err}"

        ok, _, err = self._run_cmd([
            "tgtadm", "--lld", "iscsi", "--op", "bind",
            "--mode", "target", "--tid", str(tid), "-I", "ALL",
        ])
        if not ok:
            return None, None, f"tgtadm bind failed: {err}"

        return tid, target_name, None

    # ── CRUD operations ─────────────────────────────────────

    def create_image(self, name: str, size_gb: int) -> Dict:
        """Create a sparse iSCSI image file and register it as a tgtd target."""
        image_file = self.images_path / f"{name}.img"
        if image_file.exists():
            return {"success": False, "error": f"Image '{name}' already exists"}

        try:
            logger.info(f"Creating iSCSI image: {name} ({size_gb} GB)")
            ok, _, err = self._run_cmd(["truncate", "-s", f"{size_gb}G", str(image_file)])
            if not ok:
                return {"success": False, "error": f"Failed to create image file: {err}"}

            tid, target_name, err = self._register_target(name, image_file)
            if err:
                image_file.unlink(missing_ok=True)
                return {"success": False, "error": err}

            image_data = {
                "id": name,
                "name": name,
                "size_gb": size_gb,
                "device_type": "x64",
                "target_name": target_name,
                "tid": tid,
                "file_path": str(image_file),
                "assigned_to": None,
                "status": "available",
                "created_at": datetime.now().isoformat(),
            }
            self.db.create_image(name, image_data)
            logger.info(f"iSCSI image created: {name} (TID {tid}, {size_gb} GB)")
            return {"success": True, "image": image_data}
        except Exception as e:
            logger.error(f"Error creating iSCSI image: {e}")
            image_file.unlink(missing_ok=True)
            return {"success": False, "error": str(e)}

    def delete_image(self, name: str) -> Dict:
        """Delete an iSCSI image and its tgtd target."""
        image = self.db.get_image(name)
        image_file = self.images_path / f"{name}.img"

        if image and image.get("tid"):
            self._run_cmd([
                "tgtadm", "--lld", "iscsi", "--op", "delete",
                "--mode", "target", "--tid", str(image["tid"]), "--force",
            ])

        if image_file.exists():
            image_file.unlink()

        self.db.delete_image(name)
        return {"success": True, "message": f"Image '{name}' deleted"}

    def copy_image(self, source_name: str, dest_name: str) -> Dict:
        """Copy an existing iSCSI image to a new one and register it."""
        source_file = self.images_path / f"{source_name}.img"
        dest_file = self.images_path / f"{dest_name}.img"

        if not source_file.exists():
            return {"success": False, "error": f"Source image '{source_name}' not found"}
        if dest_file.exists():
            return {"success": False, "error": f"Destination '{dest_name}' already exists"}

        try:
            ok, _, err = self._run_cmd(
                ["cp", "--sparse=auto", str(source_file), str(dest_file)],
                timeout=600,
            )
            if not ok:
                return {"success": False, "error": f"Copy failed: {err}"}

            size_gb = round(dest_file.stat().st_size / (1024 ** 3))
            tid, target_name, err = self._register_target(dest_name, dest_file)
            if err:
                dest_file.unlink(missing_ok=True)
                return {"success": False, "error": err}

            image_data = {
                "id": dest_name,
                "name": dest_name,
                "size_gb": size_gb,
                "device_type": "x64",
                "target_name": target_name,
                "tid": tid,
                "file_path": str(dest_file),
                "assigned_to": None,
                "status": "available",
                "copied_from": source_name,
                "created_at": datetime.now().isoformat(),
            }
            self.db.create_image(dest_name, image_data)
            return {"success": True, "image": image_data}
        except Exception as e:
            dest_file.unlink(missing_ok=True)
            return {"success": False, "error": str(e)}

    # ── link / unlink ───────────────────────────────────────

    def link_device(self, image_name: str, mac: str) -> Dict:
        """Link a device to an iSCSI image."""
        image = self.db.get_image(image_name)
        if not image:
            return {"success": False, "error": f"Image '{image_name}' not found"}
        if image.get("assigned_to") and image["assigned_to"] != mac:
            return {"success": False, "error": f"Image already assigned to {image['assigned_to']}"}

        self.db.update_image(image_name, {"assigned_to": mac, "status": "linked"})

        device = self.db.get_device(mac)
        if device:
            self.db.update_device(mac, {"image_id": image_name})
        else:
            self.db.create_device(mac, {
                "mac": mac,
                "device_type": "x64",
                "name": f"Device-{mac[-5:].replace(':', '')}",
                "enabled": True,
                "image_id": image_name,
            })

        return {
            "success": True,
            "message": f"Device {mac} linked to image '{image_name}'",
            "target_name": image.get("target_name", f"{self.iqn_prefix}:{image_name}"),
            "server_ip": self.boot_server_ip,
        }

    def unlink_device(self, mac: str) -> Dict:
        """Unlink a device from its iSCSI image."""
        for img in self.db.get_all_images():
            if img.get("assigned_to") == mac:
                self.db.update_image(img["id"], {"assigned_to": None, "status": "available"})
                break
        self.db.update_device(mac, {"image_id": None})
        return {"success": True, "message": f"Device {mac} unlinked"}

    # ── queries ─────────────────────────────────────────────

    def list_images(self) -> List[Dict]:
        """List all iSCSI images enriched with filesystem info."""
        db_images = self.db.get_all_images()

        for img in db_images:
            fp = self.images_path / f"{img['id']}.img"
            if fp.exists():
                st = fp.stat()
                img["actual_size_bytes"] = st.st_size
                img["actual_size_gb"] = round(st.st_size / (1024 ** 3), 2)
                img["file_exists"] = True
            else:
                img["file_exists"] = False

        # discover orphan .img files not tracked in db
        if self.images_path.exists():
            known_ids = {img["id"] for img in db_images}
            for f in self.images_path.glob("*.img"):
                if f.stem not in known_ids:
                    st = f.stat()
                    db_images.append({
                        "id": f.stem,
                        "name": f.stem,
                        "size_gb": round(st.st_size / (1024 ** 3), 2),
                        "actual_size_bytes": st.st_size,
                        "actual_size_gb": round(st.st_size / (1024 ** 3), 2),
                        "file_exists": True,
                        "file_path": str(f),
                        "assigned_to": None,
                        "status": "unregistered",
                        "created_at": datetime.fromtimestamp(st.st_ctime).isoformat(),
                    })
        return db_images

    def get_image(self, name: str) -> Optional[Dict]:
        return self.db.get_image(name)

    def get_san_boot_url(self, image_name: str) -> str:
        """Return the iPXE SAN boot URL for an image."""
        return f"iscsi:{self.boot_server_ip}::::{self.iqn_prefix}:{image_name}"

    # ── startup ─────────────────────────────────────────────

    def restore_targets(self):
        """Re-register all known images as tgtd targets on startup."""
        images = self.db.get_all_images()
        for img in images:
            fp = Path(img.get("file_path", str(self.images_path / f"{img['id']}.img")))
            if not fp.exists():
                logger.warning(f"Image file missing for {img['id']}: {fp}")
                continue
            tid, target_name, err = self._register_target(img["id"], fp)
            if err:
                logger.error(f"Failed to restore target {img['id']}: {err}")
                continue
            self.db.update_image(img["id"], {"tid": tid, "target_name": target_name})
            logger.info(f"Restored iSCSI target: {target_name} (TID {tid})")
