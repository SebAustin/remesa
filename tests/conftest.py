"""
tests/conftest.py — shared fixtures and test environment.

Sets dummy env vars BEFORE config is imported anywhere, so the package is
importable without a real .env. Provides fakes for the LLM and x402 client so
node tests run with no network and no API keys.
"""
import os

# Must be set before `config` is imported by any module under test.
os.environ.setdefault("CDP_API_KEY_ID", "test-key-id")
os.environ.setdefault("CDP_API_KEY_SECRET", "test-key-secret")
os.environ.setdefault("CDP_WALLET_SECRET", "test-wallet-secret")
os.environ.setdefault("X402_RECEIVER_ADDRESS", "0x" + "11" * 20)
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic")
os.environ.setdefault("USE_MOCK_APIS", "true")
os.environ.setdefault("MAX_TRANSFER_USD", "10.0")
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")

import pytest


class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeLLM:
    """Stand-in for ChatAnthropic that returns a canned JSON intent."""

    def __init__(self, content: str):
        self._content = content

    async def ainvoke(self, _messages):
        return _FakeMessage(self._content)


@pytest.fixture
def fake_llm_factory(monkeypatch):
    """Patch agent.nodes to use a fake LLM returning the given JSON string."""
    import agent.nodes as nodes

    def _install(json_content: str):
        monkeypatch.setattr(nodes, "_get_llm", lambda: _FakeLLM(json_content))

    return _install


class _FakeResponse:
    def __init__(self, payload: dict, headers: dict | None = None):
        self._payload = payload
        self.headers = headers or {}

    def json(self) -> dict:
        return self._payload


class _FakeX402Client:
    """Records calls and returns canned JSON; exposes a fake settlement hash."""

    def __init__(self, get_payload=None, post_payload=None):
        self._get_payload = get_payload or {}
        self._post_payload = post_payload or {}
        self._last_payment_tx = "0x" + "ab" * 32
        self.calls = []

    async def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return _FakeResponse(self._get_payload)

    async def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return _FakeResponse(self._post_payload)


@pytest.fixture
def fake_x402_client():
    return _FakeX402Client


@pytest.fixture
def patch_x402(monkeypatch):
    """Patch agent.nodes.get_x402_client to return a provided fake client."""
    import agent.nodes as nodes

    def _install(client):
        monkeypatch.setattr(nodes, "get_x402_client", lambda _ak: client)

    return _install
