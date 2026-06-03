"""
scripts/print_wallet_address.py — boot the agent wallet and print its address.

Use this to fill in X402_RECEIVER_ADDRESS in your .env: the agent "pays itself"
for its tool calls, so the x402 receiver should be the agent's own wallet.

Usage:
    python scripts/print_wallet_address.py          # print address + balances
    python scripts/print_wallet_address.py --faucet # also request testnet funds

Requires CDP_API_KEY_ID, CDP_API_KEY_SECRET, CDP_WALLET_SECRET in .env.
"""
import asyncio
import sys
from pathlib import Path

# Make the project root importable when run as `python scripts/...`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from wallet.setup import build_agent_kit, ensure_funded  # noqa: E402


def _check_creds() -> None:
    missing = [
        name
        for name in ("CDP_API_KEY_ID", "CDP_API_KEY_SECRET", "CDP_WALLET_SECRET")
        if not getattr(config, name)
    ]
    if missing:
        print("❌ Missing CDP credentials in .env: " + ", ".join(missing))
        print("   See README / portal.cdp.coinbase.com to generate them.")
        sys.exit(1)


def _usdc_balance(agent_kit) -> str:
    """Best-effort USDC balance via the ERC20 get_balance action (SYNC)."""
    for action in agent_kit.get_actions():
        if action.name.endswith("ERC20ActionProvider_get_balance"):
            try:
                return str(action.invoke({"contract_address": config.ACTIVE_USDC}))
            except Exception as exc:  # noqa: BLE001
                return f"(unavailable: {exc})"
    return "(no erc20 get_balance action)"


def main() -> None:
    _check_creds()
    want_faucet = "--faucet" in sys.argv

    # Build the kit OUTSIDE any event loop — its constructor calls asyncio.run()
    # internally (see remesa-agentkit-sync-blocking).
    try:
        agent_kit = build_agent_kit()
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Failed to initialize the CDP wallet: {exc}")
        if "padding" in str(exc).lower() or "EC key" in str(exc):
            print(
                "   → CDP_API_KEY_SECRET looks malformed. Common causes:\n"
                "     • the value lost its PEM newlines — wrap it in single quotes\n"
                "       in .env, or keep the literal \\n sequences intact;\n"
                "     • stray surrounding quotes or whitespace;\n"
                "     • you pasted the API key *name/ID* instead of the secret.\n"
                "   Regenerate under portal.cdp.coinbase.com → Secret API Keys."
            )
        sys.exit(1)
    wallet = agent_kit.wallet_provider
    address = wallet.get_address()

    print()
    print("  Network : ", config.ACTIVE_NETWORK)
    print("  Address : ", address)
    try:
        print("  ETH     : ", wallet.get_balance(), "(wei)")
    except Exception as exc:  # noqa: BLE001
        print("  ETH     :  (unavailable:", exc, ")")
    # ERC20 action signs/reads via the blocking wallet; run it off any loop.
    print("  USDC    : ", asyncio.run(asyncio.to_thread(_usdc_balance, agent_kit)))

    if want_faucet:
        print("\n  Requesting Base Sepolia faucet funds...")
        asyncio.run(ensure_funded(agent_kit))

    print()
    print("  → Put this in .env:")
    print(f"     X402_RECEIVER_ADDRESS={address}")
    print()


if __name__ == "__main__":
    main()
