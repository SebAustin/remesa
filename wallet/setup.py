"""
wallet/setup.py — CdpEvmWalletProvider factory and faucet helper.

Uses the current (non-deprecated) AgentKit API surface. The x402 buyer-side
action provider moved import paths across AgentKit releases, so it is loaded
defensively: if it cannot be found, AgentKit still builds and the graph nodes
fall back to the standalone x402 session (agent/nodes.py:get_x402_session).
"""
import structlog

from coinbase_agentkit import (
    AgentKit,
    AgentKitConfig,
    CdpEvmWalletProvider,
    CdpEvmWalletProviderConfig,
    erc20_action_provider,
    wallet_action_provider,
    x402_action_provider,
)

from config import (
    ACTIVE_NETWORK,
    CDP_API_KEY_ID,
    CDP_API_KEY_SECRET,
    CDP_WALLET_SECRET,
)

log = structlog.get_logger()


def _maybe_x402_provider():
    """
    Return AgentKit's x402 action provider. In coinbase-agentkit 0.7.x this is a
    top-level factory taking no args; wrapped defensively so a future signature
    change degrades to the standalone httpx buyer client instead of crashing.
    """
    try:
        return x402_action_provider()
    except Exception as exc:  # noqa: BLE001
        log.warning("x402 action provider unavailable — using httpx fallback",
                    error=str(exc))
        return None


def build_agent_kit() -> AgentKit:
    """
    Instantiate the Coinbase AgentKit with:
      - CdpEvmWalletProvider on Base Sepolia (testnet)
      - erc20_action_provider for USDC transfers
      - x402_action_provider for buyer-side micropayments (if available)
    """
    wallet_config = CdpEvmWalletProviderConfig(
        api_key_id=CDP_API_KEY_ID,
        api_key_secret=CDP_API_KEY_SECRET,
        wallet_secret=CDP_WALLET_SECRET,
        network_id=ACTIVE_NETWORK,  # "eip155:84532" — CAIP-2 required
    )
    wallet_provider = CdpEvmWalletProvider(wallet_config)

    action_providers = [wallet_action_provider(), erc20_action_provider()]
    x402_provider = _maybe_x402_provider()
    if x402_provider is not None:
        action_providers.append(x402_provider)

    agent_kit = AgentKit(
        AgentKitConfig(
            wallet_provider=wallet_provider,
            action_providers=action_providers,
        )
    )
    log.info("AgentKit initialized", network=ACTIVE_NETWORK)
    return agent_kit


async def ensure_funded(agent_kit: AgentKit) -> None:
    """
    Request Base Sepolia faucet funds (ETH for gas + USDC) for the agent wallet.

    Best-effort: ``CdpEvmWalletProvider`` exposes the faucet through its CDP
    client (``get_client()``), not a ``request_faucet`` method. Logs and
    continues on any error so startup never blocks on faucet availability —
    fund the wallet manually from https://faucet.circle.com if this fails.
    """
    wallet = agent_kit.wallet_provider
    address = wallet.get_address()
    log.info("Agent wallet", address=address, network=ACTIVE_NETWORK)

    try:
        client = wallet.get_client()
    except Exception as exc:  # noqa: BLE001
        log.warning("CDP client unavailable — fund wallet manually", error=str(exc))
        return

    async def _request(token: str) -> None:
        try:
            faucet = client.evm.request_faucet(
                address=address, network=ACTIVE_NETWORK, token=token
            )
            import inspect

            if inspect.isawaitable(faucet):
                await faucet
            log.info("Faucet requested", token=token)
        except Exception as exc:  # noqa: BLE001
            log.warning("Faucet request failed", token=token, error=str(exc))

    # Use the client as an async context manager when supported.
    if hasattr(client, "__aenter__"):
        async with client:
            await _request("eth")
            await _request("usdc")
    else:
        await _request("eth")
        await _request("usdc")
