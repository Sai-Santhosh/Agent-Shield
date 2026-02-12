"""Integration tests for audit log and policies."""
import pytest


@pytest.mark.asyncio
async def test_audit_list_after_evaluate(app_client):
    """Audit log contains evaluations after evaluate calls."""
    client, _ = app_client

    # Create an evaluation
    await client.post(
        "/v1/evaluate",
        json={
            "action_type": "tool_call",
            "tool_name": "search",
            "tool_args": {"query": "audit-test"},
            "context": {},
        },
    )

    r = await client.get("/v1/audit?limit=10")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    # Should have at least one entry from our evaluate + any from other tests
    assert len(items) >= 1
    assert "action_type" in items[0]
    assert "decision" in items[0]
    assert "created_at" in items[0]


@pytest.mark.asyncio
async def test_list_policies(app_client):
    """Admin can list policies."""
    client, _ = app_client

    r = await client.get("/v1/policies")
    assert r.status_code == 200
    policies = r.json()
    assert isinstance(policies, list)
    # Starter policy from bootstrap
    names = [p["name"] for p in policies]
    assert "starter" in names


@pytest.mark.asyncio
async def test_upsert_policy(app_client):
    """Admin can create/update policies."""
    client, _ = app_client

    r = await client.put(
        "/v1/policies",
        json={
            "name": "test-custom",
            "enabled": True,
            "dsl": {
                "rules": [
                    {
                        "name": "deny-all",
                        "effect": "DENY",
                        "reason": "Test rule",
                        "match": {"equals": {"action_type": "other"}},
                    }
                ]
            },
        },
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["name"] == "test-custom"
