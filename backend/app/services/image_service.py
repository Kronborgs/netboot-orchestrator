import subprocess
import os
import logging
import re
import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple
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

    def _get_tid_by_target_name(self, target_name: str) -> Optional[int]:
        """Find existing TID for a target name, if present."""
        success, stdout, _ = self._run_cmd(
            ["tgtadm", "--lld", "iscsi", "--op", "show", "--mode", "target"]
        )
        if not success:
            return None

        current_tid = None
        for line in stdout.splitlines():
            raw_line = line.strip()
            if raw_line.startswith("Target "):
                try:
                    current_tid = int(raw_line.split(":", 1)[0].replace("Target ", ""))
                except ValueError:
                    current_tid = None
                    continue

                # Common tgtd format: "Target 1: iqn...."
                if target_name in raw_line:
                    return current_tid
            elif current_tid and target_name in raw_line:
                return current_tid
        return None

    @staticmethod
    def _extract_first_int(text: str, patterns: List[str]) -> Optional[int]:
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except Exception:
                    continue
        return None

    @staticmethod
    def _read_proc_net_totals() -> Dict[str, int]:
        totals = defaultdict(int)
        try:
            with open("/proc/net/dev", "r", encoding="utf-8") as f:
                lines = f.readlines()[2:]
            for line in lines:
                if ":" not in line:
                    continue
                iface, data = line.split(":", 1)
                iface = iface.strip()
                if iface == "lo":
                    continue
                parts = data.split()
                if len(parts) >= 16:
                    totals["rx_bytes"] += int(parts[0])
                    totals["tx_bytes"] += int(parts[8])
        except Exception:
            return {"rx_bytes": 0, "tx_bytes": 0}
        return {"rx_bytes": int(totals["rx_bytes"]), "tx_bytes": int(totals["tx_bytes"])}

    @staticmethod
    def _read_proc_self_io() -> Dict[str, int]:
        values = {"read_bytes": 0, "write_bytes": 0}
        try:
            with open("/proc/self/io", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("read_bytes:"):
                        values["read_bytes"] = int(line.split(":", 1)[1].strip())
                    elif line.startswith("write_bytes:"):
                        values["write_bytes"] = int(line.split(":", 1)[1].strip())
        except Exception:
            pass
        return values

    def _get_active_target_remote_ip_refcounts(self) -> Tuple[Dict[str, int], int]:
        """Return (remote_ip -> active target count, active target total)."""
        success, stdout, _ = self._run_cmd(
            ["tgtadm", "--lld", "iscsi", "--op", "show", "--mode", "target"]
        )
        if not success or not stdout:
            return {}, 0

        refcounts: Dict[str, int] = defaultdict(int)
        active_targets = 0
        current_ips: set[str] = set()
        current_has_connection = False
        in_target = False

        def flush_current():
            nonlocal active_targets, current_ips, current_has_connection
            if not in_target:
                return
            if current_has_connection and current_ips:
                active_targets += 1
                for ip in current_ips:
                    refcounts[ip] += 1
            current_ips = set()
            current_has_connection = False

        for line in stdout.splitlines():
            raw = line.strip()
            if raw.startswith("Target "):
                flush_current()
                in_target = True
                continue

            if not in_target:
                continue

            if raw.startswith("Connection:"):
                current_has_connection = True

            ip_match = re.search(r"IP Address:\s*([^\s]+)", raw)
            if ip_match:
                cleaned = ip_match.group(1).strip().strip("[]")
                if cleaned.lower().startswith("::ffff:"):
                    cleaned = cleaned[7:]
                if cleaned:
                    current_ips.add(cleaned)

        flush_current()
        return dict(refcounts), active_targets

    def get_image_connection_metrics(self, image_name: str) -> Dict:
        """Get iSCSI connection + IO metrics for an image (best effort)."""
        image = self.db.get_image(image_name)
        if not image:
            return {"success": False, "error": f"Image '{image_name}' not found"}

        target_name = image.get("target_name", f"{self.iqn_prefix}:{image_name}")
        stored_tid = image.get("tid")
        resolved_tid = self._get_tid_by_target_name(target_name)
        tid = resolved_tid or stored_tid
        base_result = {
            "success": True,
            "image_id": image_name,
            "target_name": target_name,
            "tid": tid,
            "stored_tid": stored_tid,
            "assigned_to": image.get("assigned_to"),
            "attribution_confidence": "unknown",
            "connection": {
                "active": False,
                "session_count": 0,
                "remote_ips": [],
            },
            "disk_io": {
                "read_bytes": None,
                "write_bytes": None,
                "source": "unavailable",
            },
            "network": {
                "rx_bytes": None,
                "tx_bytes": None,
                "source": "unavailable",
            },
        }

        if not tid:
            return base_result

        ok, stdout, err = self._run_cmd([
            "tgtadm", "--lld", "iscsi", "--op", "show", "--mode", "target", "--tid", str(tid)
        ])
        if not ok:
            base_result["warning"] = f"tgtadm metrics unavailable: {err}"
            return base_result

        connection_count = len(re.findall(r"^\s*Connection:\s*\d+", stdout, flags=re.MULTILINE))
        remote_ips = sorted(set(re.findall(r"IP Address:\s*([^\s]+)", stdout)))
        if not remote_ips:
            remote_ips = sorted(set(re.findall(r"Address:\s*([^\s]+)", stdout)))

        normalized_remote_ips = []
        for raw_ip in remote_ips:
            cleaned = raw_ip.strip().strip("[]")
            if cleaned.lower().startswith("::ffff:"):
                cleaned = cleaned[7:]
            if cleaned:
                normalized_remote_ips.append(cleaned)

        remote_ips = sorted(set(normalized_remote_ips))
        base_result["connection"]["remote_ips"] = remote_ips
        base_result["connection"]["session_count"] = max(connection_count, len(remote_ips))
        base_result["connection"]["active"] = base_result["connection"]["session_count"] > 0

        socket_stats = self._get_iscsi_socket_counters()
        ip_refcounts, active_target_count = self._get_active_target_remote_ip_refcounts()
        if not base_result["connection"]["active"] and socket_stats:
            if len(socket_stats) == 1:
                inferred_ip = next(iter(socket_stats.keys()))
                base_result["connection"]["remote_ips"] = [inferred_ip]
                base_result["connection"]["session_count"] = 1
                base_result["connection"]["active"] = True
                remote_ips = [inferred_ip]

        read_bytes = self._extract_first_int(stdout, [
            r"read[_\s-]*bytes\s*[:=]\s*(\d+)",
            r"\bread\s*[:=]\s*(\d+)\s*bytes",
            r"\brd_bytes\s*[:=]\s*(\d+)",
        ])
        write_bytes = self._extract_first_int(stdout, [
            r"write[_\s-]*bytes\s*[:=]\s*(\d+)",
            r"\bwrite\s*[:=]\s*(\d+)\s*bytes",
            r"\bwr_bytes\s*[:=]\s*(\d+)",
        ])

        if read_bytes is not None:
            base_result["disk_io"]["read_bytes"] = int(read_bytes)
            base_result["disk_io"]["source"] = "target_stats"
            base_result["attribution_confidence"] = "high"
        if write_bytes is not None:
            base_result["disk_io"]["write_bytes"] = int(write_bytes)
            base_result["disk_io"]["source"] = "target_stats"
            base_result["attribution_confidence"] = "high"

        rx_bytes = self._extract_first_int(stdout, [
            r"rx[_\s-]*bytes\s*[:=]\s*(\d+)",
            r"receive[_\s-]*bytes\s*[:=]\s*(\d+)",
        ])
        tx_bytes = self._extract_first_int(stdout, [
            r"tx[_\s-]*bytes\s*[:=]\s*(\d+)",
            r"transmit[_\s-]*bytes\s*[:=]\s*(\d+)",
        ])
        if rx_bytes is not None:
            base_result["network"]["rx_bytes"] = int(rx_bytes)
            base_result["network"]["source"] = "target_stats"
            base_result["attribution_confidence"] = "high"
        if tx_bytes is not None:
            base_result["network"]["tx_bytes"] = int(tx_bytes)
            base_result["network"]["source"] = "target_stats"
            base_result["attribution_confidence"] = "high"

        # Fallback to active iSCSI TCP socket counters (per remote IP) when tgtd target stats
        # do not expose byte counters. This gives practical live transfer visibility per device.
        if base_result["connection"]["active"]:
            total_rx = 0
            total_tx = 0
            matched = False
            ambiguous_ips = [ip for ip in remote_ips if ip_refcounts.get(ip, 0) > 1]
            candidate_ips = [ip for ip in remote_ips if ip_refcounts.get(ip, 0) <= 1]

            for remote_ip in candidate_ips:
                entry = socket_stats.get(remote_ip)
                if not entry:
                    continue
                matched = True
                total_rx += int(entry.get("rx_bytes", 0))
                total_tx += int(entry.get("tx_bytes", 0))

            if not matched and base_result["connection"]["session_count"] == 1:
                # If tgtd does not expose remote IP but exactly one iSCSI session is active,
                # use aggregate socket counters as a best-effort mapping.
                if len(socket_stats) == 1 and active_target_count <= 1:
                    only = next(iter(socket_stats.values()))
                    total_rx = int(only.get("rx_bytes", 0))
                    total_tx = int(only.get("tx_bytes", 0))
                    matched = True

            if matched:
                if base_result["network"]["source"] == "unavailable":
                    base_result["network"]["rx_bytes"] = total_rx
                    base_result["network"]["tx_bytes"] = total_tx
                    base_result["network"]["source"] = "socket_counters"
                    base_result["attribution_confidence"] = "high"

                # iSCSI direction mapping (server perspective):
                # tx -> client reads from disk, rx -> client writes to disk
                if base_result["disk_io"]["source"] == "unavailable":
                    base_result["disk_io"]["read_bytes"] = total_tx
                    base_result["disk_io"]["write_bytes"] = total_rx
                    base_result["disk_io"]["source"] = "socket_counters_estimate"
                    base_result["attribution_confidence"] = "high"
            elif ambiguous_ips:
                base_result["attribution_confidence"] = "ambiguous"
                base_result["warning"] = (
                    (base_result.get("warning", "") + " ").strip() +
                    "Per-device iSCSI socket counters are ambiguous (shared initiator IP across active targets); "
                    "skipping byte attribution to avoid mixed logs."
                ).strip()

        if base_result["network"]["source"] == "unavailable":
            base_result["warning"] = (
                (base_result.get("warning", "") + " ").strip() +
                "Per-device network bytes unavailable from current tgtd output."
            ).strip()

        return base_result

    def _get_iscsi_socket_counters(self) -> Dict[str, Dict[str, int]]:
        """Get per-remote-IP iSCSI byte counters from active TCP sockets (port 3260)."""
        ok, stdout, _ = self._run_cmd(["ss", "-tinp"])
        if not ok or not stdout:
            return {}

        result: Dict[str, Dict[str, int]] = {}
        lines = stdout.splitlines()
        for idx, line in enumerate(lines):
            header = line.strip()
            if not header.startswith("ESTAB"):
                continue
            if ":3260" not in header:
                continue

            # Prefer matching tgtd-owned sockets when process info is present.
            if "users:(\"tgtd\"" not in header and "users:((\"tgtd\"" not in header and "users:(\"tgtd" not in header:
                # Keep fallback behavior if process metadata is missing in output.
                pass

            parts = header.split()
            if len(parts) < 5:
                continue

            local_ep = parts[3]
            remote_ep = parts[4]
            if ":3260" not in local_ep and ":3260" not in remote_ep:
                continue

            remote_ip = remote_ep.rsplit(":", 1)[0] if ":" in remote_ep else remote_ep
            remote_ip = remote_ip.strip("[]")

            details = lines[idx + 1] if idx + 1 < len(lines) else ""
            tx_match = re.search(r"bytes_acked:(\d+)", details)
            rx_match = re.search(r"bytes_received:(\d+)", details)
            tx = int(tx_match.group(1)) if tx_match else 0
            rx = int(rx_match.group(1)) if rx_match else 0

            prev = result.get(remote_ip, {"tx_bytes": 0, "rx_bytes": 0})
            # Same remote IP can appear more than once (multiple sessions); sum them.
            result[remote_ip] = {
                "tx_bytes": prev["tx_bytes"] + tx,
                "rx_bytes": prev["rx_bytes"] + rx,
            }

        return result

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

    def ensure_installer_iso_target(self, installer_rel_path: str, installer_file_path: Path) -> Dict:
        """Ensure a Windows installer ISO is exposed as an iSCSI CD target."""
        if not installer_file_path.exists() or not installer_file_path.is_file():
            return {"success": False, "error": f"Installer ISO not found: {installer_file_path}"}

        safe_name = re.sub(r"[^a-z0-9.-]", "-", installer_rel_path.lower())
        safe_name = re.sub(r"-+", "-", safe_name).strip(".-")
        digest = hashlib.sha1(installer_rel_path.encode("utf-8")).hexdigest()[:12]
        base_name = (safe_name[:48] if safe_name else "installer")
        target_suffix = f"winiso.{base_name}.{digest}"[:180]
        target_name = f"{self.iqn_prefix}:{target_suffix}"

        existing_tid = self._get_tid_by_target_name(target_name)
        if existing_tid:
            ok, _, err = self._run_cmd([
                "tgtadm", "--lld", "iscsi", "--op", "delete",
                "--mode", "target", "--tid", str(existing_tid), "--force",
            ])
            if not ok:
                return {
                    "success": False,
                    "error": f"Failed to refresh existing installer target {target_name} (tid={existing_tid}): {err}"
                }
            logger.info(
                f"Refreshed existing installer iSCSI target before recreate: "
                f"target={target_name} tid={existing_tid}"
            )

        tid = self._get_next_tid()

        ok, _, err = self._run_cmd([
            "tgtadm", "--lld", "iscsi", "--op", "new",
            "--mode", "target", "--tid", str(tid),
            "--targetname", target_name,
        ])
        if not ok:
            err_l = (err or "").lower()
            if "already exists" in err_l or "target exists" in err_l:
                reused_tid = self._get_tid_by_target_name(target_name)
                if reused_tid:
                    logger.info(
                        f"Installer ISO target already existed; reusing target={target_name} tid={reused_tid}"
                    )
                    return {
                        "success": True,
                        "tid": reused_tid,
                        "target_name": target_name,
                        "san_url": f"iscsi:{self.boot_server_ip}:::1:{target_name}",
                        "reused": True,
                        "lun_mode": "reused",
                    }
            return {"success": False, "error": f"tgtadm new target failed: {err}"}

        ok, _, err = self._run_cmd([
            "tgtadm", "--lld", "iscsi", "--op", "new",
            "--mode", "logicalunit", "--tid", str(tid),
            "--lun", "1", "--backing-store", str(installer_file_path), "--device-type", "cd",
        ])
        lun_mode = "cd"
        if not ok:
            logger.warning(
                f"Installer ISO LUN with device-type cd failed for {target_name} (tid={tid}): {err}. "
                f"Trying compatibility mode without --device-type."
            )
            ok2, _, err2 = self._run_cmd([
                "tgtadm", "--lld", "iscsi", "--op", "new",
                "--mode", "logicalunit", "--tid", str(tid),
                "--lun", "1", "--backing-store", str(installer_file_path),
            ])
            if not ok2:
                self._run_cmd([
                    "tgtadm", "--lld", "iscsi", "--op", "delete",
                    "--mode", "target", "--tid", str(tid), "--force",
                ])
                return {
                    "success": False,
                    "error": f"tgtadm add installer ISO LUN failed (cd: {err}) (compat: {err2})"
                }
            lun_mode = "compat"

        ok, _, err = self._run_cmd([
            "tgtadm", "--lld", "iscsi", "--op", "bind",
            "--mode", "target", "--tid", str(tid), "-I", "ALL",
        ])
        if not ok:
            self._run_cmd([
                "tgtadm", "--lld", "iscsi", "--op", "delete",
                "--mode", "target", "--tid", str(tid), "--force",
            ])
            return {"success": False, "error": f"tgtadm bind installer ISO target failed: {err}"}

        return {
            "success": True,
            "tid": tid,
            "target_name": target_name,
            "san_url": f"iscsi:{self.boot_server_ip}:::1:{target_name}",
            "reused": False,
            "lun_mode": lun_mode,
        }

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

    def rename_image(self, source_name: str, dest_name: str) -> Dict:
        """Rename an iSCSI image, move file, and re-register target."""
        source_name = source_name.strip()
        dest_name = dest_name.strip()

        if not source_name or not dest_name:
            return {"success": False, "error": "Source and destination names are required"}
        if source_name == dest_name:
            return {"success": False, "error": "Destination name must be different"}

        source_image = self.db.get_image(source_name)
        if not source_image:
            return {"success": False, "error": f"Image '{source_name}' not found"}
        if self.db.get_image(dest_name):
            return {"success": False, "error": f"Image '{dest_name}' already exists"}

        source_file = self.images_path / f"{source_name}.img"
        dest_file = self.images_path / f"{dest_name}.img"
        if not source_file.exists():
            return {"success": False, "error": f"Source image file not found: {source_file}"}
        if dest_file.exists():
            return {"success": False, "error": f"Destination file already exists: {dest_file}"}

        old_tid = source_image.get("tid")
        if old_tid:
            self._run_cmd([
                "tgtadm", "--lld", "iscsi", "--op", "delete",
                "--mode", "target", "--tid", str(old_tid), "--force",
            ])

        try:
            source_file.rename(dest_file)

            tid, target_name, err = self._register_target(dest_name, dest_file)
            if err:
                dest_file.rename(source_file)
                if old_tid:
                    self._register_target(source_name, source_file)
                return {"success": False, "error": err}

            updated = dict(source_image)
            updated["id"] = dest_name
            updated["name"] = dest_name
            updated["tid"] = tid
            updated["target_name"] = target_name
            updated["file_path"] = str(dest_file)

            self.db.create_image(dest_name, updated)
            self.db.delete_image(source_name)

            assigned_to = source_image.get("assigned_to")
            if assigned_to:
                self.db.update_device(assigned_to, {"image_id": dest_name})

            return {"success": True, "image": self.db.get_image(dest_name)}
        except Exception as e:
            if not source_file.exists() and dest_file.exists():
                try:
                    dest_file.rename(source_file)
                except Exception:
                    pass
            if old_tid:
                self._register_target(source_name, source_file)
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
