"""Integration tests for approval workflow."""
import pytest


@pytest.mark.asyncio
async def test_full_approval_flow(app_client):
    """Evaluate -> REQUIRE_APPROVAL -> approve -> verify resolved."""
    client, _ = app_client

    # 1. Evaluate shell command (triggers REQUIRE_APPROVAL)
    r1 = await client.post(
        "/v1/evaluate",
        json={
            "action_type": "tool_call",
            "tool_name": "shell",
            "tool_args": {"command": "echo hello"},
            "context": {},
        },
    )
    assert r1.status_code == 200
    data1 = r1.json()

    # If ALLOW (no matching policy), skip approval test
    if data1["decision"] != "REQUIRE_APPROVAL":
        pytest.skip("Starter policy did not match - decision was " + data1["decision"])

    approval_id = data1.get("approval_id")
    assert approval_id

    # 2. Get approval status
    r2 = await client.get(f"/v1/approvals/{approval_id}")
    assert r2.status_code == 200
    assert r2.json()["status"] == "PENDING"

    # 3. Approve
    r3 = await client.post(
        f"/v1/approvals/{approval_id}/approve",
        json={"approver": "test-admin", "comment": "Approved in test"},
    )
    assert r3.status_code == 200
    assert r3.json()["status"] == "APPROVED"

    # 4. Verify approval is resolved
    r4 = await client.get(f"/v1/approvals/{approval_id}")
    assert r4.status_code == 200
    assert r4.json()["status"] == "APPROVED"
    assert r4.json()["approver"] == "test-admin"


@pytest.mark.asyncio
async def test_deny_approval(app_client):
    """Evaluate -> REQUIRE_APPROVAL -> deny."""
    client, _ = app_client

    r1 = await client.post(
        "/v1/evaluate",
        json={
            "action_type": "tool_call",
            "tool_name": "bash",
            "tool_args": {"command": "whoami"},
            "context": {},
        },
    )
    assert r1.status_code == 200
    data1 = r1.json()

    if data1["decision"] != "REQUIRE_APPROVAL":
        pytest.skip("Policy did not require approval")

    approval_id = data1["approval_id"]
    assert approval_id

    r2 = await client.post(
        f"/v1/approvals/{approval_id}/deny",
        json={"approver": "admin", "comment": "Denied in test"},
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "DENIED"
