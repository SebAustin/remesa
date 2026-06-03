"""
tests/test_x402_server.py — tests for the x402-priced FastAPI endpoints.

The endpoint coroutines are called directly to bypass the x402 payment gate
(the gate is integration-tested live against the facilitator). /health is hit
through the ASGI test client.
"""
import json

import pytest
from starlette.requests import Request

from services import x402_server


def _make_post_request(payload: dict) -> Request:
    body = json.dumps(payload).encode()

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/sanctions-screen",
        "headers": [(b"content-type", b"application/json")],
    }
    return Request(scope, receive)


@pytest.mark.asyncio
async def test_fx_quote_mock(monkeypatch):
    monkeypatch.setattr(x402_server, "USE_MOCK_APIS", True)
    out = await x402_server.fx_quote()
    assert out["rate_mxn_per_usd"] == 17.15
    assert out["fee_usd"] == 0.01


@pytest.mark.asyncio
async def test_sanctions_clear(monkeypatch):
    monkeypatch.setattr(x402_server, "USE_MOCK_APIS", False)
    req = _make_post_request({"address": "0x742d35Cc6634C0532925a3b8D4C3b4E6C8e07e01"})
    out = await x402_server.sanctions_screen(req)
    assert out["cleared"] is True
    assert out["fee_usd"] == 0.05


@pytest.mark.asyncio
async def test_sanctions_blocks_known_address(monkeypatch):
    monkeypatch.setattr(x402_server, "USE_MOCK_APIS", False)
    req = _make_post_request({"address": "0x7F367cC41522cE07553e823bf3be79A889DEBE1B"})
    out = await x402_server.sanctions_screen(req)
    assert out["cleared"] is False
    assert "OFAC" in out["reason"]


def test_health_endpoint():
    from fastapi.testclient import TestClient

    client = TestClient(x402_server.app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
