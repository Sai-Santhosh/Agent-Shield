"""Tenant and API key management."""
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select

from app.api.deps import AuthContext, require_auth, require_scope
from app.api.schemas import ApiKeyCreate, ApiKeyCreated, TenantCreate
from app.core.config import settings
from app.core.security import generate_api_key, hash_api_key
from app.db.models import ApiKey, Tenant
from app.db.session import async_session

router = APIRouter()


@router.post("/tenants", summary="Create tenant (admin + bootstrap secret)")
async def create_tenant(
    body: TenantCreate,
    ctx: AuthContext = Depends(require_auth),
    x_bootstrap_secret: str = Header(default="", alias="X-Bootstrap-Secret"),
):
    """Create tenant. Requires admin scope and valid bootstrap secret."""
    require_scope(ctx, "admin")
    if x_bootstrap_secret != settings.ADMIN_BOOTSTRAP_SECRET:
        raise HTTPException(status_code=403, detail="Invalid bootstrap secret")

    async with async_session() as session:
        result = await session.execute(select(Tenant).where(Tenant.name == body.name))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Tenant name already exists")
        t = Tenant(name=body.name)
        session.add(t)
        await session.commit()
        await session.refresh(t)
        return {"tenant_id": str(t.id), "name": t.name}


@router.post("/tenants/{tenant_id}/api-keys", response_model=ApiKeyCreated)
async def create_api_key(
    tenant_id: str,
    body: ApiKeyCreate,
    ctx: AuthContext = Depends(require_auth),
):
    """Create API key for tenant. Requires admin scope. Same-tenant only."""
    require_scope(ctx, "admin")
    if tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=403, detail="Cross-tenant forbidden")

    raw = generate_api_key(settings.API_KEY_PREFIX)
    ak = ApiKey(
        tenant_id=UUID(tenant_id),
        name=body.name,
        key_hash=hash_api_key(raw),
        scopes=body.scopes,
        is_active=True,
    )
    async with async_session() as session:
        session.add(ak)
        await session.commit()
        await session.refresh(ak)

    return ApiKeyCreated(
        api_key=raw,
        api_key_id=str(ak.id),
        tenant_id=tenant_id,
        scopes=body.scopes,
    )
