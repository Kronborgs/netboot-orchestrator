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
import re
from ..database import Database
from ..services.file_service import FileService
from ..services.image_service import IscsiService
import os
import logging

logger = logging.getLogger(__name__)


def _env(name: str, default: str) -> str:
    """Get env var, also checking for names with trailing whitespace (Unraid quirk)."""
    val = os.getenv(name)
    if val is not None:
        return val.strip()
    # Check for name with trailing space (common Unraid template issue)
    val = os.getenv(name + " ")
    if val is not None:
        return val.strip()
    return default

router = APIRouter(prefix="/api/v1/boot", tags=["boot"])

BRANDING = "Netboot Orchestrator is designed by Kenneth Kronborg AI Team"


@router.get("/winpe/startnet.cmd")
async def winpe_startnet_cmd(
    meta: str = Query(""),
):
    """WinPE startup script that auto-launches Windows setup from installer media."""
    mac = ""
    portal_ip = ""
    target_iqn = ""
    if meta:
        try:
            decoded = meta.strip()
            parts = decoded.split("|", 2)
            if len(parts) == 3:
                mac = parts[0].strip()
                portal_ip = parts[1].strip()
                target_iqn = parts[2].strip()
        except Exception:
            mac = ""
            portal_ip = ""
            target_iqn = ""

    boot_ip = _env("BOOT_SERVER_IP", "192.168.1.50")
    mac_encoded = quote(mac, safe='') if mac else "unknown"
    log_url_base = (
        f"http://{boot_ip}:8000/api/v1/boot/log"
        f"?mac={mac_encoded}&event=winpe_setup_autostart&details="
    )

    iscsi_attach_block = ""
    if portal_ip and target_iqn:
        iscsi_attach_block = f"""
echo Attempting WinPE iSCSI attach for installer media...
iscsicli QAddTargetPortal {portal_ip} 3260 >nul 2>&1
iscsicli AddTargetPortal {portal_ip} 3260 >nul 2>&1
iscsicli QLoginTarget {target_iqn} >nul 2>&1
iscsicli LoginTarget {target_iqn} T * * * * * * * * * * * * * * * 0 >nul 2>&1
timeout /t 3 >nul
wpeutil UpdateBootInfo >nul 2>&1
"""

    script = f"""@echo off
wpeinit
echo.
echo ================================================
echo  Netboot Orchestrator - Windows Setup Autostart
echo ================================================
echo Searching for installer media (auto mode)...

{iscsi_attach_block}

for /L %%R in (1,1,20) do (
    wpeutil UpdateBootInfo >nul 2>&1
    for %%L in (D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
        if exist %%L:\setup.exe (
            echo Found installer on %%L:\
            call :log_setup %%L
            %%L:\setup.exe
            goto :done
        )
        if exist %%L:\sources\setup.exe (
            echo Found installer on %%L:\sources\
            call :log_setup %%L
            %%L:\sources\setup.exe
            goto :done
        )
    )
    timeout /t 2 >nul
)

echo.
echo No installer media with setup.exe found.
echo Opening command prompt for manual troubleshooting.
cmd.exe

:done
exit /b 0

:log_setup
set DRIVE=%1
where powershell.exe >nul 2>&1 && powershell -NoProfile -ExecutionPolicy Bypass -Command "try {{ Invoke-WebRequest -UseBasicParsing -Uri '{log_url_base}Auto%20setup%20started%20from%20drive%20' + $env:DRIVE + '%3A' -Method Get | Out-Null }} catch {{}}" >nul 2>&1
where curl.exe >nul 2>&1 && curl.exe -fsS "{log_url_base}Auto%20setup%20started%20from%20drive%20%DRIVE%%3A" >nul 2>&1
exit /b 0
"""
    return PlainTextResponse(script)


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


def _normalize_mac(mac: str) -> str:
    if not mac:
        return ""
    return re.sub(r"[^0-9a-f]", "", mac.lower())


