"""
services/fx.py — FX quote client.

Thin SYNCHRONOUS client for the x402-priced ``/fx-quote`` endpoint. The agent
graph (agent/nodes.py:quote_fx) calls ``fetch_fx_quote`` with an x402
``requests.Session`` via ``asyncio.to_thread`` — sync because the CDP wallet
signs the $0.01 micropayment with ``loop.run_until_complete`` (see
remesa-agentkit-sync-blocking). The settlement tx hash is read back from the
``x-payment-response`` header for the receipt.
"""
import httpx
import structlog

from config import X402_BASE_URL
from services._payments import ensure_paid_ok, payment_tx_from_response

log = structlog.get_logger()


def fetch_fx_quote(x402_session, base_url: str = X402_BASE_URL) -> dict:
    """
    Call /fx-quote via the x402 paying session (SYNC — run via asyncio.to_thread).

    Returns the parsed JSON body with an extra ``_payment_tx`` key holding the
    onchain settlement hash of the micropayment (or a zero hash if unavailable).
    """
    response = x402_session.get(f"{base_url}/fx-quote")
    ensure_paid_ok(response)
    data = response.json()
    data["_payment_tx"] = payment_tx_from_response(response)
    log.info("FX quote fetched", rate=data.get("rate_mxn_per_usd"))
    return data


async def fetch_fx_quote_plain(base_url: str = X402_BASE_URL) -> dict:
    """Call /fx-quote with a plain client (no payment) — for local testing."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{base_url}/fx-quote")
        return response.json()
