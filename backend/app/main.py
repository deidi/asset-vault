import os
import sys
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
import app.models  # Ensure all SQLAlchemy models are registered
from app.routes.asset_routes import router as asset_router
from app.routes.inventory_routes import router as inventory_router
from app.routes.folder_routes import router as folder_router
from app.routes.explorer_routes import router as explorer_router
from app.routes.ws_routes import router as ws_router
from app.routes.thumbnail_routes import router as thumbnail_router
from app.services.watcher_service import watcher_service
from app.services.connection_manager import manager
from app.db.session import engine, Base, init_db

# Setup logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("assetvault")

# Initialize and auto-migrate SQLite tables on startup
init_db(engine)
logger.info("Database schema initialized and verified.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: configure event loop for manager and start background file watchers
    try:
        loop = asyncio.get_running_loop()
        manager.set_loop(loop)
        watcher_service.start_all()
    except Exception as e:
        logger.error(f"Error starting file system watchers on startup: {e}")
    yield
    # Shutdown: stop watchdog observers cleanly
    try:
        watcher_service.stop_all()
    except Exception as e:
        logger.warning(f"Error stopping watchers on shutdown: {e}")

app = FastAPI(
    title="AssetVault API",
    description="AssetVault FastAPI Backend",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers — all API routes live under /api to avoid colliding with SPA routes
app.include_router(asset_router, prefix="/api")
app.include_router(inventory_router, prefix="/api")
app.include_router(folder_router, prefix="/api")
app.include_router(explorer_router, prefix="/api")
app.include_router(ws_router, prefix="/api")
app.include_router(thumbnail_router, prefix="/api")

# Resolve absolute path to the public directory
current_dir = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, 'frozen', False):
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    public_dir = os.path.abspath(os.path.join(base_dir, "public"))
else:
    public_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "public"))

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/version")
def get_version():
    return {"version": "2.0"}

# Mount static assets (JS, CSS, images) from public/assets
if os.path.exists(public_dir):
    assets_dir = os.path.join(public_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

@app.get("/")
def serve_root_index():
    index_path = os.path.join(public_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Frontend not built. Run: cd frontend && npm run build"}

@app.get("/assetvault")
@app.get("/assetvault/")
def redirect_to_root():
    return RedirectResponse(url="/")

# SPA catch-all: serve index.html for any path not matched by the API routers above.
@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    if full_path.startswith("api/") or full_path == "docs" or full_path == "redoc" or full_path == "openapi.json":
        raise HTTPException(status_code=404, detail="Not found")
    index_path = os.path.join(public_dir, "index.html")
    candidate = os.path.join(public_dir, full_path)
    if os.path.isfile(candidate):
        return FileResponse(candidate)
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Frontend not built. Run: cd frontend && npm run build"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, log_level="info")


