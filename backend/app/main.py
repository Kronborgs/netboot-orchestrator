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
    # Restore iSCSI targets on start
    try:
        from .services.image_service import IscsiService
        iscsi = IscsiService(images_path=os.getenv("IMAGES_PATH", "/iscsi-images"))
        iscsi.restore_targets()
        logger.info("iSCSI targets restored")
    except Exception as e:
        logger.warning(f"iSCSI target restore skipped: {e}")
    yield


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
