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

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.responses import PlainTextResponse, FileResponse
from typing import Optional
from pathlib import Path
from urllib.parse import quote
import unicodedata
import re
from datetime import datetime
from ..database import Database
from ..services.file_service import FileService
from ..services.image_service import IscsiService
import os
import logging

logger = logging.getLogger(__name__)


def _parse_iso_timestamp(value: str) -> Optional[datetime]:
    raw = (value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except Exception:
        return None


def _append_warning(existing: str, extra: str) -> str:
    base = (existing or "").strip()
    addition = (extra or "").strip()
    if not base:
        return addition
    if not addition or addition in base:
        return base
    return f"{base} {addition}".strip()


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
    system_portal_ip = ""
    system_target_iqn = ""
    if meta:
        try:
            decoded = meta.strip()
            parts = decoded.split("|")
            if len(parts) >= 5:
                mac = parts[0].strip()
                portal_ip = parts[1].strip()
                target_iqn = parts[2].strip()
                system_portal_ip = parts[3].strip()
                system_target_iqn = parts[4].strip()
            elif len(parts) == 3:
                mac = parts[0].strip()
                portal_ip = parts[1].strip()
                target_iqn = parts[2].strip()
        except Exception:
            mac = ""
            portal_ip = ""
            target_iqn = ""
            system_portal_ip = ""
            system_target_iqn = ""

    boot_ip = _env("BOOT_SERVER_IP", "192.168.1.50")
    mac_for_url = (mac or "").strip().lower() or "unknown"
    mac_encoded = quote(mac_for_url, safe=':')
    log_url_base = (
        f"http://{boot_ip}:8000/api/v1/boot/log"
        f"?mac={mac_encoded}&event=winpe_setup_autostart&details="
    )
    setupact_upload_url = (
        f"http://{boot_ip}:8000/api/v1/boot/winpe/logs/upload"
        f"?mac={mac_encoded}&name=setupact.log"
    )
    setuperr_upload_url = (
        f"http://{boot_ip}:8000/api/v1/boot/winpe/logs/upload"
        f"?mac={mac_encoded}&name=setuperr.log"
    )
    startnet_upload_url = (
        f"http://{boot_ip}:8000/api/v1/boot/winpe/logs/upload"
        f"?mac={mac_encoded}&name=startnet.log"
    )

    iscsi_attach_block = """
set INSTALLER_PORTAL={installer_portal}
set INSTALLER_TARGET={installer_target}
set SYSTEM_PORTAL={system_portal}
set SYSTEM_TARGET={system_target}

if not "%SYSTEM_TARGET%"=="" (
    echo Attempting WinPE iSCSI attach for system disk...
    call :attach_iscsi "%SYSTEM_PORTAL%" "%SYSTEM_TARGET%"
)

if not "%INSTALLER_TARGET%"=="" (
    echo Attempting WinPE iSCSI attach for installer media...
    call :attach_iscsi "%INSTALLER_PORTAL%" "%INSTALLER_TARGET%"
)
""".format(
        installer_portal=portal_ip,
        installer_target=target_iqn,
        system_portal=system_portal_ip,
        system_target=system_target_iqn,
    )

    script = f"""@echo off
goto :main

:log_http
set "LOG_URL=%~1"
where powershell.exe >nul 2>&1 && powershell -NoProfile -ExecutionPolicy Bypass -Command "try {{ $wc = New-Object System.Net.WebClient; $null = $wc.DownloadString($env:LOG_URL); exit 0 }} catch {{ exit 1 }}" >nul 2>&1 && exit /b 0
where powershell.exe >nul 2>&1 && powershell -NoProfile -ExecutionPolicy Bypass -Command "try {{ Invoke-WebRequest -UseBasicParsing -Uri $env:LOG_URL -Method Get | Out-Null; exit 0 }} catch {{ exit 1 }}" >nul 2>&1 && exit /b 0
if defined HTTP_HELPER if exist "%HTTP_HELPER%" where cscript.exe >nul 2>&1 && cscript //nologo "%HTTP_HELPER%" get "%LOG_URL%" >nul 2>&1 && exit /b 0
where curl.exe >nul 2>&1 && curl.exe -fsS "%LOG_URL%" >nul 2>&1 && exit /b 0
exit /b 0

:upload_setup
set SETUPACT_PATH=
for %%P in ("X:\Windows\Panther\setupact.log" "X:\$WINDOWS.~BT\Sources\Panther\setupact.log" "C:\$WINDOWS.~BT\Sources\Panther\setupact.log" "C:\Windows\Panther\setupact.log") do (
    if exist %%~P set SETUPACT_PATH=%%~P
)
if defined SETUPACT_PATH (
    call :trace uploading setupact from %SETUPACT_PATH%
    set UPLOAD_OK=
    where powershell.exe >nul 2>&1 && powershell -NoProfile -ExecutionPolicy Bypass -Command "try {{ $wc = New-Object System.Net.WebClient; $null = $wc.UploadFile('{setupact_upload_url}', 'PUT', $env:SETUPACT_PATH); exit 0 }} catch {{ exit 1 }}" >nul 2>&1 && set UPLOAD_OK=1
    if not defined UPLOAD_OK where powershell.exe >nul 2>&1 && powershell -NoProfile -ExecutionPolicy Bypass -Command "try {{ Invoke-WebRequest -UseBasicParsing -Uri '{setupact_upload_url}' -Method Put -InFile $env:SETUPACT_PATH | Out-Null; exit 0 }} catch {{ exit 1 }}" >nul 2>&1 && set UPLOAD_OK=1
    if not defined UPLOAD_OK if defined HTTP_HELPER if exist "%HTTP_HELPER%" where cscript.exe >nul 2>&1 && cscript //nologo "%HTTP_HELPER%" put "{setupact_upload_url}" "%SETUPACT_PATH%" >nul 2>&1 && set UPLOAD_OK=1
    if not defined UPLOAD_OK where curl.exe >nul 2>&1 && curl.exe -fsS -X PUT --data-binary "@%SETUPACT_PATH%" "{setupact_upload_url}" >nul 2>&1 && set UPLOAD_OK=1
    if not defined UPLOAD_OK where bitsadmin.exe >nul 2>&1 && bitsadmin /transfer nb_setupact /upload /priority normal "%SETUPACT_PATH%" "{setupact_upload_url}" >nul 2>&1 && set UPLOAD_OK=1
    if not defined UPLOAD_OK where bitsadmin.exe >nul 2>&1 && bitsadmin /transfer nb_setupact2 /upload /priority normal "{setupact_upload_url}" "%SETUPACT_PATH%" >nul 2>&1 && set UPLOAD_OK=1
    if defined UPLOAD_OK (
        call :log_http "{log_url_base}setupact_uploaded"
    ) else (
        call :log_http "{log_url_base}setupact_upload_failed"
    )
)

set SETUPERR_PATH=
for %%P in ("X:\Windows\Panther\setuperr.log" "X:\$WINDOWS.~BT\Sources\Panther\setuperr.log" "C:\$WINDOWS.~BT\Sources\Panther\setuperr.log" "C:\Windows\Panther\setuperr.log") do (
    if exist %%~P set SETUPERR_PATH=%%~P
)
if defined SETUPERR_PATH (
    call :trace uploading setuperr from %SETUPERR_PATH%
    set ERR_OK=
    where powershell.exe >nul 2>&1 && powershell -NoProfile -ExecutionPolicy Bypass -Command "try {{ $wc = New-Object System.Net.WebClient; $null = $wc.UploadFile('{setuperr_upload_url}', 'PUT', $env:SETUPERR_PATH); exit 0 }} catch {{ exit 1 }}" >nul 2>&1 && set ERR_OK=1
    if not defined ERR_OK where powershell.exe >nul 2>&1 && powershell -NoProfile -ExecutionPolicy Bypass -Command "try {{ Invoke-WebRequest -UseBasicParsing -Uri '{setuperr_upload_url}' -Method Put -InFile $env:SETUPERR_PATH | Out-Null; exit 0 }} catch {{ exit 1 }}" >nul 2>&1 && set ERR_OK=1
    if not defined ERR_OK if defined HTTP_HELPER if exist "%HTTP_HELPER%" where cscript.exe >nul 2>&1 && cscript //nologo "%HTTP_HELPER%" put "{setuperr_upload_url}" "%SETUPERR_PATH%" >nul 2>&1 && set ERR_OK=1
    if not defined ERR_OK where curl.exe >nul 2>&1 && curl.exe -fsS -X PUT --data-binary "@%SETUPERR_PATH%" "{setuperr_upload_url}" >nul 2>&1 && set ERR_OK=1
    if not defined ERR_OK where bitsadmin.exe >nul 2>&1 && bitsadmin /transfer nb_setuperr /upload /priority normal "%SETUPERR_PATH%" "{setuperr_upload_url}" >nul 2>&1 && set ERR_OK=1
    if not defined ERR_OK where bitsadmin.exe >nul 2>&1 && bitsadmin /transfer nb_setuperr2 /upload /priority normal "{setuperr_upload_url}" "%SETUPERR_PATH%" >nul 2>&1 && set ERR_OK=1
    if defined ERR_OK (
        call :log_http "{log_url_base}setuperr_uploaded"
    ) else (
        call :log_http "{log_url_base}setuperr_upload_failed"
    )
)
exit /b 0

:upload_trace_now
if not defined TRACE_ENABLED exit /b 0
if not exist "%TRACE_FILE%" exit /b 0
set TRACE_OK=
where powershell.exe >nul 2>&1 && powershell -NoProfile -ExecutionPolicy Bypass -Command "try {{ Invoke-WebRequest -UseBasicParsing -Uri '{startnet_upload_url}' -Method Put -InFile $env:TRACE_FILE | Out-Null; exit 0 }} catch {{ exit 1 }}" >nul 2>&1 && set TRACE_OK=1
if not defined TRACE_OK if defined HTTP_HELPER if exist "%HTTP_HELPER%" where cscript.exe >nul 2>&1 && cscript //nologo "%HTTP_HELPER%" put "{startnet_upload_url}" "%TRACE_FILE%" >nul 2>&1 && set TRACE_OK=1
if not defined TRACE_OK where curl.exe >nul 2>&1 && curl.exe -fsS -X PUT --data-binary "@%TRACE_FILE%" "{startnet_upload_url}" >nul 2>&1 && set TRACE_OK=1
if not defined TRACE_OK where bitsadmin.exe >nul 2>&1 && bitsadmin /transfer nb_startnet /upload /priority normal "%TRACE_FILE%" "{startnet_upload_url}" >nul 2>&1 && set TRACE_OK=1
if not defined TRACE_OK where bitsadmin.exe >nul 2>&1 && bitsadmin /transfer nb_startnet2 /upload /priority normal "{startnet_upload_url}" "%TRACE_FILE%" >nul 2>&1 && set TRACE_OK=1
if defined TRACE_OK (
    call :log_http "{log_url_base}startnet_uploaded"
) else (
    call :log_http "{log_url_base}startnet_upload_failed"
)
exit /b 0

:main
setlocal EnableExtensions EnableDelayedExpansion
set "TRACE_FILE=X:\\netboot-startnet.log"
set TRACE_ENABLED=1
set "HTTP_HELPER=X:\\nb-http.vbs"
where cscript.exe >nul 2>&1 && if not exist "%HTTP_HELPER%" (
    (
        echo On Error Resume Next
        echo Dim a,m,u,f,x,s
        echo Set a = WScript.Arguments
        echo If a.Count ^< 2 Then WScript.Quit 2
        echo m = LCase^(a^(0^)^)
        echo u = a^(1^)
        echo Set x = CreateObject^("MSXML2.ServerXMLHTTP.6.0"^)
        echo If m = "get" Then
        echo   x.open "GET", u, False
        echo   x.send
        echo   If x.status ^>= 200 And x.status ^< 300 Then WScript.Quit 0 Else WScript.Quit 1
        echo End If
        echo If m = "put" Then
        echo   If a.Count ^< 3 Then WScript.Quit 2
        echo   f = a^(2^)
        echo   Set s = CreateObject^("ADODB.Stream"^)
        echo   s.Type = 1
        echo   s.Open
        echo   s.LoadFromFile f
        echo   x.open "PUT", u, False
        echo   x.setRequestHeader "Content-Type", "text/plain"
        echo   x.send s.Read
        echo   If x.status ^>= 200 And x.status ^< 300 Then WScript.Quit 0 Else WScript.Quit 1
        echo End If
        echo WScript.Quit 2
    ) > "%HTTP_HELPER%"
)
2>nul (echo [startnet] begin %DATE% %TIME% > "%TRACE_FILE%") || set TRACE_ENABLED=
wpeinit
wpeutil InitializeNetwork >nul 2>&1
call :trace wpeinit completed
call :log_http "{log_url_base}winpe_startnet_started"
call :upload_trace_now
echo.
echo ================================================
echo  Netboot Orchestrator - Windows Setup Autostart
echo ================================================
echo Searching for installer media (auto mode)...

{iscsi_attach_block}

call :try_launch_installer E
if not errorlevel 1 goto :done

for /L %%R in (1,1,60) do (
    wpeutil UpdateBootInfo >nul 2>&1
    for %%L in (C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
        call :try_launch_installer %%L
        if not errorlevel 1 goto :done
    )
    ping -n 3 127.0.0.1 >nul 2>&1
)

echo.
echo No installer media with setup.exe found.
call :trace no installer media found
call :u
call :t
echo Opening command prompt for manual troubleshooting.
cmd.exe

:done
call :t
exit /b 0

:log_setup
set DRIVE=%1
set "EVENT_URL={log_url_base}auto_setup_started_drive_%DRIVE%"
call :log_http "!EVENT_URL!"
exit /b 0

:try_launch_installer
set DRIVE=%1
set HAS_SETUP=
set HAS_INSTALL_IMAGE=
set SETUP_PATH=

if exist %DRIVE%:\setup.exe (
    set HAS_SETUP=1
    set SETUP_PATH=%DRIVE%:\setup.exe
)
if exist %DRIVE%:\sources\setup.exe (
    set HAS_SETUP=1
    if not defined SETUP_PATH set SETUP_PATH=%DRIVE%:\sources\setup.exe
)

if not defined HAS_SETUP exit /b 1

if exist %DRIVE%:\sources\install.wim set HAS_INSTALL_IMAGE=1
if exist %DRIVE%:\sources\install.esd set HAS_INSTALL_IMAGE=1
for %%I in (%DRIVE%:\sources\install*.swm) do (
    if exist %%~I set HAS_INSTALL_IMAGE=1
)

if not defined HAS_INSTALL_IMAGE (
    call :trace skip drive %DRIVE%: setup found but no install.wim/esd/swm
    exit /b 1
)

echo Found installer media on %DRIVE%:
call :trace launching setup from %SETUP_PATH%
call :s %DRIVE%
call :u
call :t
start "" %SETUP_PATH%
set SETUP_EXIT=running
for /L %%S in (1,1,180) do (
    ping -n 6 127.0.0.1 >nul 2>&1
    set /a HEARTBEAT_MOD=%%S %% 6
    if !HEARTBEAT_MOD! EQU 0 call :log_http "{log_url_base}setup_running_tick_%%S"
    call :u
    call :t
    where tasklist.exe >nul 2>&1
    if not errorlevel 1 (
        tasklist /FI "IMAGENAME eq setup.exe" 2>nul | find /I "setup.exe" >nul 2>&1
        if errorlevel 1 goto :setup_done
    )
)

:setup_done
call :u
call :t
call :log_setup_exit !SETUP_EXIT!
exit /b 0

:s
set DRIVE=%1
set "EVENT_URL={log_url_base}auto_setup_started_drive_%DRIVE%"
call :log_http "!EVENT_URL!"
exit /b 0

:u
call :upload_setupact
exit /b 0

:t
call :upload_trace
exit /b 0

:attach_iscsi
set PORTAL=%~1
set TARGET=%~2
if "%PORTAL%"=="" set PORTAL={boot_ip}
if "%TARGET%"=="" exit /b 0
where iscsicli.exe >nul 2>&1
if errorlevel 1 (
    call :trace iscsicli.exe unavailable in this WinPE
    exit /b 0
)
call :trace attach iscsi target=%TARGET% portal=%PORTAL%
iscsicli QAddTargetPortal %PORTAL% 3260 >nul 2>&1
iscsicli AddTargetPortal %PORTAL% 3260 >nul 2>&1
iscsicli QLoginTarget %TARGET% >nul 2>&1
iscsicli LoginTarget %TARGET% T * * * * * * * * * * * * * * * 0 >nul 2>&1
ping -n 3 127.0.0.1 >nul 2>&1
wpeutil UpdateBootInfo >nul 2>&1
exit /b 0

:trace
if not defined TRACE_ENABLED exit /b 0
echo [startnet] %DATE% %TIME% - %*>> %TRACE_FILE%
exit /b 0

:log_setup_exit
set EXIT_CODE=%1
set "EVENT_URL={log_url_base}setup_process_exit_code_%EXIT_CODE%"
call :log_http "!EVENT_URL!"
exit /b 0

:log_setup
set DRIVE=%1
set "EVENT_URL={log_url_base}auto_setup_started_drive_%DRIVE%"
call :log_http "!EVENT_URL!"
exit /b 0

:upload_setup
call :upload_setupact
exit /b 0

:upload_trace_now
call :upload_trace
exit /b 0

:upload_setupact
set SETUPACT_PATH=
for %%P in ("X:\Windows\Panther\setupact.log" "X:\$WINDOWS.~BT\Sources\Panther\setupact.log" "C:\$WINDOWS.~BT\Sources\Panther\setupact.log" "C:\Windows\Panther\setupact.log") do (
    if exist %%~P set SETUPACT_PATH=%%~P
)
if defined SETUPACT_PATH (
    call :trace uploading setupact from %SETUPACT_PATH%
    set UPLOAD_OK=
    where powershell.exe >nul 2>&1 && powershell -NoProfile -ExecutionPolicy Bypass -Command "try {{ $wc = New-Object System.Net.WebClient; $null = $wc.UploadFile('{setupact_upload_url}', 'PUT', $env:SETUPACT_PATH); exit 0 }} catch {{ exit 1 }}" >nul 2>&1 && set UPLOAD_OK=1
    if not defined UPLOAD_OK where powershell.exe >nul 2>&1 && powershell -NoProfile -ExecutionPolicy Bypass -Command "try {{ Invoke-WebRequest -UseBasicParsing -Uri '{setupact_upload_url}' -Method Put -InFile $env:SETUPACT_PATH | Out-Null; exit 0 }} catch {{ exit 1 }}" >nul 2>&1 && set UPLOAD_OK=1
    if not defined UPLOAD_OK where curl.exe >nul 2>&1 && curl.exe -fsS -X PUT --data-binary "@%SETUPACT_PATH%" "{setupact_upload_url}" >nul 2>&1 && set UPLOAD_OK=1
    if not defined UPLOAD_OK where bitsadmin.exe >nul 2>&1 && bitsadmin /transfer nb_setupact /upload /priority normal "%SETUPACT_PATH%" "{setupact_upload_url}" >nul 2>&1 && set UPLOAD_OK=1
    if not defined UPLOAD_OK where bitsadmin.exe >nul 2>&1 && bitsadmin /transfer nb_setupact2 /upload /priority normal "{setupact_upload_url}" "%SETUPACT_PATH%" >nul 2>&1 && set UPLOAD_OK=1
    if defined UPLOAD_OK (
        call :log_http "{log_url_base}setupact_uploaded"
    ) else (
        call :log_http "{log_url_base}setupact_upload_failed"
    )
)

set SETUPERR_PATH=
for %%P in ("X:\Windows\Panther\setuperr.log" "X:\$WINDOWS.~BT\Sources\Panther\setuperr.log" "C:\$WINDOWS.~BT\Sources\Panther\setuperr.log" "C:\Windows\Panther\setuperr.log") do (
    if exist %%~P set SETUPERR_PATH=%%~P
)
if defined SETUPERR_PATH (
    call :trace uploading setuperr from %SETUPERR_PATH%
    set ERR_OK=
    where powershell.exe >nul 2>&1 && powershell -NoProfile -ExecutionPolicy Bypass -Command "try {{ $wc = New-Object System.Net.WebClient; $null = $wc.UploadFile('{setuperr_upload_url}', 'PUT', $env:SETUPERR_PATH); exit 0 }} catch {{ exit 1 }}" >nul 2>&1 && set ERR_OK=1
    if not defined ERR_OK where powershell.exe >nul 2>&1 && powershell -NoProfile -ExecutionPolicy Bypass -Command "try {{ Invoke-WebRequest -UseBasicParsing -Uri '{setuperr_upload_url}' -Method Put -InFile $env:SETUPERR_PATH | Out-Null; exit 0 }} catch {{ exit 1 }}" >nul 2>&1 && set ERR_OK=1
    if not defined ERR_OK where curl.exe >nul 2>&1 && curl.exe -fsS -X PUT --data-binary "@%SETUPERR_PATH%" "{setuperr_upload_url}" >nul 2>&1 && set ERR_OK=1
    if not defined ERR_OK where bitsadmin.exe >nul 2>&1 && bitsadmin /transfer nb_setuperr /upload /priority normal "%SETUPERR_PATH%" "{setuperr_upload_url}" >nul 2>&1 && set ERR_OK=1
    if not defined ERR_OK where bitsadmin.exe >nul 2>&1 && bitsadmin /transfer nb_setuperr2 /upload /priority normal "{setuperr_upload_url}" "%SETUPERR_PATH%" >nul 2>&1 && set ERR_OK=1
    if defined ERR_OK (
        call :log_http "{log_url_base}setuperr_uploaded"
    ) else (
        call :log_http "{log_url_base}setuperr_upload_failed"
    )
)
exit /b 0

:upload_trace
if not defined TRACE_ENABLED exit /b 0
if not exist "%TRACE_FILE%" exit /b 0
set TRACE_OK=
where powershell.exe >nul 2>&1 && powershell -NoProfile -ExecutionPolicy Bypass -Command "try {{ Invoke-WebRequest -UseBasicParsing -Uri '{startnet_upload_url}' -Method Put -InFile $env:TRACE_FILE | Out-Null; exit 0 }} catch {{ exit 1 }}" >nul 2>&1 && set TRACE_OK=1
if not defined TRACE_OK where curl.exe >nul 2>&1 && curl.exe -fsS -X PUT --data-binary "@%TRACE_FILE%" "{startnet_upload_url}" >nul 2>&1 && set TRACE_OK=1
if not defined TRACE_OK where bitsadmin.exe >nul 2>&1 && bitsadmin /transfer nb_startnet /upload /priority normal "%TRACE_FILE%" "{startnet_upload_url}" >nul 2>&1 && set TRACE_OK=1
if not defined TRACE_OK where bitsadmin.exe >nul 2>&1 && bitsadmin /transfer nb_startnet2 /upload /priority normal "{startnet_upload_url}" "%TRACE_FILE%" >nul 2>&1 && set TRACE_OK=1
if defined TRACE_OK (
    call :log_http "{log_url_base}startnet_uploaded"
) else (
    call :log_http "{log_url_base}startnet_upload_failed"
)
exit /b 0

:log_http
set "LOG_URL=%~1"
where powershell.exe >nul 2>&1 && powershell -NoProfile -ExecutionPolicy Bypass -Command "try {{ $wc = New-Object System.Net.WebClient; $null = $wc.DownloadString($env:LOG_URL); exit 0 }} catch {{ exit 1 }}" >nul 2>&1 && exit /b 0
where powershell.exe >nul 2>&1 && powershell -NoProfile -ExecutionPolicy Bypass -Command "try {{ Invoke-WebRequest -UseBasicParsing -Uri $env:LOG_URL -Method Get | Out-Null; exit 0 }} catch {{ exit 1 }}" >nul 2>&1 && exit /b 0
if defined HTTP_HELPER if exist "%HTTP_HELPER%" where cscript.exe >nul 2>&1 && cscript //nologo "%HTTP_HELPER%" get "%LOG_URL%" >nul 2>&1 && exit /b 0
where curl.exe >nul 2>&1 && curl.exe -fsS "%LOG_URL%" >nul 2>&1 && exit /b 0
exit /b 0
"""
    return PlainTextResponse(script)


@router.get("/winpe/winpeshl.ini")
async def winpe_winpeshl_ini():
    """Force WinPE shell flow to launch our startnet script."""
    content = """[LaunchApps]
%SYSTEMROOT%\\System32\\startnet.cmd
"""
    return PlainTextResponse(content)


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


def _winpe_logs_root() -> Path:
    return Path(_env("WINPE_LOGS_PATH", "/data/winpe-logs"))


def _logo_candidates() -> list[Path]:
    repo_root = Path(__file__).parent.parent.parent.parent
    return [
        Path("/app/docs/logo.png"),
        repo_root / "docs" / "logo.png",
        Path("/data/logo.png"),
    ]


@router.get("/ipxe/logo.png")
async def ipxe_logo_png():
    """Serve branding logo for iPXE menu background when available."""
    for candidate in _logo_candidates():
        if candidate.exists() and candidate.is_file():
            return FileResponse(path=candidate, media_type="image/png", filename="logo.png")
    raise HTTPException(status_code=404, detail="Logo not found")


def _mac_log_dir(mac: str) -> Path:
    normalized = _normalize_mac(mac)
    if len(normalized) != 12:
        raise HTTPException(status_code=400, detail="Invalid MAC")
    dashed = "-".join(normalized[i:i+2] for i in range(0, 12, 2))
    return _winpe_logs_root() / dashed


@router.put("/winpe/logs/upload")
@router.post("/winpe/logs/upload")
async def upload_winpe_log(
    request: Request,
    mac: str = Query(...),
    name: str = Query("setupact.log"),
    db: Database = Depends(get_db),
):
    """Upload WinPE log content (e.g. setupact.log) for a specific MAC."""
    if not name or Path(name).name != name:
        raise HTTPException(status_code=400, detail="Invalid log filename")

    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="Empty log content")

    log_dir = _mac_log_dir(mac)
    log_dir.mkdir(parents=True, exist_ok=True)
    target_file = log_dir / name
    target_file.write_bytes(content)

    db.add_boot_log(mac, "winpe_log_upload", f"{name} uploaded ({len(content)} bytes)")

    lower_name = name.lower()
    raw_text = ""
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            raw_text = content.decode(encoding, errors="ignore")
            if raw_text:
                break
        except Exception:
            continue

    if raw_text:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        tail = lines[-600:]

        if lower_name in {"setupact.log", "setuperr.log"}:
            pattern = re.compile(r"(error|failed|failure|cannot|0x[0-9a-f]+|rollback|abort)", re.IGNORECASE)
            hints = []
            for line in tail:
                if pattern.search(line):
                    compact = re.sub(r"\s+", " ", line)
                    if compact not in hints:
                        hints.append(compact[:320])
                if len(hints) >= 5:
                    break

            if hints:
                for hint in hints:
                    db.add_boot_log(mac, "winpe_setup_hint", f"{name}: {hint}")
            else:
                db.add_boot_log(mac, "winpe_setup_hint", f"{name}: no explicit error keywords found in recent log tail")

            latest = re.sub(r"\s+", " ", tail[-1])[:320] if tail else ""
            if latest:
                db.add_boot_log(mac, "winpe_setup_status", f"{name}: {latest}")

        elif lower_name == "startnet.log":
            status_pattern = re.compile(
                r"(wpeinit|searching for installer media|found installer media|launching setup|"
                r"attach|skip drive|no installer media|upload.*failed|setup process exit)",
                re.IGNORECASE,
            )
            candidates = [re.sub(r"\s+", " ", ln)[:320] for ln in tail if status_pattern.search(ln)]
            if candidates:
                db.add_boot_log(mac, "winpe_startnet_status", f"startnet.log: {candidates[-1]}")
            else:
                latest = re.sub(r"\s+", " ", tail[-1])[:320] if tail else ""
                if latest:
                    db.add_boot_log(mac, "winpe_startnet_status", f"startnet.log: {latest}")

    return {"success": True, "name": name, "size_bytes": len(content)}


