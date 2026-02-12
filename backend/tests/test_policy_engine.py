"""Policy engine tests."""
import pytest

from app.services.policy_engine import evaluate_policies


def test_deny_takes_precedence():
    policies = [
        {
            "name": "p1",
            "enabled": True,
            "rules": [
                {"name": "allow", "effect": "ALLOW", "match": {"equals": {"action_type": "aws_api"}}},
                {"name": "deny", "effect": "DENY", "match": {"equals": {"aws_service": "iam"}}},
            ],
        }
    ]
    ctx = {"action_type": "aws_api", "aws_service": "iam"}
    d = evaluate_policies(policies, ctx)
    assert d.decision == "DENY"


def test_require_approval_overrides_allow():
    policies = [
        {
            "name": "p1",
            "enabled": True,
            "rules": [
                {"name": "allow", "effect": "ALLOW", "match": {"equals": {"action_type": "tool_call"}}},
                {
                    "name": "approve",
                    "effect": "REQUIRE_APPROVAL",
                    "match": {"in": {"tool_name": ["shell"]}},
                },
            ],
        }
    ]
    ctx = {"action_type": "tool_call", "tool_name": "shell"}
    d = evaluate_policies(policies, ctx)
    assert d.decision == "REQUIRE_APPROVAL"


def test_disabled_policy_ignored():
    policies = [
        {
            "name": "p1",
            "enabled": False,
            "rules": [{"name": "deny", "effect": "DENY", "match": {"equals": {"action_type": "aws_api"}}}],
        }
    ]
    ctx = {"action_type": "aws_api"}
    d = evaluate_policies(policies, ctx)
    assert d.decision == "ALLOW"
