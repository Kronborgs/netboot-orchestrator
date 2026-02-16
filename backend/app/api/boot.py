"""
Boot menu & iSCSI management endpoints.

iPXE boot menu system with submenus (each endpoint returns a complete iPXE script).
Navigation between menus uses iPXE 'chain' to different API URLs.

Menu structure:
  Main Menu
  ├── OS Installers (folder navigation from /isos)
  ├── Create iSCSI Image (4/32/64/128/256 GB)
  ├── Link Device to iSCSI Image
  ├── Boot from iSCSI
  ├── Device Info
  ├── iPXE Shell
  └── Reboot
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import PlainTextResponse
from typing import Optional
from pathlib import Path
from urllib.parse import quote
import unicodedata
from ..database import Database
from ..services.file_service import FileService
from ..services.image_service import IscsiService
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/boot", tags=["boot"])

BRANDING = "Netboot Orchestrator is designed by Kenneth Kronborg AI Team"


def _ascii_safe(text: str) -> str:
    """Convert text to ASCII-safe for iPXE display.
    Replaces Unicode quotes, dashes, etc. with ASCII equivalents."""
    replacements = {
        "\u2018": "'", "\u2019": "'",  # smart single quotes
        "\u201c": '"', "\u201d": '"',  # smart double quotes
        "\u2013": "-", "\u2014": "--", # en-dash, em-dash
        "\u2026": "...",                # ellipsis
        "\u00e9": "e", "\u00e8": "e",  # accented e
        "\u00f6": "o", "\u00fc": "u",  # umlauts
    }
    for uc, asc in replacements.items():
        text = text.replace(uc, asc)
    # Strip any remaining non-ASCII
    return text.encode("ascii", errors="replace").decode("ascii")


def get_db() -> Database:
    return Database()


def get_file_service() -> FileService:
    return FileService(
        os_installers_path=os.getenv("OS_INSTALLERS_PATH", "/data/os-installers"),
        images_path=os.getenv("IMAGES_PATH", "/data/images"),
    )


def get_iscsi_service() -> IscsiService:
    return IscsiService(images_path=os.getenv("IMAGES_PATH", "/iscsi-images"))


def get_version() -> str:
    for path in [Path("/app/VERSION"), Path(__file__).parent.parent.parent.parent / "VERSION"]:
        if path.exists():
            return path.read_text().strip()
    return "unknown"


def _menu_base_url() -> str:
    ip = os.getenv("BOOT_SERVER_IP", "192.168.1.50")
    return f"http://{ip}:8000/api/v1/boot"


# =====================================================================
#  MAIN BOOT MENU
# =====================================================================

@router.get("/ipxe/menu")
async def boot_ipxe_main_menu(db: Database = Depends(get_db)):
    """Main iPXE boot menu — entry point for all PXE clients."""
    version = get_version()
    base = _menu_base_url()

    # Log boot event
    db.add_boot_log("unknown", "menu_loaded", "Main menu loaded")

    script = f"""#!ipxe
# {BRANDING}

:main_menu
menu ========= Netboot Orchestrator v{version} =========
item --gap --
item --gap --  Designed by Kenneth Kronborg AI Team
item --gap --
item --gap --  Device Info:
item --gap --  MAC:     ${{net0/mac}}
item --gap --  IP:      ${{net0/ip}}
item --gap --  Gateway: ${{net0/gateway}}
item --gap --
item --gap --  ==== Main Menu ====
item os_install    OS Installers  >>
item create_iscsi  Create iSCSI Image  >>
item link_iscsi    Link Device to iSCSI Image  >>
item boot_iscsi    Boot from iSCSI
item --gap --
item --gap --  ==== Info & Tools ====
item shell         iPXE Shell
item device_info   Device Info
item reboot        Reboot
item --gap --
choose selected || goto shell
goto ${{selected}}

:os_install
chain {base}/ipxe/os-menu || goto main_menu

:create_iscsi
chain {base}/ipxe/iscsi-create || goto main_menu

:link_iscsi
chain {base}/ipxe/iscsi-link?mac=${{net0/mac}} || goto main_menu

:boot_iscsi
chain {base}/ipxe/iscsi-boot?mac=${{net0/mac}} || goto main_menu