@router.get("/winpe/logs")
async def list_winpe_logs(mac: str = Query(...)):
    """List uploaded WinPE logs for a specific MAC."""
    log_dir = _mac_log_dir(mac)
    if not log_dir.exists():
        return []

    files = []
    for entry in sorted(log_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
        if not entry.is_file():
            continue
        stat = entry.stat()
        files.append({
            "name": entry.name,
            "size_bytes": stat.st_size,
            "modified_at": stat.st_mtime,
        })
    return files


@router.get("/winpe/logs/download")
async def download_winpe_log(mac: str = Query(...), name: str = Query("setupact.log")):
    """Download a WinPE log file for a specific MAC."""
    if not name or Path(name).name != name:
        raise HTTPException(status_code=400, detail="Invalid log filename")

    target_file = _mac_log_dir(mac) / name
    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(status_code=404, detail="Log file not found")

    return FileResponse(path=target_file, filename=f"{_normalize_mac(mac)}-{name}", media_type="text/plain")

# =====================================================================
#  MAIN BOOT MENU
# =====================================================================

@router.get("/ipxe/menu")
async def boot_ipxe_main_menu(db: Database = Depends(get_db)):
    """Main iPXE boot menu — entry point for all PXE clients."""
    version = get_version()
    base = _menu_base_url()
    boot_ip = _env("BOOT_SERVER_IP", "192.168.1.50")
    logo_url = f"http://{boot_ip}:8000/api/v1/boot/ipxe/logo.png"

    # Log boot event
    db.add_boot_log("unknown", "menu_loaded", "Main menu loaded")

    script = f"""#!ipxe
# {BRANDING}
console --picture {logo_url} ||

:main_menu
menu ======== Netboot Orchestrator v{version} ========
item --gap --
item --gap --  Designed by Kenneth Kronborg AI Team
item --gap --
item --gap --  SYSTEM
item --gap --  MAC      : ${{net0/mac}}
item --gap --  IP       : ${{net0/ip}}
item --gap --  GATEWAY  : ${{net0/gateway}}
item --gap --
item --gap --  DEPLOYMENT
item os_install    OS Installers                    >>
item create_iscsi  Create iSCSI Image               >>
item link_iscsi    Link Device to iSCSI Image       >>
item boot_iscsi    Boot from iSCSI
item win_install   Windows Install (WinPE + iSCSI)  >>
item --gap --
item --gap --  TOOLS
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
    echo  Loading Windows installer selection...
echo
echo ================================================
echo
    prompt Press any key to continue to Windows Install...
    chain {base}/ipxe/windows-select?mac={quote(mac, safe='')} || chain {base}/ipxe/menu
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
    request: Request = None,
    db: Database = Depends(get_db),
):
    """Boot Windows installer via WinPE/wimboot while attaching linked iSCSI disk."""
    base = _menu_base_url()
    iscsi = get_iscsi_service()
    boot_ip = _env("BOOT_SERVER_IP", "192.168.1.50")

    winpe_root = _env("WINDOWS_WINPE_PATH", "winpe").strip().strip("/")
    os_installers_path = Path(_env("OS_INSTALLERS_PATH", "/data/os-installers"))
    logger.info(f"Windows install requested: mac={mac} boot_ip={boot_ip} winpe_root={winpe_root} os_installers_path={os_installers_path}")
    transfer_session_id = ""
    if mac:
        reset_state = db.reset_device_transfer(mac)
        transfer_session_id = (reset_state or {}).get("session_id", "")
        db.add_boot_log(
            mac,
            "transfer_reset",
            f"Reset HTTP/iSCSI counters for new Windows install session sid={transfer_session_id or 'none'}",
        )
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
    system_portal_ip, system_target_iqn = _parse_iscsi_san_url(san_url)
    sanhook_cmd = " || ".join([f"sanhook --drive 0x80 {url}" for url in san_urls])
    logger.info(
        f"Windows install image resolved: mac={mac} image_id={device_image.get('id')} target={target_name} "
        f"san_candidates={san_urls}"
    )

    mac_encoded = quote(mac or "", safe='')
    sid_encoded = quote(transfer_session_id, safe='') if transfer_session_id else ""
    query_parts = []
    if mac_encoded:
        query_parts.append(f"mac={mac_encoded}")
    if sid_encoded:
        query_parts.append(f"sid={sid_encoded}")
    mac_qs = f"?{'&'.join(query_parts)}" if query_parts else ""
    wimboot_url = f"http://{boot_ip}:8000/api/v1/os-installers/download/{quote(required_rel[0], safe='/')}{mac_qs}"
    bcd_url = f"http://{boot_ip}:8000/api/v1/os-installers/download/{quote(required_rel[1], safe='/')}{mac_qs}"
    sdi_url = f"http://{boot_ip}:8000/api/v1/os-installers/download/{quote(required_rel[2], safe='/')}{mac_qs}"
    wim_url = f"http://{boot_ip}:8000/api/v1/os-installers/download/{quote(required_rel[3], safe='/')}{mac_qs}"
    installer_meta_portal = ""
    installer_meta_iqn = ""
    winpeshl_url = f"http://{boot_ip}:8000/api/v1/boot/winpe/winpeshl.ini"
    iso_hook_cmd = ""
    iso_info_line = ""
    installer_iso_url = ""
    installer_log_value = installer_iso_path or installer_iso_san_url or "none"
    installer_mode = "none"

    if installer_iso_san_url:
        iso_hook_cmd = (
            f"sanhook --drive 0xE0 {installer_iso_san_url} "
            f"|| sanhook --drive 0x81 {installer_iso_san_url} "
            f"|| echo  !! Optional installer media SAN attach failed in iPXE; WinPE will retry."
        )
        iso_info_line = f"echo  Installer media (0xE0/0x81): {installer_iso_san_url}"
        installer_log_value = installer_iso_san_url
        installer_mode = "san_url"
        portal_ip, target_iqn = _parse_iscsi_san_url(installer_iso_san_url)
        if portal_ip and target_iqn:
            installer_meta_portal = portal_ip
            installer_meta_iqn = target_iqn
        logger.info(f"Windows install optional ISO SAN configured: {installer_iso_san_url}")
    elif installer_iso_path:
        installer_full_path = os_installers_path / installer_iso_path
        installer_iso_url = (
            f"http://{boot_ip}:8000/api/v1/os-installers/download/"
            f"{quote(installer_iso_path, safe='/')}{mac_qs}"
        )
        ensure_iso = iscsi.ensure_installer_iso_target(installer_iso_path, installer_full_path)
        if ensure_iso.get("success"):
            installer_iso_san_url = ensure_iso.get("san_url", "")
            iso_hook_cmd = (
                f"sanhook --drive 0xE0 {installer_iso_san_url} "
                f"|| sanhook --drive 0x81 {installer_iso_san_url} "
                f"|| echo  !! Optional installer media SAN attach failed in iPXE; WinPE will retry."
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
                installer_meta_portal = portal_ip
                installer_meta_iqn = target_iqn
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
    startnet_meta = quote(
        f"{mac}|{installer_meta_portal}|{installer_meta_iqn}|{system_portal_ip}|{system_target_iqn}",
        safe=''
    )
    startnet_url = f"http://{boot_ip}:8000/api/v1/boot/winpe/startnet.cmd?meta={startnet_meta}"

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
        f"WinPE install boot via {target_name} (normalized_mac={normalized_mac}); installer={installer_log_value}; mode={installer_mode}; startnet_meta=installer:{installer_meta_iqn or 'none'} system:{system_target_iqn or 'none'}",
        request.client.host if request and request.client else "",
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
{sanhook_cmd} || echo  !! System iSCSI SAN attach failed in iPXE; WinPE will retry via iSCSI initiator.

{iso_hook_cmd}

echo Loading WinPE via wimboot...
kernel {wimboot_url} || goto windows_failed
initrd {bcd_url} BCD || goto windows_failed
initrd {sdi_url} boot.sdi || goto windows_failed
initrd {wim_url} boot.wim || goto windows_failed
initrd {startnet_url} startnet.cmd || goto windows_failed
initrd {startnet_url} Windows/System32/startnet.cmd || goto windows_failed
initrd {startnet_url} windows/system32/startnet.cmd || goto windows_failed
initrd {winpeshl_url} winpeshl.ini || goto windows_failed
initrd {winpeshl_url} Windows/System32/winpeshl.ini || goto windows_failed
initrd {winpeshl_url} windows/system32/winpeshl.ini || goto windows_failed
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
@router.get("/log")
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
    since: str = Query(None),
    db: Database = Depends(get_db),
):
    """Get boot logs, optionally filtered by MAC."""
    return db.get_boot_logs(mac=mac, limit=limit, since=since)


@router.get("/devices/{mac}/metrics")
async def get_device_metrics(mac: str, db: Database = Depends(get_db)):
    """Get connection/network/disk metrics for a specific device (best effort)."""
    device = db.get_device(mac)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    image_id = device.get("image_id")
    if not image_id:
        transfer = db.get_device_transfer(mac)
        return {
            "mac": mac,
            "name": device.get("name"),
            "image_id": None,
            "linked": False,
            "message": "No iSCSI image linked",
            "boot_transfer": {
                "http_tx_bytes": int((transfer or {}).get("http_tx_bytes", 0) or 0),
                "http_requests": int((transfer or {}).get("http_requests", 0) or 0),
                "last_path": (transfer or {}).get("last_path", ""),
                "last_seen": (transfer or {}).get("last_seen", ""),
                "last_remote_ip": (transfer or {}).get("last_remote_ip", ""),
            },
        }

    iscsi = get_iscsi_service()
    metrics = iscsi.get_image_connection_metrics(image_id)
    if not metrics.get("success"):
        raise HTTPException(status_code=400, detail=metrics.get("error", "Unable to fetch metrics"))

    transfer = db.get_device_transfer(mac)
    if transfer:
        fallback_remote_ip = (transfer.get("last_remote_ip") or "").strip()
        metrics["boot_transfer"] = {
            "http_tx_bytes": int(transfer.get("http_tx_bytes", 0) or 0),
            "http_requests": int(transfer.get("http_requests", 0) or 0),
            "last_path": transfer.get("last_path", ""),
            "last_seen": transfer.get("last_seen", ""),
            "last_remote_ip": transfer.get("last_remote_ip", ""),
            "session_started_at": transfer.get("session_started_at", ""),
        }

        connection = metrics.get("connection") or {}
        existing_ips = list(connection.get("remote_ips") or [])
        if fallback_remote_ip and not existing_ips:
            existing_ips.append(fallback_remote_ip)
            connection["remote_ips"] = existing_ips
            metrics["connection"] = connection

        if metrics.get("network", {}).get("source") == "unavailable":
            metrics["network"] = {
                "rx_bytes": None,
                "tx_bytes": int(transfer.get("http_tx_bytes", 0) or 0),
                "source": "http_transfer_aggregate",
            }

            metrics["warning"] = (
                "Per-device iSCSI byte counters unavailable; showing MAC-attributed HTTP download bytes instead."
            )

    metrics["mac"] = mac
    metrics["name"] = device.get("name")
    metrics["linked"] = True

    transfer = transfer or {}
    now = datetime.now().astimezone()
    now_iso = now.isoformat()
    stall_threshold_seconds = max(int(_env("INSTALL_STALL_THRESHOLD_SECONDS", "180") or 180), 30)

    network = metrics.get("network") or {}
    disk_io = metrics.get("disk_io") or {}
    connection = metrics.get("connection") or {}

    recent_transfer_window_seconds = max(int(_env("METRICS_RECENT_TRANSFER_SECONDS", "300") or 300), 30)
    last_transfer_seen = (transfer.get("last_seen") or "").strip()
    last_transfer_dt = _parse_iso_timestamp(last_transfer_seen)
    if last_transfer_dt is not None and last_transfer_dt.tzinfo is None:
        last_transfer_dt = last_transfer_dt.astimezone()
    has_recent_transfer = (
        last_transfer_dt is not None and
        (
            int(transfer.get("http_requests", 0) or 0) > 0
            or int(transfer.get("iscsi_requests", 0) or 0) > 0
        ) and
        int((now - last_transfer_dt).total_seconds()) <= recent_transfer_window_seconds
    )

    owner_window_seconds = max(int(_env("METRICS_IP_OWNER_WINDOW_SECONDS", "7200") or 7200), 300)

    def _resolve_ip_owner_mac(remote_ip: str) -> str:
        candidate_ip = (remote_ip or "").strip()
        if not candidate_ip:
            return ""

        owner_mac = ""
        owner_start_dt = None
        for dev in db.get_all_devices():
            dev_mac = (dev.get("mac") or "").strip().lower()
            if not dev_mac:
                continue

            dev_transfer = db.get_device_transfer(dev_mac)
            if not dev_transfer:
                continue

            if (dev_transfer.get("last_remote_ip") or "").strip() != candidate_ip:
                continue

            if int(dev_transfer.get("http_requests", 0) or 0) <= 0:
                continue

            started_raw = (dev_transfer.get("session_started_at") or "").strip()
            started_dt = _parse_iso_timestamp(started_raw)
            if started_dt is None:
                continue
            if started_dt.tzinfo is None:
                started_dt = started_dt.astimezone()

            age_seconds = int((now - started_dt).total_seconds())
            if age_seconds > owner_window_seconds:
                continue

            if owner_start_dt is None or started_dt > owner_start_dt:
                owner_start_dt = started_dt
                owner_mac = dev_mac

        return owner_mac

    def _is_unique_recent_ip_owner(remote_ip: str) -> bool:
        candidate_ip = (remote_ip or "").strip()
        if not candidate_ip:
            return False

        for other in db.get_all_devices():
            other_mac = (other.get("mac") or "").strip().lower()
            if not other_mac or other_mac == mac.lower():
                continue

            other_transfer = db.get_device_transfer(other_mac)
            if not other_transfer:
                continue

            other_ip = (other_transfer.get("last_remote_ip") or "").strip()
            if other_ip != candidate_ip:
                continue

            other_seen_raw = (other_transfer.get("last_seen") or "").strip()
            other_seen_dt = _parse_iso_timestamp(other_seen_raw)
            if other_seen_dt is None:
                continue
            if other_seen_dt.tzinfo is None:
                other_seen_dt = other_seen_dt.astimezone()

            age_seconds = int((now - other_seen_dt).total_seconds())
            if age_seconds <= recent_transfer_window_seconds:
                return False

        return True

    if bool(connection.get("active")) and has_recent_transfer and metrics.get("network", {}).get("source") in {"unavailable", "http_transfer_aggregate"}:
        candidate_ip = (transfer.get("last_remote_ip") or "").strip()
        remote_ips = list((connection or {}).get("remote_ips") or [])
        if not candidate_ip and len(remote_ips) == 1:
            candidate_ip = remote_ips[0]

        if candidate_ip and _is_unique_recent_ip_owner(candidate_ip):
            socket_stats = iscsi.get_iscsi_socket_counters()
            entry = socket_stats.get(candidate_ip) or {}
            hinted_rx = int(entry.get("rx_bytes", 0) or 0)
            hinted_tx = int(entry.get("tx_bytes", 0) or 0)
            if hinted_rx > 0 or hinted_tx > 0:
                metrics["network"] = {
                    "rx_bytes": hinted_rx,
                    "tx_bytes": hinted_tx,
                    "source": "socket_counters_mac_hint",
                }
                if metrics.get("disk_io", {}).get("source") == "unavailable":
                    metrics["disk_io"] = {
                        "read_bytes": hinted_tx,
                        "write_bytes": hinted_rx,
                        "source": "socket_counters_mac_hint_estimate",
                    }
                metrics["attribution_confidence"] = "medium"

    connection = metrics.get("connection") or {}
    remote_ips = list(connection.get("remote_ips") or [])
    owner_ip = remote_ips[0] if remote_ips else (transfer.get("last_remote_ip") or "").strip()
    resolved_owner_mac = _resolve_ip_owner_mac(owner_ip).lower() if owner_ip else ""
    current_mac_normalized = (mac or "").strip().lower()

    if resolved_owner_mac and resolved_owner_mac != current_mac_normalized:
        connection["active"] = False
        connection["session_count"] = 0
        connection["remote_ips"] = []
        metrics["connection"] = connection

        metrics["network"] = {
            "rx_bytes": None,
            "tx_bytes": None,
            "source": "unavailable",
        }
        if metrics.get("disk_io", {}).get("source") != "target_stats":
            metrics["disk_io"] = {
                "read_bytes": None,
                "write_bytes": None,
                "source": "unavailable",
            }

        metrics["warning"] = _append_warning(
            metrics.get("warning", ""),
            f"Remote IP {owner_ip} is currently attributed to device {resolved_owner_mac}; hiding stale metrics for this device.",
        )

    network = metrics.get("network") or {}
    disk_io = metrics.get("disk_io") or {}
    connection = metrics.get("connection") or {}
    attribution_confidence = (metrics.get("attribution_confidence") or "unknown").strip().lower()
    stall_measurement_allowed = attribution_confidence in {"high", "medium"}

    if bool(connection.get("active")) and attribution_confidence != "high" and not has_recent_transfer:
        connection["active"] = False
        connection["session_count"] = 0
        connection["remote_ips"] = []
        metrics["connection"] = connection

        if metrics.get("network", {}).get("source") == "http_transfer_aggregate":
            metrics["network"] = {
                "rx_bytes": None,
                "tx_bytes": None,
                "source": "unavailable",
            }

        metrics["warning"] = _append_warning(
            metrics.get("warning", ""),
            "Stale unattributed iSCSI session hidden for this device (no recent device-local transfer activity).",
        )

    observed_total_bytes = None
    observed_source = "none"
    rx = network.get("rx_bytes")
    tx = network.get("tx_bytes")
    if isinstance(rx, int) and isinstance(tx, int):
        observed_total_bytes = int(rx) + int(tx)
        observed_source = "network_total"
    else:
        read_bytes = disk_io.get("read_bytes")
        write_bytes = disk_io.get("write_bytes")
        if isinstance(read_bytes, int) and isinstance(write_bytes, int):
            observed_total_bytes = int(read_bytes) + int(write_bytes)
            observed_source = "disk_total"
        elif isinstance(write_bytes, int):
            observed_total_bytes = int(write_bytes)
            observed_source = "disk_write_only"
        elif isinstance(tx, int):
            observed_total_bytes = int(tx)
            observed_source = "network_tx_only"
        elif isinstance(transfer.get("http_tx_bytes"), int):
            observed_total_bytes = int(transfer.get("http_tx_bytes") or 0)
            observed_source = "http_fallback"

    previous_total = transfer.get("stall_last_total_bytes")
    if not isinstance(previous_total, int):
        previous_total = None

    last_progress_at = transfer.get("stall_last_progress_at")
    last_progress_dt = _parse_iso_timestamp(last_progress_at)
    if last_progress_dt is not None and last_progress_dt.tzinfo is None:
        last_progress_dt = last_progress_dt.astimezone()

    stall_state = (transfer.get("stall_state") or "idle").strip().lower()
    active_session = bool(connection.get("active"))
    has_progress = False
    stall_seconds = 0
    stalled = False
    progress_log_every_seconds = max(int(_env("INSTALL_PROGRESS_LOG_INTERVAL_SECONDS", "30") or 30), 10)

    session_started_at = (transfer.get("session_started_at") or "").strip()
    session_started_dt = _parse_iso_timestamp(session_started_at)
    if session_started_dt is not None and session_started_dt.tzinfo is None:
        session_started_dt = session_started_dt.astimezone()

    last_progress_log_at = (transfer.get("stall_last_progress_log_at") or "").strip()
    last_progress_log_dt = _parse_iso_timestamp(last_progress_log_at)
    if last_progress_log_dt is not None and last_progress_log_dt.tzinfo is None:
        last_progress_log_dt = last_progress_log_dt.astimezone()

    try:
        log_dir = _mac_log_dir(mac)
        has_winpe_logs = log_dir.exists() and any(entry.is_file() for entry in log_dir.glob("*"))
    except Exception:
        has_winpe_logs = False

    winpe_missing_logged_at = (transfer.get("winpe_missing_logged_at") or "").strip()
    winpe_missing_log_threshold_seconds = max(int(_env("WINPE_LOG_MISSING_THRESHOLD_SECONDS", "120") or 120), 30)

    if observed_source == "http_fallback":
        stall_measurement_allowed = False

    if active_session and observed_total_bytes is not None and stall_measurement_allowed:
        if previous_total is None:
            has_progress = True
            last_progress_at = now_iso
            db.update_device_transfer_fields(mac, {
                "stall_last_total_bytes": observed_total_bytes,
                "stall_last_progress_at": now_iso,
                "stall_state": "active",
            })
        elif observed_total_bytes > previous_total:
            has_progress = True
            last_progress_at = now_iso
            delta_bytes = observed_total_bytes - previous_total
            db.update_device_transfer_fields(mac, {
                "stall_last_total_bytes": observed_total_bytes,
                "stall_last_progress_at": now_iso,
                "stall_state": "active",
            })

            should_log_progress = (
                last_progress_log_dt is None
                or int((now - last_progress_log_dt).total_seconds()) >= progress_log_every_seconds
            )
            if should_log_progress:
                db.add_boot_log(
                    mac,
                    "windows_install_progress",
                    f"I/O +{delta_bytes} bytes ({observed_source}); total={observed_total_bytes} bytes",
                )
                db.update_device_transfer_fields(mac, {
                    "stall_last_progress_log_at": now_iso,
                })

            if stall_state == "stalled":
                db.add_boot_log(mac, "windows_install_resumed", f"I/O resumed after stall ({observed_source})")
        else:
            if last_progress_dt is None:
                last_progress_dt = now
                last_progress_at = now_iso
                db.update_device_transfer_fields(mac, {
                    "stall_last_progress_at": now_iso,
                    "stall_last_total_bytes": observed_total_bytes,
                    "stall_state": "active",
                })
            stall_seconds = max(int((now - last_progress_dt).total_seconds()), 0)
            stalled = stall_seconds >= stall_threshold_seconds
            db.update_device_transfer_fields(mac, {
                "stall_last_total_bytes": observed_total_bytes,
                "stall_state": "stalled" if stalled else "active",
            })
            if stalled and stall_state != "stalled":
                db.add_boot_log(
                    mac,
                    "windows_install_stalled",
                    f"No byte delta for {stall_seconds}s while iSCSI session is active ({observed_source})",
                )
    elif not active_session:
        db.update_device_transfer_fields(mac, {"stall_state": "idle"})
    elif active_session and not stall_measurement_allowed:
        db.update_device_transfer_fields(mac, {"stall_state": "active_unattributed"})

    if active_session and not has_winpe_logs and session_started_dt is not None:
        session_age_seconds = max(int((now - session_started_dt).total_seconds()), 0)
        if session_age_seconds >= winpe_missing_log_threshold_seconds and not winpe_missing_logged_at:
            db.add_boot_log(
                mac,
                "winpe_log_missing",
                f"No WinPE log files uploaded after {session_age_seconds}s from session start",
            )
            db.update_device_transfer_fields(mac, {"winpe_missing_logged_at": now_iso})

    if active_session and observed_total_bytes is not None and not has_progress and not stalled and last_progress_dt is not None:
        stall_seconds = max(int((now - last_progress_dt).total_seconds()), 0)

    metrics["install_progress"] = {
        "active_session": active_session,
        "stalled": stalled,
        "stall_seconds": stall_seconds,
        "threshold_seconds": stall_threshold_seconds,
        "last_progress_at": last_progress_at or "",
        "observed_total_bytes": observed_total_bytes,
        "observed_source": observed_source,
        "attribution_confidence": attribution_confidence,
    }

    if stalled:
        metrics["warning"] = _append_warning(
            metrics.get("warning", ""),
            f"Install appears stalled: no byte growth for {stall_seconds}s while iSCSI session is active.",
        )

    if active_session and not has_winpe_logs and session_started_dt is not None:
        session_age_seconds = max(int((now - session_started_dt).total_seconds()), 0)
        if session_age_seconds >= winpe_missing_log_threshold_seconds:
            metrics["warning"] = _append_warning(
                metrics.get("warning", ""),
                f"WinPE logs still missing after {session_age_seconds}s; check WinPE uploader path/startnet execution.",
            )

    if active_session and not stall_measurement_allowed:
        metrics["warning"] = _append_warning(
            metrics.get("warning", ""),
            "Per-device install progress counters are not unique for this session; progress/stall log events are temporarily suppressed to avoid MAC mixup.",
        )

    return metrics


@router.post("/devices/{mac}/transfer/reset")
async def reset_device_transfer_state(mac: str, db: Database = Depends(get_db)):
    """Manually reset stale transfer/session telemetry for a specific device."""
    device = db.get_device(mac)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    reset_state = db.reset_device_transfer(mac)
    db.update_device_transfer_fields(mac, {
        "stall_state": "idle",
        "stall_last_total_bytes": 0,
        "stall_last_progress_at": "",
        "stall_last_progress_log_at": "",
        "winpe_missing_logged_at": "",
    })
    db.add_boot_log(mac, "transfer_state_reset", "Manual transfer/session state reset from WebUI/API")

    return {
        "success": True,
        "mac": mac,
        "session_id": (reset_state or {}).get("session_id", ""),
    }


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
