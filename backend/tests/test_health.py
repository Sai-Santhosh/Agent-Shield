"""Health and basic endpoint tests."""
import pytest


@pytest.mark.asyncio
async def test_healthz(app_client):
    """Health check returns 200."""
    client, _ = app_client
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


@pytest.mark.asyncio
async def test_readyz(app_client):
    """Readiness check returns 200."""
    client, _ = app_client
    r = await client.get("/readyz")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
