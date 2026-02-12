"""Pydantic request/response schemas."""
from typing import Any, Literal

from pydantic import BaseModel, Field

ActionType = Literal["tool_call", "aws_api", "codegen", "other"]
Decision = Literal["ALLOW", "DENY", "REQUIRE_APPROVAL"]


class EvaluateRequest(BaseModel):
    action_type: ActionType
    actor: str | None = None
    agent: str | None = None
    trace_id: str | None = None

    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None

    aws_service: str | None = None
    aws_operation: str | None = None
    params: dict[str, Any] | None = None

    context: dict[str, Any] = Field(default_factory=dict)
    wait_for_approval: bool = False


class EvaluateResponse(BaseModel):
    decision: Decision
    reason: str
    risk_score: int
    risk_signals: list[str]
    policy_hits: list[dict]
    evaluation_id: str
    approval_id: str | None = None


class ApprovalResponse(BaseModel):
    id: str
    status: str
    evaluation_id: str
    approver: str | None = None
    comment: str | None = None
    created_at: str
    resolved_at: str | None = None


class ApprovalActionRequest(BaseModel):
    approver: str
    comment: str | None = None


class PolicyUpsert(BaseModel):
    name: str
    enabled: bool = True
    dsl: dict


class TenantCreate(BaseModel):
    name: str


class ApiKeyCreate(BaseModel):
    name: str
    scopes: list[str] = Field(default_factory=list)


class ApiKeyCreated(BaseModel):
    api_key: str
    api_key_id: str
    tenant_id: str
    scopes: list[str]
