"""API key generation, hashing, and authentication."""
import hashlib
import hmac
import secrets
from dataclasses import dataclass

from sqlalchemy import select

from app.core.config import settings
from app.db.models import ApiKey
from app.db.session import async_session


def generate_api_key(prefix: str | None = None) -> str:
    """Generate a URL-safe random API key with optional prefix."""
    prefix = prefix or settings.API_KEY_PREFIX
    token = secrets.token_urlsafe(32)
    return f"{prefix}{token}"


def hash_api_key(raw_key: str) -> str:
    """SHA-256 hash of API key for secure storage."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


@dataclass
class AuthContext:
    tenant_id: str
    api_key_id: str
    scopes: list[str]


async def authenticate_api_key(raw_key: str) -> AuthContext | None:
    """Validate API key and return auth context if valid."""
    if not raw_key or not raw_key.strip():
        return None

    key_hash = hash_api_key(raw_key)

    async with async_session() as session:
        result = await session.execute(
            select(ApiKey).where(
                ApiKey.key_hash == key_hash,
                ApiKey.is_active == True,
            )
        )
        api_key = result.scalar_one_or_none()
        if not api_key:
            return None

        return AuthContext(
            tenant_id=str(api_key.tenant_id),
            api_key_id=str(api_key.id),
            scopes=api_key.scopes or [],
        )
