"""Policy-as-code DSL evaluator."""
from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from typing import Any


@dataclass
class PolicyDecision:
    decision: str
    reason: str
    hits: list[dict]


def _match_all(match: dict, ctx: dict) -> bool:
    """
    Match context against rule.
    Supports: equals, in, glob.
    """
    for k, v in (match.get("equals") or {}).items():
        if ctx.get(k) != v:
            return False

    for k, arr in (match.get("in") or {}).items():
        val = ctx.get(k)
        if val not in (arr or []):
            return False

    for k, pat in (match.get("glob") or {}).items():
        if not fnmatch(str(ctx.get(k) or ""), str(pat)):
            return False

    return True


def evaluate_policies(policies: list[dict[str, Any]], ctx: dict[str, Any]) -> PolicyDecision:
    """
    Evaluate policies in order. First matching rule wins by effect precedence:
    DENY > REQUIRE_APPROVAL > ALLOW
    """
    hits: list[dict] = []
    default_decision = ctx.get("default_decision") or "ALLOW"
    decision = default_decision
    reason = "default"

    precedence = {"DENY": 3, "REQUIRE_APPROVAL": 2, "ALLOW": 1}

    for p in policies:
        if not p.get("enabled", True):
            continue

        for rule in p.get("rules", []):
            if not _match_all(rule.get("match", {}), ctx):
                continue

            effect = rule.get("effect", "ALLOW")
            hits.append({
                "policy": p.get("name", "unknown"),
                "rule": rule.get("name", "unnamed"),
                "effect": effect,
            })

            if precedence.get(effect, 0) >= precedence.get(decision, 0):
                decision = effect
                reason = rule.get("reason") or f"matched:{p.get('name')}:{rule.get('name')}"

    return PolicyDecision(decision=decision, reason=reason, hits=hits)
