import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import v1, boot


logger = logging.getLogger(__name__)

BRANDING = "Netboot Orchestrator is designed by Kenneth Kronborg AI Team"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    # Start file index/storage background sync for fast API responses
    try:
        from .services.file_service import FileService
        _os_installers = (os.getenv("OS_INSTALLERS_PATH") or os.getenv("OS_INSTALLERS_PATH ") or "/data/os-installers").strip()
        _images_path = (os.getenv("IMAGES_PATH") or os.getenv("IMAGES_PATH ") or "/iscsi-images").strip()
        _sync_interval = int((os.getenv("FILE_SYNC_INTERVAL") or "15").strip())
        FileService.start_background_sync(
            os_installers_path=_os_installers,
            images_path=_images_path,
            interval_seconds=_sync_interval,
        )
        logger.info("FileService background sync started")
    except Exception as e:
        logger.warning(f"FileService background sync skipped: {e}")

    # Restore iSCSI targets on start
    try:
        from .services.image_service import IscsiService
        _images_path = (os.getenv("IMAGES_PATH") or os.getenv("IMAGES_PATH ") or "/iscsi-images").strip()
        iscsi = IscsiService(images_path=_images_path)
        iscsi.restore_targets()
        logger.info("iSCSI targets restored")
    except Exception as e:
        logger.warning(f"iSCSI target restore skipped: {e}")
    try:
        yield
    finally:
        try:
            from .services.file_service import FileService
            FileService.stop_background_sync()
        except Exception:
            pass


app = FastAPI(
    title="Netboot Orchestrator",
    description=f"Network boot management for Raspberry Pi, x86 & x64. {BRANDING}",
    version="0.2.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(v1.router)
app.include_router(boot.router)


@app.get("/")
async def root():
    return {
        "name": "Netboot Orchestrator API",
        "version": "0.2.0",
        "branding": BRANDING,
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
