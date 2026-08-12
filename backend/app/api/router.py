from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.manufacturing_orders import router as manufacturing_orders_router
from app.api.routes.masters import router as masters_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(masters_router)
api_router.include_router(manufacturing_orders_router)
