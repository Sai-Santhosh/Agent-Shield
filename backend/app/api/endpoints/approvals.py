"""Approval workflow endpoints."""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.api.deps import AuthContext, require_auth, require_scope
from app.api.schemas import ApprovalActionRequest, ApprovalResponse
from app.db.models import ApprovalRequest
from app.db.session import async_session

router = APIRouter()


async def _get_approval(session, tenant_id: str, approval_id: str) -> ApprovalRequest | None:
    try:
        aid = UUID(approval_id)
        tid = UUID(tenant_id)
    except (ValueError, TypeError):
        return None
    result = await session.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.tenant_id == tid,
            ApprovalRequest.id == aid,
        )
    )
    return result.scalar_one_or_none()


@router.get("/approvals/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: str,
    ctx: AuthContext = Depends(require_auth),
):
    """Get approval request status."""
    async with async_session() as session:
        appr = await _get_approval(session, ctx.tenant_id, approval_id)
        if not appr:
            raise HTTPException(status_code=404, detail="Approval not found")
        return ApprovalResponse(
            id=str(appr.id),
            status=appr.status,
            evaluation_id=str(appr.evaluation_id),
            approver=appr.approver,
            comment=appr.comment,
            created_at=appr.created_at.isoformat(),
            resolved_at=appr.resolved_at.isoformat() if appr.resolved_at else None,
        )


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalResponse)
async def approve(
    approval_id: str,
    body: ApprovalActionRequest,
    ctx: AuthContext = Depends(require_auth),
):
    """Approve a pending request. Requires admin scope."""
    require_scope(ctx, "admin")

    async with async_session() as session:
        appr = await _get_approval(session, ctx.tenant_id, approval_id)
        if not appr:
            raise HTTPException(status_code=404, detail="Approval not found")
        if appr.status != "PENDING":
            raise HTTPException(status_code=409, detail=f"Approval already {appr.status}")

        appr.status = "APPROVED"
        appr.approver = body.approver
        appr.comment = body.comment
        appr.resolved_at = datetime.utcnow()
        await session.commit()
        await session.refresh(appr)

        return ApprovalResponse(
            id=str(appr.id),
            status=appr.status,
            evaluation_id=str(appr.evaluation_id),
            approver=appr.approver,
            comment=appr.comment,
            created_at=appr.created_at.isoformat(),
            resolved_at=appr.resolved_at.isoformat() if appr.resolved_at else None,
        )


@router.post("/approvals/{approval_id}/deny", response_model=ApprovalResponse)
async def deny(
    approval_id: str,
    body: ApprovalActionRequest,
    ctx: AuthContext = Depends(require_auth),
):
    """Deny a pending request. Requires admin scope."""
    require_scope(ctx, "admin")

    async with async_session() as session:
        appr = await _get_approval(session, ctx.tenant_id, approval_id)
        if not appr:
            raise HTTPException(status_code=404, detail="Approval not found")
        if appr.status != "PENDING":
            raise HTTPException(status_code=409, detail=f"Approval already {appr.status}")

        appr.status = "DENIED"
        appr.approver = body.approver
        appr.comment = body.comment
        appr.resolved_at = datetime.utcnow()
        await session.commit()
        await session.refresh(appr)

        return ApprovalResponse(
            id=str(appr.id),
            status=appr.status,
            evaluation_id=str(appr.evaluation_id),
            approver=appr.approver,
            comment=appr.comment,
            created_at=appr.created_at.isoformat(),
            resolved_at=appr.resolved_at.isoformat() if appr.resolved_at else None,
        )