def _find_device_image(images: list, mac: str) -> Optional[dict]:
    normalized_mac = _normalize_mac(mac)
    if not normalized_mac:
        return None

    for img in images:
        assigned_to = _normalize_mac((img.get("assigned_to") or "").strip())
        if assigned_to and assigned_to == normalized_mac:
            return img

    mac_dash = "-".join([normalized_mac[i:i+2] for i in range(0, len(normalized_mac), 2)])
    disk_prefix = f"disk-{mac_dash}-"
    for img in images:
        image_id = (img.get("id") or "").lower()
        image_name = (img.get("name") or "").lower()
        if image_id.startswith(disk_prefix) or image_name.startswith(disk_prefix):
            return img

    return None


def get_db() -> Database:
    return Database()


def get_file_service() -> FileService:
    return FileService(
        os_installers_path=_env("OS_INSTALLERS_PATH", "/data/os-installers"),
        images_path=_env("IMAGES_PATH", "/data/images"),
    )


def get_iscsi_service() -> IscsiService:
    return IscsiService(images_path=_env("IMAGES_PATH", "/iscsi-images"))


def get_version() -> str:
    for path in [Path("/app/VERSION"), Path(__file__).parent.parent.parent.parent / "VERSION"]:
        if path.exists():
            return path.read_text().strip()
    return "unknown"


def _menu_base_url() -> str:
    ip = _env("BOOT_SERVER_IP", "192.168.1.50")
    return f"http://{ip}:8000/api/v1/boot"

def _build_iscsi_urls(boot_ip: str, target_name: str) -> list[str]:
    """Return prioritized iPXE iSCSI URL variants for maximum client compatibility."""
    candidates = [
        f"iscsi:{boot_ip}:::1:{target_name}",
        f"iscsi:{boot_ip}::3260:1:{target_name}",
        f"iscsi:{boot_ip}:tcp:3260:1:{target_name}",
        f"iscsi:{boot_ip}:::0:{target_name}",
        f"iscsi:{boot_ip}::3260:0:{target_name}",
        f"iscsi:{boot_ip}::::{target_name}",
    ]
    unique = []
    seen = set()
    for url in candidates:
        if url not in seen:
            unique.append(url)
            seen.add(url)
    return unique


def _parse_iscsi_san_url(san_url: str) -> tuple[str, str]:
    """Parse iPXE iSCSI SAN URL into (portal_ip, target_iqn)."""
    if not san_url:
        return "", ""

    raw = san_url.strip()
    if raw.startswith("iscsi:"):
        raw = raw[len("iscsi:"):]

    parts = raw.split(":")
    portal_ip = parts[0].strip() if parts else ""
    target_iqn = parts[-1].strip() if len(parts) >= 2 else ""
    return portal_ip, target_iqn

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
item win_install   Windows Install (WinPE + iSCSI)  >>
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

:win_install
chain {base}/ipxe/windows-select?mac=${{net0/mac}} || goto main_menu

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
    boot_ip = _env("BOOT_SERVER_IP", "192.168.1.50")

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
        script += "item --gap --  --- Currently Linked ---\n"
        for img in linked:
            script += f'item --gap --  * {img["name"]}  [{img.get("size_gb", "?")} GB]\n'
        script += f'item unlink     Unlink current image\n'
        script += "item --gap --\n"

    if available:
        script += "item --gap --  --- Available Images ---\n"
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
    boot_ip = _env("BOOT_SERVER_IP", "192.168.1.50")

    # Find image for this device
    normalized_mac = _normalize_mac(mac)
    images = iscsi.list_images()
    logger.info(f"iSCSI boot requested: mac={mac} normalized={normalized_mac} images_found={len(images)}")
    device_image = _find_device_image(images, mac)

    if not device_image:
        sample = [f"{img.get('id')}=>{img.get('assigned_to')}" for img in images[:10]]
        logger.warning(f"No iSCSI image resolved for mac={mac} normalized={normalized_mac}; sample_assignments={sample}")
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
echo  Returning to menu in 8 seconds...
sleep 8
chain {base}/ipxe/menu
"""
        return PlainTextResponse(script)

    target_name = device_image.get("target_name", f"{iscsi.iqn_prefix}:{device_image['id']}")
    san_urls = _build_iscsi_urls(boot_ip, target_name)
    san_url = san_urls[0]
    sanboot_cmd = " || ".join([f"sanboot {url}" for url in san_urls]) + " || goto iscsi_failed"
    logger.info(
        f"iSCSI boot resolved: mac={mac} image_id={device_image.get('id')} target={target_name} "
        f"san_candidates={san_urls}"
    )

    db.add_boot_log(mac, "iscsi_boot", f"Booting from {target_name} (normalized_mac={normalized_mac})")

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
{sanboot_cmd}

:iscsi_failed
echo
echo !! iSCSI boot failed!
echo !! Check that the image has an OS installed.
echo
prompt Press any key to return to menu...
chain {base}/ipxe/menu
"""
    return PlainTextResponse(script)