:device_info
echo
echo ================================================
echo  Device Information
echo ================================================
echo  MAC Address:  ${{net0/mac}}
echo  IP Address:   ${{net0/ip}}
echo  Gateway:      ${{net0/gateway}}
echo  DNS:          ${{net0/dns}}
echo  Next Server:  ${{next-server}}
echo  Platform:     ${{platform}}
echo  Buildarch:    ${{buildarch}}
echo ================================================
echo
prompt Press any key to return to menu...
goto main_menu

:shell
echo
echo Type 'exit' to return to menu
shell
goto main_menu

:reboot
reboot
"""
    return PlainTextResponse(script)


# =====================================================================
#  OS INSTALLERS SUBMENU (folder navigation)
# =====================================================================

@router.get("/ipxe/os-menu")
async def boot_ipxe_os_menu(
    path: str = "",
    file_service: FileService = Depends(get_file_service),
    db: Database = Depends(get_db),
):
    """OS installer submenu with folder-structure navigation."""
    version = get_version()
    base = _menu_base_url()
    boot_ip = os.getenv("BOOT_SERVER_IP", "192.168.1.50")

    db.add_boot_log("unknown", "os_menu", f"Browsing: /{path}")

    result = file_service.get_folder_contents(path, is_images=False)
    items = result.get("items", [])

    breadcrumb = _ascii_safe(f"/{path}") if path else "/ (root)"

    script = f"""#!ipxe
# {BRANDING}

:os_menu
menu ========== OS Installers  [ {breadcrumb} ] ==========
item --gap --
"""

    # Folders first
    folders = [i for i in items if i["type"] == "folder"]
    files = [i for i in items if i["type"] == "file"]

    if path:
        # "Back" option to parent folder
        parent = "/".join(path.rstrip("/").split("/")[:-1])
        script += f'item back       << Back\n'

    if folders:
        script += "item --gap --  ---- Folders ----\n"
        for idx, folder in enumerate(folders):
            label = f"folder_{idx}"
            display_name = _ascii_safe(folder["name"])
            script += f'item {label}    [DIR] {display_name}  [{folder.get("size_display", "")}]\n'

    if files:
        script += "item --gap --  ---- OS Images ----\n"
        for idx, f in enumerate(files):
            label = f"file_{idx}"
            name = _ascii_safe(f["name"][:50])
            size = f.get("size_display", "")
            script += f'item {label}    {name}  [{size}]\n'

    if not folders and not files:
        script += "item --gap --  (empty folder)\n"

    script += """item --gap --
item main_menu  << Main Menu
item --gap --
choose selected || goto main_menu
goto ${selected}

"""

    # Goto targets for back
    if path:
        parent = "/".join(path.rstrip("/").split("/")[:-1])
        parent_encoded = quote(parent, safe='/') if parent else ""
        parent_query = f"?path={parent_encoded}" if parent else ""
        script += f""":back
chain {base}/ipxe/os-menu{parent_query} || goto os_menu

"""

    # Goto targets for folders
    for idx, folder in enumerate(folders):
        folder_path = quote(folder["path"], safe='/')
        script += f""":folder_{idx}
chain {base}/ipxe/os-menu?path={folder_path} || goto os_menu

"""

    # Goto targets for files (download via sanboot for ISOs, chain for iPXE scripts)
    for idx, f in enumerate(files):
        file_path = f["path"]
        encoded_path = quote(file_path, safe='/')
        url = f"http://{boot_ip}:8000/api/v1/os-installers/download/{encoded_path}"
        name = _ascii_safe(f["name"][:50])
        ext = f["name"].lower().rsplit('.', 1)[-1] if '.' in f["name"] else ''

        # Choose boot method based on file type
        if ext in ('iso', 'img'):
            boot_cmd = f"sanboot --no-describe {url}"
        elif ext == 'ipxe':
            boot_cmd = f"chain {url}"
        elif ext == 'efi':
            boot_cmd = f"chain {url}"
        else:
            boot_cmd = f"sanboot --no-describe {url}"

        script += f""":{f'file_{idx}'}
echo
echo ================================================
echo  Loading: {name}
echo  Source:  {url}
echo ================================================
echo
{boot_cmd} || goto os_failed
goto os_menu

"""

    script += f""":os_failed
echo
echo !! Download failed - returning to menu in 5s...
sleep 5
goto os_menu

