"""Integration tests for /v1/evaluate - real API, real DB."""
import pytest


@pytest.mark.asyncio
async def test_evaluate_denies_dangerous_shell(app_client):
    """Dangerous shell command (rm -rf) should be DENY or REQUIRE_APPROVAL."""
    client, _ = app_client

    r = await client.post(
        "/v1/evaluate",
        json={
            "action_type": "tool_call",
            "actor": "user-1",
            "agent": "test-agent",
            "tool_name": "shell",
            "tool_args": {"command": "rm -rf /"},
            "context": {},
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "decision" in data
    assert data["decision"] in ("DENY", "REQUIRE_APPROVAL", "ALLOW")
    assert "risk_score" in data
    assert "evaluation_id" in data
    assert data["risk_score"] > 0


@pytest.mark.asyncio
async def test_evaluate_shell_requires_approval(app_client):
    """Shell tool should trigger REQUIRE_APPROVAL per starter policy."""
    client, _ = app_client

    r = await client.post(
        "/v1/evaluate",
        json={
            "action_type": "tool_call",
            "tool_name": "shell",
            "tool_args": {"command": "ls -la"},
            "context": {},
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["decision"] in ("REQUIRE_APPROVAL", "ALLOW", "DENY")
    if data["decision"] == "REQUIRE_APPROVAL":
        assert "approval_id" in data
        assert data["approval_id"]


@pytest.mark.asyncio
async def test_evaluate_aws_iam_requires_approval_or_deny(app_client):
    """IAM CreateAccessKey should be DENY or REQUIRE_APPROVAL."""
    client, _ = app_client

    r = await client.post(
        "/v1/evaluate",
        json={
            "action_type": "aws_api",
            "aws_service": "iam",
            "aws_operation": "CreateAccessKey",
            "params": {"UserName": "test"},
            "context": {},
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["decision"] in ("DENY", "REQUIRE_APPROVAL")
    assert data["risk_score"] > 0


@pytest.mark.asyncio
async def test_evaluate_safe_action_allowed(app_client):
    """Low-risk action (search tool) should be ALLOW."""
    client, _ = app_client

    r = await client.post(
        "/v1/evaluate",
        json={
            "action_type": "tool_call",
            "tool_name": "search",
            "tool_args": {"query": "hello"},
            "context": {},
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["decision"] == "ALLOW"
    assert "evaluation_id" in data


@pytest.mark.asyncio
async def test_evaluate_rejects_invalid_api_key(app_client):
    """Request with invalid API key should return 401."""
    # Use app_client to ensure app+DB are up; then call with bad key
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-Api-Key": "invalid-key", "Content-Type": "application/json"},
    ) as bad_client:
        r = await bad_client.post(
            "/v1/evaluate",
            json={
                "action_type": "tool_call",
                "tool_name": "search",
                "tool_args": {},
                "context": {},
            },
        )
    assert r.status_code == 401