@router.get("/ipxe/windows-install")
async def boot_ipxe_windows_install(
    mac: str = Query(""),
    installer: str = Query(""),
    db: Database = Depends(get_db),
):
    """Boot Windows installer via WinPE/wimboot while attaching linked iSCSI disk."""
    base = _menu_base_url()
    iscsi = get_iscsi_service()
    boot_ip = _env("BOOT_SERVER_IP", "192.168.1.50")

    winpe_root = _env("WINDOWS_WINPE_PATH", "winpe").strip().strip("/")
    os_installers_path = Path(_env("OS_INSTALLERS_PATH", "/data/os-installers"))
    logger.info(f"Windows install requested: mac={mac} boot_ip={boot_ip} winpe_root={winpe_root} os_installers_path={os_installers_path}")
    required_rel = [
        f"{winpe_root}/wimboot",
        f"{winpe_root}/boot/BCD",
        f"{winpe_root}/boot/boot.sdi",
        f"{winpe_root}/sources/boot.wim",
    ]
    installer_iso_san_url = _env("WINDOWS_INSTALLER_ISO_SAN_URL", "").strip()
    installer_iso_path = installer.strip().strip("/") if installer else ""
    if not installer_iso_path:
        installer_iso_path = _env("WINDOWS_OS_INSTALLER_ISO_PATH", "").strip().strip("/")
    if not installer_iso_path:
        installer_iso_path = _env("WINDOWS_INSTALLER_ISO_PATH", "").strip().strip("/")

    if not installer_iso_path and not installer_iso_san_url:
        for candidate in [
            "winpe-iscsi.iso",
            "winpe_iscsi.iso",
            "winpe.iso",
            "windows/winpe-iscsi.iso",
            "windows/winpe_iscsi.iso",
            "windows/WinPe_iscsi.iso",
        ]:
            if (os_installers_path / candidate).exists():
                installer_iso_path = candidate
                logger.info(f"Windows install auto-detected installer ISO (candidate): {installer_iso_path}")
                break

    if not installer_iso_path and not installer_iso_san_url:
        try:
            all_isos = [p for p in os_installers_path.rglob("*.iso") if p.is_file()]
            preferred = None
            fallback = None
            for iso in all_isos:
                rel = str(iso.relative_to(os_installers_path)).replace("\\", "/")
                low = rel.lower()
                if "winpe" in low and "iscsi" in low:
                    preferred = rel
                    break
                if "winpe" in low and fallback is None:
                    fallback = rel
            installer_iso_path = preferred or fallback or ""
            if installer_iso_path:
                logger.info(f"Windows install auto-detected installer ISO (scan): {installer_iso_path}")
            else:
                logger.info("Windows install auto-detect scan found no WinPE ISO")
        except Exception as e:
            logger.warning(f"Windows install ISO auto-detect scan failed: {e}")

    missing = [rel for rel in required_rel if not (os_installers_path / rel).exists()]
    has_iso_fallback = bool(installer_iso_san_url or installer_iso_path)

    if missing and not has_iso_fallback:
        logger.warning(f"Windows install missing WinPE files for mac={mac}: {missing}")
        db.add_boot_log(mac or "unknown", "windows_install_missing", f"Missing WinPE files: {', '.join(missing)}")
        script = f"""#!ipxe
echo
echo ================================================
echo  Windows Install files not found
echo ================================================
echo  Expected under OS installers path:
echo  - {required_rel[0]}
echo  - {required_rel[1]}
echo  - {required_rel[2]}
echo  - {required_rel[3]}
echo
echo  Configure WINDOWS_WINPE_PATH or WINDOWS_INSTALLER_ISO_PATH.
echo
prompt Press any key to return to menu...
chain {base}/ipxe/menu
"""
        return PlainTextResponse(script)
    if missing and has_iso_fallback:
        logger.info(
            f"Windows install: WinPE files missing, using ISO fallback for mac={mac}; "
            f"iso_san={'set' if installer_iso_san_url else 'unset'} iso_path={installer_iso_path}"
        )

    normalized_mac = _normalize_mac(mac)
    images = iscsi.list_images()
    logger.info(f"Windows install image lookup: mac={mac} normalized={normalized_mac} images_found={len(images)}")
    device_image = _find_device_image(images, mac)

    if not device_image:
        sample = [f"{img.get('id')}=>{img.get('assigned_to')}" for img in images[:10]]
        logger.warning(f"Windows install aborted: no iSCSI image resolved for mac={mac} normalized={normalized_mac}; sample_assignments={sample}")
        script = f"""#!ipxe
echo
echo ================================================
echo  No iSCSI image linked to this device.
echo ================================================
echo  Link an image first, then retry Windows Install.
echo  Device: {mac}
echo
echo  Returning to menu in 8 seconds...
sleep 8
chain {base}/ipxe/menu
"""
        return PlainTextResponse(script)

    target_name = device_image.get("target_name", f"{iscsi.iqn_prefix}:{device_image['id']}")
    san_urls = _build_iscsi_urls(boot_ip, target_name)
    san_url = san_urls[0]
    sanhook_cmd = " || ".join([f"sanhook --drive 0x80 {url}" for url in san_urls]) + " || goto windows_failed"
    logger.info(
        f"Windows install image resolved: mac={mac} image_id={device_image.get('id')} target={target_name} "
        f"san_candidates={san_urls}"
    )

    wimboot_url = f"http://{boot_ip}:8000/api/v1/os-installers/download/{quote(required_rel[0], safe='/')}"
    bcd_url = f"http://{boot_ip}:8000/api/v1/os-installers/download/{quote(required_rel[1], safe='/')}"
    sdi_url = f"http://{boot_ip}:8000/api/v1/os-installers/download/{quote(required_rel[2], safe='/')}"
    wim_url = f"http://{boot_ip}:8000/api/v1/os-installers/download/{quote(required_rel[3], safe='/')}"
    startnet_meta = quote(f"{mac}||", safe='')
    startnet_url = f"http://{boot_ip}:8000/api/v1/boot/winpe/startnet.cmd?meta={startnet_meta}"
    iso_hook_cmd = ""
    iso_info_line = ""
    installer_iso_url = ""
    installer_log_value = installer_iso_path or installer_iso_san_url or "none"
    installer_mode = "none"

    if installer_iso_san_url:
        iso_hook_cmd = (
            f"sanhook --drive 0xE0 {installer_iso_san_url} "
            f"|| sanhook --drive 0x81 {installer_iso_san_url} "
            f"|| goto windows_failed"
        )
        iso_info_line = f"echo  Installer media (0xE0/0x81): {installer_iso_san_url}"
        installer_log_value = installer_iso_san_url
        installer_mode = "san_url"
        portal_ip, target_iqn = _parse_iscsi_san_url(installer_iso_san_url)
        if portal_ip and target_iqn:
            iscsi_meta = quote(f"{mac}|{portal_ip}|{target_iqn}", safe='')
            startnet_url = (
                f"http://{boot_ip}:8000/api/v1/boot/winpe/startnet.cmd"
                f"?meta={iscsi_meta}"
            )
        logger.info(f"Windows install optional ISO SAN configured: {installer_iso_san_url}")
    elif installer_iso_path:
        installer_full_path = os_installers_path / installer_iso_path
        ensure_iso = iscsi.ensure_installer_iso_target(installer_iso_path, installer_full_path)
        if ensure_iso.get("success"):
            installer_iso_san_url = ensure_iso.get("san_url", "")
            iso_hook_cmd = (
                f"sanhook --drive 0xE0 {installer_iso_san_url} "
                f"|| sanhook --drive 0x81 {installer_iso_san_url} "
                f"|| goto windows_failed"
            )
            iso_info_line = f"echo  Installer media (0xE0/0x81): {installer_iso_path}"
            installer_log_value = installer_iso_path
            installer_mode = "iscsi_export"
            target_iqn = ensure_iso.get("target_name", "")
            portal_ip = boot_ip
            if installer_iso_san_url:
                parsed_portal, parsed_iqn = _parse_iscsi_san_url(installer_iso_san_url)
                portal_ip = parsed_portal or portal_ip
                target_iqn = parsed_iqn or target_iqn
            if portal_ip and target_iqn:
                iscsi_meta = quote(f"{mac}|{portal_ip}|{target_iqn}", safe='')
                startnet_url = (
                    f"http://{boot_ip}:8000/api/v1/boot/winpe/startnet.cmd"
                    f"?meta={iscsi_meta}"
                )
            logger.info(
                f"Windows install installer ISO exported as iSCSI: path={installer_iso_path} "
                f"target={ensure_iso.get('target_name')} san={installer_iso_san_url} reused={ensure_iso.get('reused')}"
            )
        else:
            error = ensure_iso.get("error", "unknown error")
            logger.error(
                f"Windows install aborted: failed to export installer ISO as iSCSI: "
                f"path={installer_iso_path} error={error}"
            )
            db.add_boot_log(
                mac,
                "windows_install_media_error",
                f"Installer media export failed for {installer_iso_path}: {error}"
            )
            script = f"""#!ipxe
echo
echo ================================================
echo  Windows installer media export failed
echo ================================================
echo  ISO: {installer_iso_path}
echo
echo  Could not prepare iSCSI media target.
echo  Check backend logs for tgtd/tgtadm error details.
echo
echo  Returning to menu in 10 seconds...
sleep 10
chain {base}/ipxe/menu
"""
            return PlainTextResponse(script)
    else:
        logger.info("Windows install optional ISO not configured (continuing with WinPE only)")

    logger.info(
        f"Windows install URLs: wimboot={wimboot_url} bcd={bcd_url} sdi={sdi_url} wim={wim_url}"
    )

    if missing and has_iso_fallback:
        db.add_boot_log(
            mac,
            "windows_install_iso_fallback",
            f"ISO fallback install via {target_name}; installer={installer_log_value}; mode={installer_mode}"
        )

        if installer_iso_san_url:
            iso_attach_cmd = (
                f"sanhook --drive 0xE0 {installer_iso_san_url} "
                f"|| sanhook --drive 0x81 {installer_iso_san_url} "
                f"|| goto windows_failed"
            )
            iso_boot_cmd = "sanboot --drive 0xE0 || sanboot --drive 0x81 || goto windows_failed"
            iso_display = installer_iso_san_url
        else:
            iso_attach_cmd = ""
            iso_boot_cmd = f"sanboot --no-describe {installer_iso_url} || goto windows_failed"
            iso_display = installer_iso_path

        script = f"""#!ipxe
echo
echo ================================================
echo  Windows Install (ISO fallback + iSCSI)
echo ================================================
echo  Device: {mac}
echo  System disk (0x80): {target_name}
echo  Installer ISO: {iso_display}
echo ================================================
echo

echo Acquiring DHCP lease...
dhcp || goto windows_failed

echo Attaching system iSCSI disk...
{sanhook_cmd}

{iso_attach_cmd}

echo Booting installer ISO...
{iso_boot_cmd}

:windows_failed
echo
echo !! Windows installer ISO fallback failed.
echo !! Verify ISO path/SAN URL and iSCSI target reachability.
echo
echo  Returning to menu in 10 seconds...
sleep 10
chain {base}/ipxe/menu
"""
        return PlainTextResponse(script)

    db.add_boot_log(
        mac,
        "windows_install",
        f"WinPE install boot via {target_name} (normalized_mac={normalized_mac}); installer={installer_log_value}; mode={installer_mode}"
    )

    script = f"""#!ipxe
echo
echo ================================================
echo  Windows Install (WinPE + iSCSI)
echo ================================================
echo  Device: {mac}
echo  System disk (0x80): {target_name}
{iso_info_line}
echo ================================================
echo

echo Acquiring DHCP lease...
dhcp || goto windows_failed

echo Attaching system iSCSI disk...
{sanhook_cmd}

{iso_hook_cmd}

echo Loading WinPE via wimboot...
kernel {wimboot_url} || goto windows_failed
initrd {bcd_url} BCD || goto windows_failed
initrd {sdi_url} boot.sdi || goto windows_failed
initrd {wim_url} boot.wim || goto windows_failed
initrd {startnet_url} Windows/System32/startnet.cmd || goto windows_failed
boot || goto windows_failed

:windows_failed
echo
echo !! Windows installer boot failed.
echo !! Verify WinPE files and optional ISO target/path.
echo
echo  Returning to menu in 10 seconds...
sleep 10
chain {base}/ipxe/menu
"""
    return PlainTextResponse(script)


