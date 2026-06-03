"""
tests/test_nodes.py — unit tests for the LangGraph nodes.

These exercise the pure decision logic with fakes for the LLM and x402 client,
so they run with no network, no API keys, and no real wallet.
"""
import pytest

from agent import nodes

DEMO_ADDR = "0x742d35Cc6634C0532925a3b8D4C3b4E6C8e07e01"


# ── parse_intent ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_parse_intent_happy_path(fake_llm_factory):
    fake_llm_factory(
        '{"action":"send_usdc","amount_usd":5,'
        f'"recipient_address":"{DEMO_ADDR}","recipient_name":"mama"}}'
    )
    out = await nodes.parse_intent({"user_message": "send 5 to mama"})
    assert out["status"] == "pending"
    assert out["intent"]["amount_usd"] == 5.0
    assert out["intent"]["recipient_name"] == "mama"
    # Address is checksummed.
    assert out["intent"]["recipient_address"].startswith("0x")


@pytest.mark.asyncio
async def test_parse_intent_rejects_over_cap(fake_llm_factory):
    fake_llm_factory(
        '{"action":"send_usdc","amount_usd":999,'
        f'"recipient_address":"{DEMO_ADDR}","recipient_name":"mama"}}'
    )
    out = await nodes.parse_intent({"user_message": "send 999 to mama"})
    assert out["status"] == "failed"
    assert "cap" in out["error"].lower()


@pytest.mark.asyncio
async def test_parse_intent_rejects_bad_address(fake_llm_factory):
    fake_llm_factory(
        '{"action":"send_usdc","amount_usd":5,'
        '"recipient_address":"not-an-address","recipient_name":"x"}'
    )
    out = await nodes.parse_intent({"user_message": "send 5 to nowhere"})
    assert out["status"] == "failed"
    assert "address" in out["error"].lower()


# ── quote_fx ──────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_quote_fx_returns_quote(patch_x402, fake_x402_session):
    session = fake_x402_session(get_payload={"rate_mxn_per_usd": 17.15, "fee_usd": 0.01})
    patch_x402(session)
    out = await nodes.quote_fx({"intent": {}}, agent_kit=object())
    assert out["fx_quote"]["rate_mxn_per_usd"] == 17.15
    assert out["fx_quote"]["x402_tx_hash"].startswith("0x")


# ── check_sanctions ───────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_check_sanctions_clear(patch_x402, fake_x402_session):
    session = fake_x402_session(
        post_payload={"cleared": True, "reason": "No match found"}
    )
    patch_x402(session)
    state = {"intent": {"recipient_address": DEMO_ADDR}}
    out = await nodes.check_sanctions(state, agent_kit=object())
    assert out["sanctions_result"]["cleared"] is True
    assert "status" not in out  # does not short-circuit


@pytest.mark.asyncio
async def test_check_sanctions_blocks(patch_x402, fake_x402_session):
    session = fake_x402_session(
        post_payload={"cleared": False, "reason": "Address on OFAC SDN list"}
    )
    patch_x402(session)
    state = {"intent": {"recipient_address": DEMO_ADDR}}
    out = await nodes.check_sanctions(state, agent_kit=object())
    assert out["status"] == "failed"
    assert "sanctions" in out["error"].lower()


# ── generate_receipt ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_generate_receipt_math():
    state = {
        "intent": {
            "amount_usd": 200.0,
            "recipient_address": DEMO_ADDR,
            "recipient_name": "mama",
        },
        "fx_quote": {"rate_mxn_per_usd": 17.15, "fee_usd": 0.01, "x402_tx_hash": "0xaa"},
        "sanctions_result": {
            "cleared": True, "reason": "ok", "fee_usd": 0.05, "x402_tx_hash": "0xbb",
        },
        "transfer_tx_hash": "0x" + "cd" * 32,
    }
    out = await nodes.generate_receipt(state)
    r = out["receipt"]
    assert r["total_fees_usd"] == pytest.approx(0.06)
    assert r["mxn_amount"] == pytest.approx(3430.0)
    assert r["wu_fee_usd"] == pytest.approx(9.9)
    assert r["savings_usd"] == pytest.approx(9.84)
    assert len(r["micropayments"]) == 2
    assert "Remesa enviada" in r["telegram_msg"]


# ── tx hash extraction ────────────────────────────────────────────────────────
def test_extract_tx_hash_from_dict():
    h = "0x" + "9" * 64
    assert nodes._extract_tx_hash({"transaction_hash": h}) == h


def test_extract_tx_hash_from_string():
    h = "0x" + "7" * 64
    assert nodes._extract_tx_hash(f"Transferred 5 USDC, tx {h} confirmed") == h
