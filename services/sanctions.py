"""
services/sanctions.py — Sanctions screen client.

Thin SYNCHRONOUS client for the x402-priced ``/sanctions-screen`` endpoint. The
agent graph (agent/nodes.py:check_sanctions) calls ``screen_address`` with an
x402 ``requests.Session`` via ``asyncio.to_thread`` — sync because the CDP wallet
signs the $0.05 micropayment with ``loop.run_until_complete``. The settlement tx
hash is read back from the ``x-payment-response`` header.
"""
import httpx
import structlog

from config import X402_BASE_URL
from services._payments import ensure_paid_ok, payment_tx_from_response

log = structlog.get_logger()


def screen_address(
    x402_session, address: str, base_url: str = X402_BASE_URL
) -> dict:
    """
    Call /sanctions-screen via the x402 paying session (SYNC — via to_thread).

    Returns the parsed JSON body with an extra ``_payment_tx`` key holding the
    onchain settlement hash of the micropayment.
    """
    response = x402_session.post(
        f"{base_url}/sanctions-screen",
        json={"address": address},
    )
    ensure_paid_ok(response)
    data = response.json()
    data["_payment_tx"] = payment_tx_from_response(response)
    log.info("Sanctions screen fetched", address=address, cleared=data.get("cleared"))
    return data


async def screen_address_plain(address: str, base_url: str = X402_BASE_URL) -> dict:
    """Call /sanctions-screen with a plain client (no payment) — for testing."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{base_url}/sanctions-screen", json={"address": address}
        )
        return response.json()
