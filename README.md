<!-- SUBMISSION CHECKLIST
[ ] GitHub public, clean commit history
[ ] Demo video: 2-4 min, opens with $64.7B LATAM stat, shows itemized receipt
[ ] All three tracks named in BUIDL description
[ ] Sponsor sections below are filled in
[ ] Live testnet demo URL or Replit link added
-->

# Remesa 🌎 — AI Remittances on Base

> Your AI agent sends money home. And pays its own way.

[![Demo Video](docs/demo_thumbnail.png)](YOUR_DEMO_VIDEO_URL)

## The Problem

45 million Americans send **$64.7B/year to Mexico**. Western Union charges ~5%
($9.90 on a $200 transfer). The recipient waits 3-5 days. Half of Mexicans are
unbanked — they need cash, not bank accounts.

## What Remesa Does

Remesa is a Telegram AI agent powered by LangGraph that:

1. Parses a natural-language transfer request ("send $20 to mama")
2. Quotes the best FX rate — **paying $0.01 USDC for the quote via x402**
3. Runs a sanctions screen — **paying $0.05 USDC for the check via x402**
4. Asks the user to confirm before broadcasting
5. Executes a USDC transfer on Base in seconds
6. Returns an itemized receipt showing **every fee the AI paid onchain**

Total fee: **$0.18 on a $200 transfer (0.09%)** vs. Western Union's $9.90.

## The Wow Moment: Itemized Agent Receipt

```
✅ Remesa enviada
📤 Sent: $200.00 USDC
📥 Recipient: mama (0x742d…7e01)
💱 Rate: 17.15 MXN/USD ≈ 3,430 MXN

🤖 Agent micropayments (your AI paid for its tools):
  • FX Quote API:      $0.01 → tx 0xabc1…ef23
  • Sanctions Screen:  $0.05 → tx 0xdef4…ab56

💰 Total fees: $0.18 (0.09%)
   vs. Western Union: ~$9.90 (4.95%)
   You saved: $9.72
```

## Architecture

```
User → Telegram → LangGraph StateGraph
                      ├── parse_intent (Claude Sonnet)
                      ├── quote_fx ──────────────→ x402 FastAPI /fx-quote ($0.01 USDC)
                      ├── check_sanctions ────────→ x402 FastAPI /sanctions-screen ($0.05)
                      ├── confirm_with_user [INTERRUPT — human approval required]
                      ├── execute_transfer ───────→ Base Sepolia USDC transfer (AgentKit)
                      ├── notify_recipient
                      └── generate_receipt ───────→ Itemized receipt to Telegram
```

Failure/cancellation at any pre-execution node short-circuits straight to END
via conditional routing, so the agent never broadcasts an unconfirmed or
sanctioned transfer.

## Tech Stack

- **LangGraph** — stateful agent orchestration with human-in-the-loop interrupts
- **Coinbase AgentKit** (CdpEvmWalletProvider) — MPC wallet + USDC transfers on Base
- **x402 Protocol** — agent pays for its own tool calls ($0.01/$0.05 per call)
- **Circle USDC + CCTP V2** — native stablecoin transfers, 20-second finality
- **Base Sepolia** (`base-sepolia`) — L2 with Circle Paymaster (gasless for users)
- **python-telegram-bot v21** — consumer UX, no app install required
- **LangSmith** — live trace observability during judging
- **Claude Sonnet 4.5** — intent parsing and confirmation copy

## How We Used Each Sponsor

### Coinbase CDP / AgentKit / x402

The agent wallet is provisioned via `CdpEvmWalletProvider` on Base Sepolia.
AgentKit's `x402_action_provider` handles buyer-side micropayments transparently —
the LangGraph nodes call our FastAPI endpoints just like any HTTP API; the x402
layer intercepts the 402 response and signs a gasless EIP-3009 USDC
authorization. The `erc20_action_provider` executes the final USDC transfer.

### Circle USDC + Circle Paymaster

All transfers are in native USDC. The Circle Paymaster is configured to sponsor
gas so Mexican recipients with no ETH can receive funds without any setup. CCTP
V2 Fast Transfer enables cross-chain settlement in ~20 seconds.

### Base (L2)

Base Sepolia is the deployment network. USDC is native on Base, Circle Paymaster
is available, and Base's EIP-4337 AA support lets us offer gasless UX.

## Setup

