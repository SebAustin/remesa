"""
agent/nodes.py — One async function per LangGraph node.

Each function takes AgentState and returns a partial update dict. Nodes that
need wallet access take an extra ``agent_kit`` keyword, which ``graph.py`` binds
via ``functools.partial`` before registering the node.
"""
import asyncio
import json
import re

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langgraph.types import interrupt
from web3 import Web3

from agent.state import AgentState, FxQuote, Intent, SanctionsResult
from config import (
    ACTIVE_USDC,
    ANTHROPIC_API_KEY,
    LLM_MODEL,
    MAX_TRANSFER_USD,
    X402_MAX_PAYMENT_RAW,
    short_hash,
)

log = structlog.get_logger()

# ── LLM client (lazy singleton, shared across nodes) ──────────────────────────
_llm: ChatAnthropic | None = None


def _get_llm() -> ChatAnthropic:
    """Build the Claude client lazily so importing this module needs no API key."""
    global _llm
    if _llm is None:
        _llm = ChatAnthropic(
            model=LLM_MODEL,
            api_key=ANTHROPIC_API_KEY,
            max_tokens=512,
        )
    return _llm


# ── x402 buyer session (the agent is the buyer) ───────────────────────────────
# The CDP wallet is sync-blocking (it signs via loop.run_until_complete), so it
# CANNOT sign inside a running event loop. We therefore use x402's SYNC
# requests-based session and drive every call through asyncio.to_thread — in a
# worker thread there is no running loop, so the wallet's signing works. The CDP
# MPC wallet stays the payer, bridged via wallet_provider.to_signer().
#
# IMPORTANT: an x402 requests.Session pays for ONE request only — after a
# successful payment it stops attaching X-PAYMENT on subsequent requests. So we
# build a FRESH session per tool call rather than caching a singleton.
def get_x402_session(agent_kit):
    """Build a single-use sync x402 ``requests.Session`` paying from the CDP wallet."""
    from x402.clients import x402_requests

    return x402_requests(
        account=agent_kit.wallet_provider.to_signer(),
        max_value=X402_MAX_PAYMENT_RAW,  # cap a single micropayment
    )


# ── Node 1: parse_intent ──────────────────────────────────────────────────────
async def parse_intent(state: AgentState) -> dict:
    """
    Use Claude to extract: action, amount_usd, recipient_address, recipient_name
    from a free-text message like "send 50 to mama at 0xabc...".
    """
    prompt = f"""
    Extract the transfer intent from this message. Return a JSON object ONLY,
    no explanation, no markdown fences.
    Fields: action (always "send_usdc"), amount_usd (float),
    recipient_address (string, must start with 0x),
    recipient_name (string, human label or "recipient").

    Message: {state['user_message']}
    """
    try:
        response = await _get_llm().ainvoke([HumanMessage(content=prompt)])
        raw = re.sub(r"```json|```", "", response.content).strip()
        intent_data = json.loads(raw)
    except (json.JSONDecodeError, Exception) as exc:  # noqa: BLE001 - demo-safe
        log.error("Intent parse failed", error=str(exc))
        return {"status": "failed", "error": "Could not understand the request."}

    # Validate address immediately
    try:
        intent_data["recipient_address"] = Web3.to_checksum_address(
            intent_data["recipient_address"]
        )
    except Exception:  # noqa: BLE001
        return {"status": "failed", "error": "Invalid Ethereum address in message."}

    intent_data.setdefault("action", "send_usdc")
    intent_data.setdefault("recipient_name", "recipient")

    # Enforce demo cap
    try:
        amount = float(intent_data["amount_usd"])
    except (KeyError, TypeError, ValueError):
        return {"status": "failed", "error": "Could not read a transfer amount."}

    if amount <= 0:
        return {"status": "failed", "error": "Transfer amount must be positive."}
    if amount > MAX_TRANSFER_USD:
        return {
            "status": "failed",
            "error": f"Demo cap: max ${MAX_TRANSFER_USD:.2f} USDC on testnet.",
        }
    intent_data["amount_usd"] = amount

    log.info("Intent parsed", intent=intent_data)
    return {"intent": Intent(**intent_data), "status": "pending"}


