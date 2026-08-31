from app.routes.asset_routes import router as asset_router
from app.routes.inventory_routes import router as inventory_router
from app.routes.folder_routes import router as folder_router
from app.routes.explorer_routes import router as explorer_router
from app.routes.ws_routes import router as ws_router
from app.routes.thumbnail_routes import router as thumbnail_router

__all__ = [
    "asset_router",
    "inventory_router",
    "folder_router",
    "explorer_router",
    "ws_router",
    "thumbnail_router"
]
