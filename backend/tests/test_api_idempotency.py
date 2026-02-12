"""Integration tests for idempotency - same key returns same result."""
import pytest


@pytest.mark.asyncio
async def test_idempotency_same_result(app_client):
    """Two evaluate requests with same Idempotency-Key return identical result."""
    client, _ = app_client

    payload = {
        "action_type": "tool_call",
        "tool_name": "search",
        "tool_args": {"query": "test"},
        "context": {},
    }
    idem_key = "test-idem-key-001"

    r1 = await client.post(
        "/v1/evaluate",
        json=payload,
        headers={"Idempotency-Key": idem_key},
    )
    assert r1.status_code == 200
    data1 = r1.json()

    r2 = await client.post(
        "/v1/evaluate",
        json=payload,
        headers={"Idempotency-Key": idem_key},
    )
    assert r2.status_code == 200
    data2 = r2.json()

    assert data1["evaluation_id"] == data2["evaluation_id"]
    assert data1["decision"] == data2["decision"]
    assert data1["risk_score"] == data2["risk_score"]


@pytest.mark.asyncio
async def test_different_idempotency_keys_different_results(app_client):
    """Different keys produce separate evaluations."""
    client, _ = app_client

    payload = {
        "action_type": "tool_call",
        "tool_name": "search",
        "tool_args": {"query": "x"},
        "context": {},
    }

    r1 = await client.post(
        "/v1/evaluate",
        json=payload,
        headers={"Idempotency-Key": "key-a"},
    )
    r2 = await client.post(
        "/v1/evaluate",
        json=payload,
        headers={"Idempotency-Key": "key-b"},
    )

    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["evaluation_id"] != r2.json()["evaluation_id"]
