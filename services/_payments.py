"""
services/_payments.py — helpers for reading x402 settlement details.

After a paid x402 request, the facilitator returns an ``X-PAYMENT-RESPONSE``
header containing the base64-encoded settlement result. We decode it to surface
the real onchain tx hash in the user's receipt — the wow moment of the demo.
"""
import structlog

log = structlog.get_logger()

ZERO_HASH = "0x" + "0" * 64


def payment_tx_from_response(response) -> str:
    """
    Extract the settlement tx hash from an httpx Response's payment header.

    Returns ZERO_HASH if the header is absent (e.g. payment gate disabled in a
    mock/test run) or cannot be decoded.
    """
    headers = getattr(response, "headers", None) or {}
    header = headers.get("x-payment-response")
    if not header:
        return ZERO_HASH
    try:
        from x402.clients import decode_x_payment_response

        decoded = decode_x_payment_response(header)
        return decoded.get("transaction") or ZERO_HASH
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not decode x-payment-response", error=str(exc))
        return ZERO_HASH