This project targets **Python 3.11+**. The repo uses [`uv`](https://docs.astral.sh/uv/)
(macOS system Python is often 3.9, which is too old).

```bash
git clone https://github.com/SebAustin/remesa
cd remesa
cp .env.example .env          # fill in your keys

# with uv (recommended — pins a 3.11 interpreter automatically)
uv venv --python 3.11
uv pip install -e ".[dev]"

# or with pip on an existing 3.11+ interpreter
# pip install -e ".[dev]"

python main.py
```

### Verify the install

```bash
# x402 server standalone
uvicorn services.x402_server:app --port 8402 --reload
curl http://localhost:8402/health

# run the tests (no network/keys needed — uses fakes)
pytest tests/ -v
```

### Run the full graph end-to-end (programmatically)

`build_graph` is **async** (it opens a SQLite checkpointer), so await it:

```python
import asyncio
from langgraph.types import Command
from wallet.setup import build_agent_kit
from agent.graph import build_graph

async def run():
    ak = build_agent_kit()
    g = await build_graph(ak)
    cfg = {"configurable": {"thread_id": "test-001"}}
    state = {
        "thread_id": "test-001",
        "user_message": "send 10 to mama at 0x742d35Cc6634C0532925a3b8D4C3b4E6C8e07e01",
        "status": "pending", "intent": None, "fx_quote": None,
        "sanctions_result": None, "transfer_tx_hash": None,
        "receipt": None, "error": None,
    }
    # Runs until the confirm interrupt:
    first = await g.ainvoke(state, cfg)
    print(first["__interrupt__"][0].value["message"])
    # Resume with the user's confirmation:
    final = await g.ainvoke(Command(resume="YES"), cfg)
    print(final["receipt"]["telegram_msg"])
    await g.aclose()

asyncio.run(run())
```

## Project Layout

```
remesa/
├── config.py                 # constants + env loading (single source of truth)
├── main.py                   # entry point — runs bot + x402 server concurrently
├── agent/
│   ├── state.py              # AgentState TypedDict
│   ├── nodes.py              # one async function per node
│   ├── graph.py              # StateGraph wiring + conditional routing
│   └── tools.py              # optional AgentKit↔LangChain bridge
├── services/
│   ├── x402_server.py        # FastAPI app, x402-priced endpoints
│   ├── fx.py                 # FX quote client
│   └── sanctions.py          # sanctions screen client
├── wallet/setup.py           # AgentKit factory + faucet helper
├── telegram_bot/             # NOT "telegram" — avoids shadowing the PTB library
│   ├── bot.py
│   └── handlers.py
└── tests/
```

## Implementation Notes (deviations from the original spec)

A few changes were made so the code actually runs as wired:

- **`telegram/` → `telegram_bot/`**: a local package named `telegram` shadows the
  `python-telegram-bot` library, breaking every `from telegram import ...`.
- **Graph routing**: the spec mixed static `add_edge` *and* `add_conditional_edges`
  on the same nodes. We use conditional edges only (next-node-or-END), which is
  the valid LangGraph pattern.
- **Checkpointer**: `AsyncSqliteSaver.from_conn_string` returns an async context
  manager, so `build_graph` is async and keeps the connection alive (with
  `aclose()` for shutdown). A `build_graph_in_memory` variant exists for tests.
- **Single interrupt**: human-in-the-loop uses the dynamic `interrupt()` inside
  `confirm_with_user`; `interrupt_before` was removed to avoid double-pausing.
- **`main.py`**: `Application.run_polling()` can't run inside `asyncio.gather`, so
  the bot lifecycle is driven manually alongside uvicorn.
- **Dependency versions / API surface**: the original spec pinned
  `x402>=3.0.0a1` and `coinbase-agentkit>=0.4.0` with an invented API. The real,
  installed versions are `x402==1.0.0` (coinbase-agentkit pins `x402<2`) and
  `coinbase-agentkit>=0.7.0`, so the wiring was rebuilt against the actual API:
  - x402 server gate: `x402.fastapi.middleware.require_payment` (per-path, price
    as `"$0.01"`), not `PaymentMiddlewareASGI` + `RouteConfig`.
  - x402 buyer: `x402.clients.httpx.x402HttpxClient(account=...)`, fed by
    `wallet_provider.to_signer()`, not `AsyncPayingClient(wallet_provider=...)`.
  - Settlement tx hash for the receipt is decoded from the `x-payment-response`
    header via `x402.clients.decode_x_payment_response`.
  - Network is the string `"base-sepolia"`, not CAIP-2 `eip155:84532`.
  - USDC transfer uses the `ERC20ActionProvider_transfer` action with the amount
    in **whole units** (AgentKit converts decimals); invoked via
    `agent_kit.get_actions()` → `action.invoke(...)` (there is no
    `execute_action`).
  - Faucet is requested through `wallet_provider.get_client()` (CDP client);
    `CdpEvmWalletProvider` has no `request_faucet`/token-arg `get_balance`.
- **x402 / AgentKit imports** are still loaded defensively where signatures may
  drift; mismatches log a clear warning instead of crashing.

## Roadmap

- **Near-term:** Off-ramp via Bitso API (USDC → MXN → SPEI instant transfer to any Mexican bank)
- **Mid-term:** Multi-chain support (Polygon/Arbitrum) via CCTP V2 + multi-leg routing
- **Business case:** $64.7B corridor × 0.09% fee = $58M TAM at 0.1% market share
