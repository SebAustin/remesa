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


class _FakeX402Session:
    """
    Stand-in for the x402 ``requests.Session`` (SYNC). Records calls, returns
    canned JSON, and carries a fake settlement header so the receipt path runs.
    """

    def __init__(self, get_payload=None, post_payload=None):
        self._get_payload = get_payload or {}
        self._post_payload = post_payload or {}
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return _FakeResponse(self._get_payload)

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return _FakeResponse(self._post_payload)


@pytest.fixture
def fake_x402_session():
    return _FakeX402Session


@pytest.fixture
def patch_x402(monkeypatch):
    """Patch agent.nodes.get_x402_session to return a provided fake session."""
    import agent.nodes as nodes

    def _install(session):
        monkeypatch.setattr(nodes, "get_x402_session", lambda _ak: session)

    return _install
