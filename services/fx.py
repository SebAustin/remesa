"""
services/fx.py — FX quote client.

Thin async client for the x402-priced ``/fx-quote`` endpoint. The agent graph
(agent/nodes.py:quote_fx) calls ``fetch_fx_quote`` with an ``x402HttpxClient`` so
the $0.01 USDC micropayment settles automatically; the settlement tx hash is
read back from the ``x-payment-response`` header for the receipt.
"""
import httpx
import structlog

from config import X402_BASE_URL
from services._payments import payment_tx_from_response

log = structlog.get_logger()


async def fetch_fx_quote(x402_client, base_url: str = X402_BASE_URL) -> dict:
    """
    Call /fx-quote via the x402 paying client.

    Returns the parsed JSON body with an extra ``_payment_tx`` key holding the
    onchain settlement hash of the micropayment (or a zero hash if unavailable).
    """
    response = await x402_client.get(f"{base_url}/fx-quote")
    data = response.json()
    data["_payment_tx"] = payment_tx_from_response(response)
    log.info("FX quote fetched", rate=data.get("rate_mxn_per_usd"))
    return data


async def fetch_fx_quote_plain(base_url: str = X402_BASE_URL) -> dict:
    """Call /fx-quote with a plain client (no payment) — for local testing."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{base_url}/fx-quote")
        return response.json()