:main_menu
chain {base}/ipxe/menu || goto os_menu
"""
    return PlainTextResponse(script)


# =====================================================================
#  CREATE iSCSI IMAGE SUBMENU
# =====================================================================

@router.get("/ipxe/iscsi-create")
async def boot_ipxe_iscsi_create(db: Database = Depends(get_db)):
    """iSCSI image creation size-selection menu."""
    base = _menu_base_url()

    script = f"""#!ipxe
# {BRANDING}

:iscsi_create_menu
menu ========== Create iSCSI Image ==========
item --gap --
item --gap --  Select image size for this device:
item --gap --  MAC: ${{net0/mac}}
item --gap --
item size_4      4 GB   (lightweight / testing)
item size_32    32 GB   (basic OS install)
item size_64    64 GB   (standard workstation)
item size_128  128 GB   (large workstation)
item size_256  256 GB   (server / heavy use)
item --gap --
item main_menu  << Main Menu
item --gap --
choose selected || goto main_menu
goto ${{selected}}

:size_4
chain {base}/ipxe/iscsi-do-create?mac=${{net0/mac}}&size=4 || goto iscsi_create_menu

:size_32
chain {base}/ipxe/iscsi-do-create?mac=${{net0/mac}}&size=32 || goto iscsi_create_menu

:size_64
chain {base}/ipxe/iscsi-do-create?mac=${{net0/mac}}&size=64 || goto iscsi_create_menu

:size_128
chain {base}/ipxe/iscsi-do-create?mac=${{net0/mac}}&size=128 || goto iscsi_create_menu

:size_256
chain {base}/ipxe/iscsi-do-create?mac=${{net0/mac}}&size=256 || goto iscsi_create_menu

:main_menu
chain {base}/ipxe/menu || goto iscsi_create_menu
"""
    return PlainTextResponse(script)


@router.get("/ipxe/iscsi-do-create")
async def boot_ipxe_iscsi_do_create(
    mac: str = Query(...),
    size: int = Query(...),
    db: Database = Depends(get_db),
):
    """Action endpoint: create the iSCSI image and show result."""
    base = _menu_base_url()
    iscsi = get_iscsi_service()

    # Sanitize MAC for use as image name
    safe_mac = mac.replace(":", "-").lower()
    image_name = f"disk-{safe_mac}-{size}g"

    db.add_boot_log(mac, "iscsi_create", f"Creating {size}GB image: {image_name}")
    result = iscsi.create_image(image_name, size)

    if result.get("success"):
        # Auto-link the image to this device
        iscsi.link_device(image_name, mac)
        db.add_boot_log(mac, "iscsi_created", f"Image {image_name} created and linked")

        script = f"""#!ipxe
echo
echo ================================================
echo  iSCSI Image Created Successfully!
echo ================================================
echo
echo  Image Name: {image_name}
echo  Size:       {size} GB
echo  Device:     {mac}
echo  Target:     {iscsi.iqn_prefix}:{image_name}
echo  Server:     {iscsi.boot_server_ip}
echo
echo  The image has been linked to this device.
echo  Loading OS Installers menu...
echo
echo ================================================
echo
prompt Press any key to continue to OS Installers...
chain {base}/ipxe/os-menu
"""
    else:
        error = result.get("error", "Unknown error")
        script = f"""#!ipxe
echo
echo ================================================
echo  ERROR: iSCSI Image Creation Failed
echo ================================================
echo
echo  Error: {error}
echo
echo ================================================
echo
prompt Press any key to return to menu...
chain {base}/ipxe/menu
"""
    return PlainTextResponse(script)


# =====================================================================
#  LINK DEVICE TO iSCSI IMAGE
# =====================================================================

@router.get("/ipxe/iscsi-link")
async def boot_ipxe_iscsi_link(
    mac: str = Query(""),
    db: Database = Depends(get_db),
):
    """Show available iSCSI images for linking."""
    base = _menu_base_url()
    iscsi = get_iscsi_service()
    images = iscsi.list_images()

    available = [img for img in images if not img.get("assigned_to")]
    linked = [img for img in images if img.get("assigned_to") == mac]

    script = f"""#!ipxe
# {BRANDING}

