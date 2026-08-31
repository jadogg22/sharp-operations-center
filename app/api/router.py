from fastapi import APIRouter

from app.api.customer_invoice import router as customer_invoice_router
from app.api.fleet_cost_revenue import router as fleet_cost_revenue_router
from app.api.health import router as health_router
from app.api.lane_profitability import router as lane_profitability_router
from app.api.operations_overview import router as operations_overview_router

router = APIRouter(prefix="/api")
router.include_router(health_router)
router.include_router(operations_overview_router)
router.include_router(lane_profitability_router)
router.include_router(customer_invoice_router)
router.include_router(fleet_cost_revenue_router)