@router.get("/ipxe/windows-select")
async def boot_ipxe_windows_select(
    mac: str = Query(""),
    path: str = Query(""),
    file_service: FileService = Depends(get_file_service),
):
    """Select Windows installer ISO before starting WinPE + iSCSI flow."""
    base = _menu_base_url()
    items = file_service.get_folder_contents(path, is_images=False).get("items", [])

    folders = [i for i in items if i.get("type") == "folder"]
    files = [
        i for i in items
        if i.get("type") == "file"
        and i.get("name", "").lower().endswith(".iso")
        and "winpe" not in i.get("name", "").lower()
    ]

    breadcrumb = _ascii_safe(f"/{path}") if path else "/ (root)"

    script = f"""#!ipxe
# {BRANDING}

:windows_select
menu ========== Windows Installer Select  [ {breadcrumb} ] ==========
item --gap --
item --gap --  Device: {mac}
item --gap --
"""

    if path:
        script += "item back       << Back\n"

    if folders:
        script += "item --gap --  ---- Folders ----\n"
        for idx, folder in enumerate(folders):
            label = f"folder_{idx}"
            display_name = _ascii_safe(folder.get("name", ""))
            script += f"item {label}    [DIR] {display_name}\n"

    if files:
        script += "item --gap --  ---- Windows ISOs ----\n"
        for idx, f in enumerate(files):
            label = f"iso_{idx}"
            display_name = _ascii_safe(f.get("name", "")[:52])
            script += f"item {label}    {display_name}\n"
    else:
        script += "item --gap --  (No Windows installer ISO in this folder)\n"

    script += """item --gap --
item quick_winpe  Start WinPE without installer ISO
item main_menu    << Main Menu
item --gap --
choose selected || goto main_menu
goto ${selected}

"""

    if path:
        parent = "/".join(path.rstrip("/").split("/")[:-1])
        parent_encoded = quote(parent, safe='/') if parent else ""
        query = f"?mac={quote(mac, safe='')}&path={parent_encoded}" if parent else f"?mac={quote(mac, safe='')}"
        script += f":back\nchain {base}/ipxe/windows-select{query} || goto windows_select\n\n"

    for idx, folder in enumerate(folders):
        folder_path = quote(folder.get("path", ""), safe='/')
        script += (
            f":folder_{idx}\n"
            f"chain {base}/ipxe/windows-select?mac={quote(mac, safe='')}&path={folder_path} || goto windows_select\n\n"
        )

    for idx, f in enumerate(files):
        installer_path = quote(f.get("path", ""), safe='/')
        script += (
            f":iso_{idx}\n"
            f"chain {base}/ipxe/windows-install?mac={quote(mac, safe='')}&installer={installer_path} || goto windows_select\n\n"
        )

    script += (
        f":quick_winpe\n"
        f"chain {base}/ipxe/windows-install?mac={quote(mac, safe='')} || goto windows_select\n\n"
        f":main_menu\n"
        f"chain {base}/ipxe/menu || goto windows_select\n"
    )

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
            images_path = _env("IMAGES_PATH", "/iscsi-images")
            return {
                "action": "boot_image",
                "image_id": image_id,
                "image_path": f"{images_path}/{image_id}.img",
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


@router.post("/iscsi/images/{name}/rename")
async def rename_iscsi_image(
    name: str,
    new_name: str = Query(...),
    db: Database = Depends(get_db),
):
    """Rename an iSCSI image."""
    iscsi = get_iscsi_service()
    db.add_boot_log("webui", "iscsi_rename", f"Renaming {name} -> {new_name}")
    result = iscsi.rename_image(name, new_name)
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
