"""
AgentShield LangChain integration.
Wrap LangChain tools so every invocation is gated by the security API.
"""
from __future__ import annotations

from typing import Any, Callable

import httpx


class AgentShieldClient:
    """HTTP client for AgentShield evaluate API."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def evaluate(
        self,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Call /v1/evaluate and return decision."""
        headers = {"X-Api-Key": self.api_key, "Content-Type": "application/json"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(
                f"{self.base_url}/v1/evaluate",
                json=payload,
                headers=headers,
            )
            r.raise_for_status()
            return r.json()


def guard_tool(
    guard: AgentShieldClient,
    tool_name: str,
    tool_fn: Callable[..., Any],
    *,
    actor: str | None = None,
    agent: str | None = None,
    trace_id: str | None = None,
) -> Callable[..., Any]:
    """
    Wrap a LangChain tool so each call is gated by AgentShield.

    Example:
        from app.integrations.langchain_guard import AgentShieldClient, guard_tool

        guard = AgentShieldClient("http://localhost:8080", "ash_live_...")
        safe_shell = guard_tool(guard, "shell", shell_tool, actor="user-1", agent="my-agent")
    """

    def wrapped(**kwargs: Any) -> Any:
        decision = guard.evaluate(
            {
                "action_type": "tool_call",
                "actor": actor,
                "agent": agent,
                "trace_id": trace_id,
                "tool_name": tool_name,
                "tool_args": kwargs,
                "context": {},
                "wait_for_approval": False,
            },
            idempotency_key=kwargs.get("idempotency_key"),
        )
        if decision["decision"] == "DENY":
            raise RuntimeError(f"Blocked by AgentShield: {decision['reason']}")
        if decision["decision"] == "REQUIRE_APPROVAL":
            raise RuntimeError(
                f"Approval required: approval_id={decision.get('approval_id')}"
            )
        return tool_fn(**kwargs)

    return wrapped
