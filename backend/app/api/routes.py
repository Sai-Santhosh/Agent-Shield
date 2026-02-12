"""API route aggregation."""
from fastapi import APIRouter

from app.api.endpoints import approvals, audit, evaluate, policies, tenants

router = APIRouter(prefix="/v1")
router.include_router(evaluate.router, tags=["evaluate"])
router.include_router(approvals.router, tags=["approvals"])
router.include_router(policies.router, tags=["policies"])
router.include_router(audit.router, tags=["audit"])
router.include_router(tenants.router, tags=["tenants"])
