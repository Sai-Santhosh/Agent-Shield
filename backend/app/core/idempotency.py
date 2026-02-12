"""Idempotency lookup for safe agent retries."""
from uuid import UUID

from sqlalchemy import select

from app.db.models import Evaluation
from app.db.session import async_session


async def get_by_idempotency(tenant_id: str, idempotency_key: str) -> Evaluation | None:
    """Return existing evaluation for tenant + idempotency key, if any."""
    if not idempotency_key or not idempotency_key.strip():
        return None
    try:
        tid = UUID(tenant_id)
    except (ValueError, TypeError):
        return None

    async with async_session() as session:
        result = await session.execute(
            select(Evaluation).where(
                Evaluation.tenant_id == tid,
                Evaluation.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()
