import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import v1, boot

app = FastAPI(
    title="RPi Netboot Orchestrator",
    description="Web-based orchestrator for SD-card-less netboot",
    version="0.1.0"
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
        "name": "RPi Netboot Orchestrator API",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