# ── Node 2: quote_fx ──────────────────────────────────────────────────────────
async def quote_fx(state: AgentState, agent_kit) -> dict:
    """
    Call the x402-priced /fx-quote endpoint. The agent pays $0.01 USDC
    autonomously for this tool call and returns the tx hash for the receipt.
    """
    session = get_x402_session(agent_kit)
    try:
        from services.fx import fetch_fx_quote

        # Blocking (signs the x402 payment) — run off the event loop.
        data = await asyncio.to_thread(fetch_fx_quote, session)
        quote = FxQuote(
            rate_mxn_per_usd=data["rate_mxn_per_usd"],
            fee_usd=data.get("fee_usd", 0.01),
            x402_tx_hash=data.get("_payment_tx", "0x" + "0" * 64),
        )
        log.info("FX quote obtained", rate=quote["rate_mxn_per_usd"])
        return {"fx_quote": quote}
    except Exception as exc:  # noqa: BLE001
        log.error("FX quote failed", error=str(exc))
        return {"status": "failed", "error": f"FX quote error: {exc}"}


# ── Node 3: check_sanctions ───────────────────────────────────────────────────
async def check_sanctions(state: AgentState, agent_kit) -> dict:
    """
    Call the x402-priced /sanctions-screen endpoint. The agent pays $0.05 USDC.
    Blocks the transfer if the recipient address is on the OFAC SDN list.
    """
    session = get_x402_session(agent_kit)
    recipient = state["intent"]["recipient_address"]
    try:
        from services.sanctions import screen_address

        # Blocking (signs the x402 payment) — run off the event loop.
        data = await asyncio.to_thread(screen_address, session, recipient)
        result = SanctionsResult(
            cleared=data["cleared"],
            reason=data["reason"],
            fee_usd=data.get("fee_usd", 0.05),
            x402_tx_hash=data.get("_payment_tx", "0x" + "0" * 64),
        )
        log.info("Sanctions check", cleared=result["cleared"])
        if not result["cleared"]:
            return {
                "sanctions_result": result,
                "status": "failed",
                "error": f"Sanctions match: {result['reason']}",
            }
        return {"sanctions_result": result}
    except Exception as exc:  # noqa: BLE001
        log.error("Sanctions check failed", error=str(exc))
        return {"status": "failed", "error": f"Sanctions check error: {exc}"}


# ── Node 4: confirm_with_user [INTERRUPT] ─────────────────────────────────────
async def confirm_with_user(state: AgentState) -> dict:
    """
    MANDATORY human-in-the-loop interrupt before executing any transfer.
    LangGraph's dynamic ``interrupt()`` pauses the graph here; the Telegram
    handler resumes it with ``Command(resume=<user reply>)``.
    """
    intent = state["intent"]
    quote = state["fx_quote"]
    mxn_amount = intent["amount_usd"] * quote["rate_mxn_per_usd"]
    confirmation_msg = (
        f"💸 *Ready to send:*\n"
        f"  Amount: `${intent['amount_usd']:.2f} USDC`\n"
        f"  To: `{short_hash(intent['recipient_address'])}`\n"
        f"  ({intent.get('recipient_name', 'recipient')})\n"
        f"  Rate: `{quote['rate_mxn_per_usd']:.2f} MXN/USD`\n"
        f"  ≈ `{mxn_amount:,.0f} MXN`\n\n"
        f"Reply *YES* to confirm or *NO* to cancel."
    )
    user_reply = interrupt({"message": confirmation_msg})
    if str(user_reply).strip().upper() != "YES":
        return {"status": "cancelled", "error": "User cancelled the transfer."}
    return {"status": "confirmed"}


# ── Node 5: execute_transfer ──────────────────────────────────────────────────
async def execute_transfer(state: AgentState, agent_kit) -> dict:
    """Execute the USDC transfer on Base Sepolia using AgentKit's erc20 action."""
    intent = state["intent"]
    try:
        # The ERC20 transfer action takes the amount in WHOLE units (e.g. "1.5"),
        # not raw 6-decimal units — AgentKit handles the decimal conversion.
        # The CDP wallet signs synchronously (loop.run_until_complete), so this
        # must run off the event loop in a worker thread.
        result = await asyncio.to_thread(
            _invoke_action,
            agent_kit,
            "ERC20ActionProvider_transfer",
            {
                "amount": str(intent["amount_usd"]),
                "contract_address": ACTIVE_USDC,
                "destination_address": intent["recipient_address"],
            },
        )
        tx_hash = _extract_tx_hash(result)
        log.info("Transfer executed", tx_hash=tx_hash, amount_usd=intent["amount_usd"])
        return {"transfer_tx_hash": tx_hash, "status": "executed"}
    except Exception as exc:  # noqa: BLE001
        log.error("Transfer failed", error=str(exc))
        return {"status": "failed", "error": f"Transfer error: {exc}"}


