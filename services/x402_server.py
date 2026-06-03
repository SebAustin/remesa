"""
services/x402_server.py — FastAPI app exposing two x402-priced endpoints.

  GET  /fx-quote           → costs $0.01 USDC, returns MXN/USD rate
  POST /sanctions-screen   → costs $0.05 USDC, returns OFAC clearance

Run standalone with:   uvicorn services.x402_server:app --port 8402 --reload
or let main.py start it alongside the Telegram bot.

x402 API (verified against x402==1.0.0)
---------------------------------------
The payment gate is ``x402.fastapi.middleware.require_payment`` — a per-path
middleware factory registered with ``app.middleware("http")(...)``. ``price``
takes a human-readable dollar string ("$0.01"); ``network`` is "base-sepolia".
If the receiver address is unset (e.g. unit tests), the gate is skipped so the
endpoints stay reachable.
"""
import httpx
import structlog
from fastapi import FastAPI, Request

from config import (
    ACTIVE_NETWORK,
    FX_QUOTE_PRICE,
    SANCTIONS_PRICE,
    USE_MOCK_APIS,
    X402_FACILITATOR_URL,
    X402_RECEIVER_ADDRESS,
)

log = structlog.get_logger()

app = FastAPI(title="Remesa x402 API", version="0.1.0")


# ── x402 payment middleware ───────────────────────────────────────────────────
def _install_x402_middleware(fastapi_app: FastAPI) -> bool:
    """
    Gate /fx-quote ($0.01) and /sanctions-screen ($0.05) behind x402 payments.
    Returns True if the gate was installed.
    """
    if not X402_RECEIVER_ADDRESS or X402_RECEIVER_ADDRESS.startswith("0xYour"):
        log.warning(
            "X402_RECEIVER_ADDRESS unset — serving WITHOUT payment gating "
            "(fine for tests/mock demos, not for the real x402 flow)."
        )
        return False
    try:
        from x402.facilitator import FacilitatorConfig
        from x402.fastapi.middleware import require_payment

        facilitator = FacilitatorConfig(url=X402_FACILITATOR_URL)
        for path, price in (
            ("/fx-quote", FX_QUOTE_PRICE),
            ("/sanctions-screen", SANCTIONS_PRICE),
        ):
            fastapi_app.middleware("http")(
                require_payment(
                    price=price,
                    pay_to_address=X402_RECEIVER_ADDRESS,
                    path=path,
                    network=ACTIVE_NETWORK,
                    facilitator_config=facilitator,
                )
            )
        log.info("x402 middleware installed", receiver=X402_RECEIVER_ADDRESS)
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "x402 middleware NOT installed — endpoints will serve WITHOUT payment "
            "gating. Verify the x402 SDK version/import path.",
            error=str(exc),
        )
        return False


X402_ENABLED = _install_x402_middleware(app)


# ── Endpoints ─────────────────────────────────────────────────────────────────
MOCK_FX = {"rate_mxn_per_usd": 17.15, "source": "mock", "fee_usd": 0.01}
MOCK_SANCTIONS = {"cleared": True, "reason": "No match found (mock)", "fee_usd": 0.05}


@app.get("/fx-quote")
async def fx_quote(from_currency: str = "USD", to_currency: str = "MXN") -> dict:
    """
    Return the current FX rate. Costs $0.01 USDC via x402.
    In production, calls a live FX API (open.er-api.com here).
    """
    if USE_MOCK_APIS:
        log.info("FX quote (mock)", rate=MOCK_FX["rate_mxn_per_usd"])
        return MOCK_FX
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"https://open.er-api.com/v6/latest/{from_currency}")
            data = r.json()
            rate = data["rates"][to_currency]
            log.info("FX quote (live)", rate=rate)
            return {"rate_mxn_per_usd": rate, "source": "exchangerate", "fee_usd": 0.01}
    except Exception as exc:  # noqa: BLE001
        log.warning("FX API failed, using mock", error=str(exc))
        return MOCK_FX


@app.post("/sanctions-screen")
async def sanctions_screen(request: Request) -> dict:
    """
    Check an Ethereum address against a mock OFAC SDN list. Costs $0.05 USDC.
    In production, calls a real sanctions API (Chainalysis, Elliptic, etc.).
    """
    body = await request.json()
    address = body.get("address", "")

    if USE_MOCK_APIS:
        log.info("Sanctions screen (mock)", address=address, cleared=True)
        return MOCK_SANCTIONS

    # OFAC-sanctioned Ethereum addresses are public; a small hardcoded blocklist
    # is enough to demonstrate a real positive/negative result for the hackathon.
    KNOWN_SANCTIONED = {
        "0x7F367cC41522cE07553e823bf3be79A889DEBE1B",  # Lazarus Group (public OFAC)
        "0xd882cFc20F52f2599D84b8e8D58C7FB62cfE344b",
    }
    cleared = address not in KNOWN_SANCTIONED
    log.info("Sanctions screen", address=address, cleared=cleared)
    return {
        "cleared": cleared,
        "reason": "Address on OFAC SDN list" if not cleared else "No match found",
        "fee_usd": 0.05,
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "remesa-x402-server", "x402_enabled": X402_ENABLED}
