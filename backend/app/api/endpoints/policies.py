"""Policy CRUD and management."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.api.deps import AuthContext, require_auth, require_scope
from app.api.schemas import PolicyUpsert
from app.db.models import Policy
from app.db.session import async_session

router = APIRouter()


@router.get("/policies")
async def list_policies(ctx: AuthContext = Depends(require_auth)):
    """List policies for tenant. Requires admin scope."""
    require_scope(ctx, "admin")

    async with async_session() as session:
        result = await session.execute(
            select(Policy).where(Policy.tenant_id == UUID(ctx.tenant_id))
        )
        policies = result.scalars().all()
        return [
            {
                "id": str(p.id),
                "name": p.name,
                "enabled": p.enabled,
                "version": p.version,
                "dsl": p.dsl,
            }
            for p in policies
        ]


@router.put("/policies", summary="Upsert policy by name")
async def upsert_policy(
    body: PolicyUpsert,
    ctx: AuthContext = Depends(require_auth),
):
    """Create or update policy. Requires admin scope."""
    require_scope(ctx, "admin")

    async with async_session() as session:
        result = await session.execute(
            select(Policy).where(
                Policy.tenant_id == UUID(ctx.tenant_id),
                Policy.name == body.name,
            )
        )
        p = result.scalar_one_or_none()
        if not p:
            p = Policy(
                tenant_id=UUID(ctx.tenant_id),
                name=body.name,
                enabled=body.enabled,
                dsl=body.dsl,
                version=1,
            )
            session.add(p)
        else:
            p.enabled = body.enabled
            p.dsl = body.dsl
            p.version += 1
        await session.commit()
        return {"ok": True, "name": body.name, "id": str(p.id)}


@router.post("/policies/{policy_id}/toggle")
async def toggle_policy(
    policy_id: str,
    enabled: bool,
    ctx: AuthContext = Depends(require_auth),
):
    """Enable or disable policy. Requires admin scope."""
    require_scope(ctx, "admin")

    try:
        pid = UUID(policy_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid policy ID")

    async with async_session() as session:
        result = await session.execute(
            select(Policy).where(
                Policy.tenant_id == UUID(ctx.tenant_id),
                Policy.id == pid,
            )
        )
        p = result.scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="Policy not found")
        p.enabled = enabled
        await session.commit()
        return {"ok": True, "enabled": enabled, "policy_id": policy_id}