def _invoke_action(agent_kit, action_name: str, params: dict):
    """
    Invoke an AgentKit action by name (SYNCHRONOUS — call via asyncio.to_thread).

    AgentKit exposes actions through its action providers (``get_actions`` →
    ``action.invoke(args)``). The CDP wallet's signing is sync-blocking, so this
    helper is intentionally synchronous and must not be awaited directly.
    """
    for action in agent_kit.get_actions():
        if action.name == action_name or action.name.endswith(action_name):
            return action.invoke(params)
    available = [a.name for a in agent_kit.get_actions()]
    raise RuntimeError(
        f"AgentKit action not found: {action_name}. Available: {available}"
    )


def _extract_tx_hash(result) -> str:
    """AgentKit actions return human-readable strings or dicts; dig out the tx."""
    if isinstance(result, dict):
        return result.get("transaction_hash") or result.get("transactionHash") or (
            "0x" + "0" * 64
        )
    text = str(result)
    match = re.search(r"0x[a-fA-F0-9]{64}", text)
    return match.group(0) if match else "0x" + "0" * 64


# ── Node 6: notify_recipient (optional, show in demo) ─────────────────────────
async def notify_recipient(state: AgentState) -> dict:
    """
    In a real product: send SMS/WhatsApp to the recipient.
    For the hackathon: log and return — the receipt covers this.
    """
    log.info(
        "Recipient notified (mock)",
        recipient=state["intent"]["recipient_address"],
        tx=state.get("transfer_tx_hash"),
    )
    return {}


# ── Node 7: generate_receipt ──────────────────────────────────────────────────
async def generate_receipt(state: AgentState) -> dict:
    """
    Build the itemized receipt dict. This is the wow moment in the demo:
    the agent paid for its own tools — this receipt proves it onchain.
    """
    intent = state["intent"]
    quote = state["fx_quote"]
    sanctions = state["sanctions_result"]
    tx = state.get("transfer_tx_hash", "0x" + "0" * 64)

    total_fees = quote["fee_usd"] + sanctions["fee_usd"]
    fee_pct = (total_fees / intent["amount_usd"]) * 100 if intent["amount_usd"] else 0
    wu_fee = intent["amount_usd"] * 0.0495
    savings = wu_fee - total_fees

    receipt = {
        "amount_usd": intent["amount_usd"],
        "recipient": intent["recipient_address"],
        "recipient_name": intent.get("recipient_name", "recipient"),
        "rate_mxn_per_usd": quote["rate_mxn_per_usd"],
        "mxn_amount": intent["amount_usd"] * quote["rate_mxn_per_usd"],
        "transfer_tx_hash": tx,
        "micropayments": [
            {
                "service": "FX Quote API",
                "fee_usd": quote["fee_usd"],
                "tx_hash": quote["x402_tx_hash"],
            },
            {
                "service": "Sanctions Screen",
                "fee_usd": sanctions["fee_usd"],
                "tx_hash": sanctions["x402_tx_hash"],
            },
        ],
        "total_fees_usd": total_fees,
        "fee_pct": fee_pct,
        "wu_fee_usd": wu_fee,
        "savings_usd": savings,
    }

    telegram_msg = (
        f"✅ *Remesa enviada / Remittance sent*\n\n"
        f"📤 Sent: `${receipt['amount_usd']:.2f} USDC`\n"
        f"📥 Recipient: `{short_hash(intent['recipient_address'])}`\n"
        f"💱 FX Rate: `{receipt['rate_mxn_per_usd']:.2f} MXN/USD`\n"
        f"≈ `{receipt['mxn_amount']:,.0f} MXN`\n\n"
        f"🤖 *Agent micropayments (your AI paid for its own tools):*\n"
    )
    for mp in receipt["micropayments"]:
        telegram_msg += (
            f"  • {mp['service']}: `${mp['fee_usd']:.2f}` "
            f"→ tx `{short_hash(mp['tx_hash'])}`\n"
        )
    telegram_msg += (
        f"\n💰 *Total fees: ${receipt['total_fees_usd']:.2f} "
        f"({receipt['fee_pct']:.2f}%)*\n"
        f"  vs. Western Union: ~${receipt['wu_fee_usd']:.2f} (4.95%)\n"
        f"  You saved: *${receipt['savings_usd']:.2f}*\n\n"
        f"🔗 [View on BaseScan]"
        f"(https://sepolia.basescan.org/tx/{tx})"
    )

    return {"receipt": {**receipt, "telegram_msg": telegram_msg}}
