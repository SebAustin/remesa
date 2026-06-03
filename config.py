"""
config.py — single source of truth for all constants and env loading.

All other modules import from here. Never call os.environ directly elsewhere.

Required env vars raise KeyError on import if missing; optional vars fall back
to sane defaults so the x402 server and unit tests can run without a full
production secret set.
"""
import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    """Fetch a required env var with a friendly error if absent."""
    try:
        return os.environ[name]
    except KeyError as exc:  # pragma: no cover - exercised via error path
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and fill it in."
        ) from exc


# ── Coinbase / Base ──────────────────────────────────────────────────────────
CDP_API_KEY_ID = os.environ.get("CDP_API_KEY_ID", "")
CDP_API_KEY_SECRET = os.environ.get("CDP_API_KEY_SECRET", "")
CDP_WALLET_SECRET = os.environ.get("CDP_WALLET_SECRET", "")
# Pin a wallet so the SAME account is reused across restarts. If empty, CDP
# mints a BRAND-NEW wallet on every run (different address each time).
CDP_WALLET_ADDRESS = os.environ.get("CDP_WALLET_ADDRESS", "")

# Coinbase AgentKit / CDP and x402 both use plain network-id strings here
# (e.g. "base-sepolia"), NOT the CAIP-2 "eip155:84532" form.
TESTNET_NETWORK = "base-sepolia"
MAINNET_NETWORK = "base-mainnet"

USDC_BASE_SEPOLIA = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
USDC_BASE_MAINNET = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_DECIMALS = 6  # USDC is 6 decimals, NOT 18

ACTIVE_NETWORK = TESTNET_NETWORK  # used for both CDP wallet and x402 middleware
ACTIVE_USDC = USDC_BASE_SEPOLIA

# ── x402 ─────────────────────────────────────────────────────────────────────
X402_RECEIVER_ADDRESS = os.environ.get("X402_RECEIVER_ADDRESS", "")
X402_FACILITATOR_URL = "https://x402.org/facilitator"  # free testnet facilitator
X402_SERVER_PORT = int(os.environ.get("X402_SERVER_PORT", "8402"))
X402_BASE_URL = os.environ.get("X402_BASE_URL", f"http://localhost:{X402_SERVER_PORT}")

# require_payment() accepts human-readable dollar price strings.
FX_QUOTE_PRICE = "$0.01"
SANCTIONS_PRICE = "$0.05"
FX_QUOTE_PRICE_USDC = 10_000   # $0.01 in raw USDC units (for reference/receipts)
SANCTIONS_PRICE_USDC = 50_000  # $0.05 in raw USDC units

# Hard cap on a single x402 micropayment the buyer client will authorize (raw).
X402_MAX_PAYMENT_RAW = 500_000  # $0.50

# ── LLM ──────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-4-6")

# ── Telegram ─────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# ── Demo safety ──────────────────────────────────────────────────────────────
USE_MOCK_APIS = os.environ.get("USE_MOCK_APIS", "false").lower() == "true"
MAX_TRANSFER_USD = float(os.environ.get("MAX_TRANSFER_USD", "100.0"))

# ── Receipt economics ─────────────────────────────────────────────────────────
# Remesa's fees are FLAT (FX + sanctions), so the % advantage only shows at real
# remittance sizes. The receipt projects savings at the corridor-average amount.
WU_FEE_PCT = 0.0495                 # Western Union ~4.95%
REFERENCE_REMITTANCE_USD = 200.0    # avg US→MX remittance, for the projection line


# ── Helpers ──────────────────────────────────────────────────────────────────
def usd_to_raw(amount_usd: float) -> int:
    """Convert dollar amount to raw USDC units (6 decimals)."""
    return int(round(amount_usd * 10 ** USDC_DECIMALS))


def raw_to_usd(raw: int) -> float:
    """Convert raw USDC units to dollar amount."""
    return raw / 10 ** USDC_DECIMALS


def short_hash(tx_hash: str) -> str:
    """Truncate a tx hash for display: 0xabc1…ef23"""
    if not tx_hash:
        return "—"
    return f"{tx_hash[:6]}…{tx_hash[-4:]}" if len(tx_hash) > 10 else tx_hash


def require_runtime_secrets() -> None:
    """
    Call from main.py at startup to fail fast if production secrets are missing.
    Kept out of import time so the x402 server and unit tests stay importable.
    """
    for name in (
        "CDP_API_KEY_ID",
        "CDP_API_KEY_SECRET",
        "CDP_WALLET_SECRET",
        "X402_RECEIVER_ADDRESS",
        "TELEGRAM_BOT_TOKEN",
    ):
        _require(name)
