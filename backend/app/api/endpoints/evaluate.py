"""Evaluate agent actions - gate tool calls and AWS API."""
import hashlib
import json
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select

from app.api.deps import AuthContext, require_auth
from app.api.schemas import EvaluateRequest, EvaluateResponse
from app.core.idempotency import get_by_idempotency
from app.db.models import ApprovalRequest, Evaluation, Policy
from app.db.session import async_session
from app.services.approvals import wait_for_approval
from app.services.policy_engine import evaluate_policies
from app.services.risk import score_risk

router = APIRouter()


def _stable_hash(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(
    body: EvaluateRequest,
    ctx: AuthContext = Depends(require_auth),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    """Evaluate an agent action. Returns ALLOW, DENY, or REQUIRE_APPROVAL."""
    tenant_id = ctx.tenant_id

    if idempotency_key and idempotency_key.strip():
        existing = await get_by_idempotency(tenant_id, idempotency_key)
        if existing:
            approval_id = None
            async with async_session() as session:
                result = await session.execute(
                    select(ApprovalRequest).where(
                        ApprovalRequest.evaluation_id == existing.id
                    )
                )
                appr = result.scalar_one_or_none()
                if appr:
                    approval_id = str(appr.id)

            payload = existing.request_payload or {}
            return EvaluateResponse(
                decision=existing.decision,
                reason=existing.reason,
                risk_score=existing.risk_score,
                risk_signals=payload.get("risk_signals", []),
                policy_hits=existing.policy_hits or [],
                evaluation_id=str(existing.id),
                approval_id=approval_id,
            )

    req_payload = body.model_dump()
    req_hash = _stable_hash(req_payload)
    risk_score, risk_signals = score_risk(body.action_type, req_payload)

    match_ctx = {
        "action_type": body.action_type,
        "actor": body.actor,
        "agent": body.agent,
        "tool_name": body.tool_name,
        "aws_service": body.aws_service,
        "aws_operation": body.aws_operation,
        "risk_score": risk_score,
        "default_decision": "REQUIRE_APPROVAL" if risk_score >= 60 else "ALLOW",
    }

    async with async_session() as session:
        result = await session.execute(
            select(Policy).where(
                Policy.tenant_id == UUID(tenant_id),
                Policy.enabled == True,
            )
        )
        policies = result.scalars().all()
        policy_dsls = [
            {"name": p.name, "enabled": p.enabled, "rules": (p.dsl or {}).get("rules", [])}
            for p in policies
        ]

        pd = evaluate_policies(policy_dsls, match_ctx)

        ev = Evaluation(
            tenant_id=UUID(tenant_id),
            idempotency_key=idempotency_key,
            trace_id=body.trace_id,
            action_type=body.action_type,
            actor=body.actor,
            agent=body.agent,
            tool_name=body.tool_name,
            aws_service=body.aws_service,
            aws_operation=body.aws_operation,
            request_payload={**req_payload, "risk_signals": risk_signals},
            request_hash=req_hash,
            decision=pd.decision,
            reason=pd.reason,
            risk_score=risk_score,
            policy_hits=pd.hits,
        )
        session.add(ev)
        await session.commit()
        await session.refresh(ev)

        approval_id = None
        if pd.decision == "REQUIRE_APPROVAL":
            appr = ApprovalRequest(
                tenant_id=UUID(tenant_id),
                evaluation_id=ev.id,
                status="PENDING",
            )
            session.add(appr)
            await session.commit()
            await session.refresh(appr)
            approval_id = str(appr.id)

            if body.wait_for_approval and approval_id:
                resolved = await wait_for_approval(tenant_id, approval_id)
                if resolved:
                    final_decision = "ALLOW" if resolved.status == "APPROVED" else "DENY"
                    return EvaluateResponse(
                        decision=final_decision,
                        reason=f"approval:{resolved.status}",
                        risk_score=risk_score,
                        risk_signals=risk_signals,
                        policy_hits=pd.hits,
                        evaluation_id=str(ev.id),
                        approval_id=approval_id,
                    )

        return EvaluateResponse(
            decision=pd.decision,
            reason=pd.reason,
            risk_score=risk_score,
            risk_signals=risk_signals,
            policy_hits=pd.hits,
            evaluation_id=str(ev.id),
            approval_id=approval_id,
        )
