"""Audit log - immutable event trail of evaluations."""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select

from app.api.deps import AuthContext, require_auth, require_scope
from app.db.models import Evaluation
from app.db.session import async_session

router = APIRouter()


@router.get("/audit")
async def list_audit(
    limit: int = 50,
    ctx: AuthContext = Depends(require_auth),
):
    """List evaluation audit log. Requires admin scope."""
    require_scope(ctx, "admin")

    limit = min(max(limit, 1), 200)

    async with async_session() as session:
        result = await session.execute(
            select(Evaluation)
            .where(Evaluation.tenant_id == UUID(ctx.tenant_id))
            .order_by(desc(Evaluation.created_at))
            .limit(limit)
        )
        rows = result.scalars().all()
        return [
            {
                "id": str(r.id),
                "created_at": r.created_at.isoformat(),
                "action_type": r.action_type,
                "actor": r.actor,
                "agent": r.agent,
                "tool_name": r.tool_name,
                "aws_service": r.aws_service,
                "aws_operation": r.aws_operation,
                "decision": r.decision,
                "risk_score": r.risk_score,
                "reason": r.reason,
                "policy_hits": r.policy_hits,
                "trace_id": r.trace_id,
            }
            for r in rows
        ]
