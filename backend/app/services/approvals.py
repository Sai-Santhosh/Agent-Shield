"""Approval workflow - wait for human decision."""
import asyncio
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from app.core.config import settings
from app.db.models import ApprovalRequest
from app.db.session import async_session


async def wait_for_approval(tenant_id: str, approval_id: str) -> ApprovalRequest | None:
    """
    Poll until approval is resolved or timeout.
    Returns resolved ApprovalRequest or None if timeout.
    """
    try:
        approval_uuid = UUID(approval_id)
        tenant_uuid = UUID(tenant_id)
    except (ValueError, TypeError):
        return None

    deadline = datetime.utcnow() + timedelta(seconds=settings.APPROVAL_WAIT_TIMEOUT)

    while datetime.utcnow() < deadline:
        async with async_session() as session:
            result = await session.execute(
                select(ApprovalRequest).where(
                    ApprovalRequest.tenant_id == tenant_uuid,
                    ApprovalRequest.id == approval_uuid,
                )
            )
            appr = result.scalar_one_or_none()
            if appr and appr.status in {"APPROVED", "DENIED"}:
                return appr

        await asyncio.sleep(0.5)

    return None
