"""FastAPI dependencies."""
from fastapi import Header, HTTPException, status

from app.core.security import AuthContext, authenticate_api_key


async def require_auth(x_api_key: str = Header(..., alias="X-Api-Key")) -> AuthContext:
    """Require valid API key. Raises 401 if invalid."""
    ctx = await authenticate_api_key(x_api_key)
    if not ctx:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return ctx


def require_scope(ctx: AuthContext, scope: str) -> None:
    """Require scope. Raises 403 if missing."""
    if scope not in (ctx.scopes or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required scope: {scope}",
        )
