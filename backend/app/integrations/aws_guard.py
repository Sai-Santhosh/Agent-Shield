"""
AgentShield AWS/boto3 integration.
Wrap boto3 clients (IAM, STS, etc.) so every API call is gated.
"""
from __future__ import annotations

from typing import Any

import httpx


class GuardedBoto3Client:
    """
    Wraps a boto3 client (e.g. iam, sts, organizations) and enforces
    AgentShield evaluate before each call.
    """

    def __init__(
        self,
        boto_client: Any,
        guard_base_url: str,
        api_key: str,
        *,
        actor: str | None = None,
        agent: str | None = None,
    ):
        self._client = boto_client
        self._base_url = guard_base_url.rstrip("/")
        self._api_key = api_key
        self._actor = actor
        self._agent = agent

    def __getattr__(self, op_name: str):
        real = getattr(self._client, op_name)

        def wrapped(**params: Any) -> Any:
            svc = self._client.meta.service_model.service_name
            operation_name = op_name[0].upper() + op_name[1:] if op_name else ""

            payload: dict[str, Any] = {
                "action_type": "aws_api",
                "actor": self._actor,
                "agent": self._agent,
                "aws_service": svc,
                "aws_operation": operation_name,
                "params": params,
                "context": {},
                "wait_for_approval": False,
            }

            headers = {"X-Api-Key": self._api_key, "Content-Type": "application/json"}
            with httpx.Client(timeout=10.0) as client:
                r = client.post(
                    f"{self._base_url}/v1/evaluate",
                    json=payload,
                    headers=headers,
                )
                r.raise_for_status()
                dec = r.json()

            if dec["decision"] == "DENY":
                raise RuntimeError(
                    f"Blocked AWS call {svc}.{op_name}: {dec['reason']}"
                )
            if dec["decision"] == "REQUIRE_APPROVAL":
                raise RuntimeError(
                    f"Approval required for {svc}.{op_name}: approval_id={dec.get('approval_id')}"
                )

            return real(**params)

        return wrapped
