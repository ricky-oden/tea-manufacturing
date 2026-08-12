from fastapi import APIRouter

from app.api.routes.csv_imports import router as csv_imports_router
from app.api.routes.health import router as health_router
from app.api.routes.manufacturing_orders import router as manufacturing_orders_router
from app.api.routes.masters import router as masters_router
from app.api.routes.phase3 import router as phase3_router
from app.api.routes.phase4 import router as phase4_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(csv_imports_router)
api_router.include_router(masters_router)
api_router.include_router(phase3_router)
api_router.include_router(phase4_router)
api_router.include_router(manufacturing_orders_router)