:link_menu
menu ========== Link Device to iSCSI Image ==========
item --gap --
item --gap --  Device: {mac}
item --gap --
"""

    if linked:
        script += "item --gap --  ─── Currently Linked ───\n"
        for img in linked:
            script += f'item --gap --  ✓ {img["name"]}  [{img.get("size_gb", "?")} GB]\n'
        script += f'item unlink     Unlink current image\n'
        script += "item --gap --\n"

    if available:
        script += "item --gap --  ─── Available Images ───\n"
        for idx, img in enumerate(available):
            label = f"link_{idx}"
            script += f'item {label}    {img["name"]}  [{img.get("size_gb", "?")} GB]\n'
    else:
        script += "item --gap --  No available images. Create one first.\n"

    script += """item --gap --
item main_menu  << Main Menu
item --gap --
choose selected || goto main_menu
goto ${selected}

"""

    # Goto targets
    if linked:
        script += f""":unlink
chain {base}/ipxe/iscsi-do-unlink?mac={mac} || goto link_menu

"""

    for idx, img in enumerate(available):
        script += f""":link_{idx}
chain {base}/ipxe/iscsi-do-link?mac={mac}&image={img["id"]} || goto link_menu

"""

    script += f""":main_menu
chain {base}/ipxe/menu || goto link_menu
"""
    return PlainTextResponse(script)


@router.get("/ipxe/iscsi-do-link")
async def boot_ipxe_iscsi_do_link(
    mac: str = Query(...),
    image: str = Query(...),
    db: Database = Depends(get_db),
):
    """Action: link device to image."""
    base = _menu_base_url()
    iscsi = get_iscsi_service()

    db.add_boot_log(mac, "iscsi_link", f"Linking to {image}")
    result = iscsi.link_device(image, mac)

    if result.get("success"):
        script = f"""#!ipxe
echo
echo ================================================
echo  Device linked to iSCSI image!
echo ================================================
echo  Device: {mac}
echo  Image:  {image}
echo  Target: {result.get('target_name', '')}
echo ================================================
echo
prompt Press any key to return to menu...
chain {base}/ipxe/menu
"""
    else:
        script = f"""#!ipxe
echo
echo  ERROR: {result.get('error', 'Unknown error')}
echo
prompt Press any key to return to menu...
chain {base}/ipxe/menu
"""
    return PlainTextResponse(script)


@router.get("/ipxe/iscsi-do-unlink")
async def boot_ipxe_iscsi_do_unlink(mac: str = Query(...), db: Database = Depends(get_db)):
    """Action: unlink device."""
    base = _menu_base_url()
    iscsi = get_iscsi_service()

    db.add_boot_log(mac, "iscsi_unlink", f"Unlinking device {mac}")
    iscsi.unlink_device(mac)

    script = f"""#!ipxe
echo
echo  Device {mac} unlinked from iSCSI image.
echo
prompt Press any key to return to menu...
chain {base}/ipxe/menu
"""
    return PlainTextResponse(script)


# =====================================================================
#  BOOT FROM iSCSI
# =====================================================================

@router.get("/ipxe/iscsi-boot")
async def boot_ipxe_iscsi_boot(mac: str = Query(""), db: Database = Depends(get_db)):
    """Boot device from its linked iSCSI image."""
    base = _menu_base_url()
    iscsi = get_iscsi_service()
    boot_ip = os.getenv("BOOT_SERVER_IP", "192.168.1.50")

    # Find image for this device
    images = iscsi.list_images()
    device_image = None
    for img in images:
        if img.get("assigned_to") == mac:
            device_image = img
            break

    if not device_image:
        script = f"""#!ipxe
echo
echo ================================================
echo  No iSCSI image linked to this device.
echo ================================================
echo  MAC: {mac}
echo
echo  Go to "Link Device to iSCSI Image" first,
echo  or create a new image via "Create iSCSI Image".
echo
prompt Press any key to return to menu...
chain {base}/ipxe/menu
"""
        return PlainTextResponse(script)

    target_name = device_image.get("target_name", f"{iscsi.iqn_prefix}:{device_image['id']}")
    san_url = f"iscsi:{boot_ip}::::{target_name}"

    db.add_boot_log(mac, "iscsi_boot", f"Booting from {target_name}")

    script = f"""#!ipxe
echo
echo ================================================
echo  Booting from iSCSI
echo ================================================
echo  Device: {mac}
echo  Image:  {device_image['name']}
echo  Target: {target_name}
echo  Size:   {device_image.get('size_gb', '?')} GB
echo  SAN:    {san_url}
echo ================================================
echo

echo Connecting to iSCSI target...
sanboot {san_url} || goto iscsi_failed

:iscsi_failed
echo
echo !! iSCSI boot failed!
echo !! Check that the image has an OS installed.
echo
prompt Press any key to return to menu...
chain {base}/ipxe/menu
"""
    return PlainTextResponse(script)


# =====================================================================
#  BOOT CHECK-IN & LOGGING (REST API)
# =====================================================================

@router.get("/check-in")
async def check_in(mac: str, device_type: str, db: Database = Depends(get_db)):
    """Check-in endpoint for devices at boot time."""
    db.add_boot_log(mac, "check_in", f"device_type={device_type}")

    device = db.get_device(mac)
    if device:
        image_id = device.get("image_id")
        kernel_set = device.get("kernel_set", "default")
        if image_id:
            image = db.get_image(image_id)
            return {
                "action": "boot_image",
                "image_id": image_id,
                "image_path": f"/data/iscsi/images/{image_id}.img",
                "kernel_set": kernel_set,
            }
        else:
            return {"action": "boot_default", "kernel_set": kernel_set}
    else:
        return {
            "action": "show_menu",
            "device_type": device_type,
            "message": "Unknown device. Please register or select boot option.",
        }


@router.post("/log")
async def record_boot_log(
    mac: str = Query(...),
    event: str = Query(...),
    details: str = Query(""),
    ip: str = Query(""),
    db: Database = Depends(get_db),
):
    """Record a boot event from iPXE or WebUI."""
    entry = db.add_boot_log(mac, event, details, ip)
    return {"status": "logged", "entry": entry}


@router.get("/logs")
async def get_boot_logs(
    mac: str = Query(None),
    limit: int = Query(100),
    db: Database = Depends(get_db),
):
    """Get boot logs, optionally filtered by MAC."""
    return db.get_boot_logs(mac=mac, limit=limit)


# =====================================================================
#  iSCSI REST API (for WebUI)
# =====================================================================

@router.get("/iscsi/images")
async def list_iscsi_images():
    """List all iSCSI images with status."""
    iscsi = get_iscsi_service()
    return iscsi.list_images()


@router.post("/iscsi/images")
async def create_iscsi_image(
    name: str = Query(...),
    size_gb: int = Query(...),
    db: Database = Depends(get_db),
):
    """Create a new iSCSI image."""
    iscsi = get_iscsi_service()
    db.add_boot_log("webui", "iscsi_create", f"Creating {size_gb}GB image: {name}")
    result = iscsi.create_image(name, size_gb)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.delete("/iscsi/images/{name}")
async def delete_iscsi_image(name: str, db: Database = Depends(get_db)):
    """Delete an iSCSI image."""
    iscsi = get_iscsi_service()
    db.add_boot_log("webui", "iscsi_delete", f"Deleting image: {name}")
    result = iscsi.delete_image(name)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/iscsi/images/{name}/copy")
async def copy_iscsi_image(
    name: str,
    dest_name: str = Query(...),
    db: Database = Depends(get_db),
):
    """Copy an iSCSI image."""
    iscsi = get_iscsi_service()
    db.add_boot_log("webui", "iscsi_copy", f"Copying {name} -> {dest_name}")
    result = iscsi.copy_image(name, dest_name)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/iscsi/images/{name}/link")
async def link_iscsi_image(
    name: str,
    mac: str = Query(...),
    db: Database = Depends(get_db),
):
    """Link an iSCSI image to a device."""
    iscsi = get_iscsi_service()
    db.add_boot_log(mac, "iscsi_link", f"Linking to {name}")
    result = iscsi.link_device(name, mac)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/iscsi/images/{name}/unlink")
async def unlink_iscsi_image(name: str, db: Database = Depends(get_db)):
    """Unlink an iSCSI image from its device."""
    iscsi = get_iscsi_service()
    image = iscsi.get_image(name)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    mac = image.get("assigned_to", "")
    if mac:
        db.add_boot_log(mac, "iscsi_unlink", f"Unlinking from {name}")
        result = iscsi.unlink_device(mac)
    else:
        result = {"success": True, "message": "Image was not linked"}
    return result
