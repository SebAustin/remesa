<!-- SUBMISSION CHECKLIST
[ ] GitHub public, clean commit history
[ ] Demo video: 2-4 min, opens with $64.7B LATAM stat, shows itemized receipt
[ ] All three tracks named in BUIDL description
[ ] Sponsor sections below are filled in
[ ] Live testnet demo URL or Replit link added
-->

# Remesa 🌎 — AI Remittances on Base

> Your AI agent sends money home. And pays its own way.

[![CI](https://github.com/SebAustin/remesa/actions/workflows/ci.yml/badge.svg)](https://github.com/SebAustin/remesa/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[![Demo Video](docs/demo_thumbnail.png)](YOUR_DEMO_VIDEO_URL)

📹 **Recording the demo?** See [docs/DEMO.md](docs/DEMO.md) for a 90-second script, shot list, and pre-flight checklist.

> **Status:** working end-to-end on **Base Sepolia** — real USDC transfer + two
> real x402 micropayments per run, with human-in-the-loop confirmation. 🧪
> testnet only (no real funds).

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

Remesa's fee is **flat — $0.06 (FX $0.01 + sanctions $0.05), regardless of
amount**. On a typical $200 remittance that's ~0.03% vs. Western Union's $9.90.

## The Wow Moment: Itemized Agent Receipt

The agent paid for its own tools, and the receipt proves it onchain. (Demo runs
send a small testnet amount; the receipt projects the at-scale savings.)

```
✅ Remesa enviada / Remittance sent

📤 Sent: $5.00 USDC
📥 Recipient: 0x742d…7e01
💱 FX Rate: 17.30 MXN/USD ≈ 86 MXN

🤖 Agent micropayments (your AI paid for its own tools):
  • FX Quote API:     $0.01 → tx 0xbf0e…34e2
  • Sanctions Screen: $0.05 → tx 0xeb20…1259

💰 Remesa fee: $0.06 flat (FX + sanctions, any amount)

📊 On a typical $200 remittance:
  Remesa: $0.06 (0.03%)
  Western Union: ~$9.90 (4.95%)
  → You'd save $9.84

🔗 View transfer on BaseScan
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
- **Claude Sonnet 4.6** — intent parsing and confirmation copy

## How We Used Each Sponsor

### Coinbase CDP / AgentKit / x402  ✅ implemented

The agent wallet is a CDP **Server Wallet v2**, provisioned via
`CdpEvmWalletProvider` on Base Sepolia (keys in a TEE; the developer holds the
Wallet Secret). The agent pays for its own tool calls over **x402**: each
LangGraph node hits our FastAPI endpoint, gets an HTTP 402, and the x402 client
— signing with the CDP wallet via `wallet_provider.to_signer()` — submits a
gasless **EIP-3009** USDC authorization. The facilitator settles it on-chain and
returns the settlement tx hash (decoded from `x-payment-response`) for the
receipt. The final remittance uses AgentKit's `erc20_action_provider` transfer.
Every micropayment and the transfer are real, viewable Base Sepolia transactions.

### Circle USDC  ✅ implemented · Paymaster / CCTP 🛣️ roadmap

All value moves as native **Circle USDC** (6-decimal, EIP-3009), used for both
the x402 micropayments and the remittance itself. **Roadmap:** Circle Paymaster
to sponsor gas so recipients with no ETH receive funds with zero setup, and CCTP
V2 Fast Transfer for ~20-second cross-chain settlement.

### Base (L2)  ✅ implemented

Base Sepolia (`base-sepolia`) is the deployment network — USDC is native, fees
are negligible, and txs confirm in seconds. Mainnet is a one-line switch to
`base-mainnet`. Gasless recipient UX via Base's EIP-4337 / Circle Paymaster is
on the roadmap (see above).

## Setup

This project targets **Python 3.11+**. The repo uses [`uv`](https://docs.astral.sh/uv/)
(macOS system Python is often 3.9, which is too old).

```bash
git clone https://github.com/SebAustin/remesa
cd remesa
cp .env.example .env          # then fill it in — see "Configure .env" below

# with uv (recommended — pins a 3.11 interpreter automatically)
uv venv --python 3.11
uv pip install -e ".[dev]"

# or with pip on an existing 3.11+ interpreter
# pip install -e ".[dev]"
```

### Configure `.env`

| Variable | Where to get it |
|---|---|
| `CDP_API_KEY_ID`, `CDP_API_KEY_SECRET` | [portal.cdp.coinbase.com](https://portal.cdp.coinbase.com) → **Secret API Keys** |
| `CDP_WALLET_SECRET` | CDP portal → **Wallets → Security → Generate** (separate from the API key; an ECDSA key, shown once) |
| `CDP_WALLET_ADDRESS` | leave blank on first run, then pin it (below) |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) → API Keys |
| `TELEGRAM_BOT_TOKEN` | Telegram [@BotFather](https://t.me/BotFather) |
| `X402_RECEIVER_ADDRESS` | the agent's own address (printed in the next step) |

### First run: create + fund + pin the wallet

```bash
# Creates the agent wallet (first run) and prints its address + balances.
python scripts/print_wallet_address.py --faucet
```

Then in `.env`, set **both** to the printed address (the agent pays its own
fees, so it is its own x402 receiver):

```dotenv
CDP_WALLET_ADDRESS=0x...     # pins the wallet so it's reused across restarts
X402_RECEIVER_ADDRESS=0x...  # same address
```

> Without `CDP_WALLET_ADDRESS`, CDP mints a **new** wallet every run. The CDP
> faucet is rate-limited (~3 USDC/window); top up testnet USDC at
> [faucet.circle.com](https://faucet.circle.com) (Base Sepolia, 10/day).

### Run it

```bash
python main.py     # starts the Telegram bot + the x402 server
```

Then message your bot:  `send 5 to mama at 0x742d35Cc6634C0532925a3b8D4C3b4E6C8e07e01`

### Verify the install

```bash
# x402 server standalone
uvicorn services.x402_server:app --port 8402 --reload
curl http://localhost:8402/health

# run the tests (no network/keys needed — uses fakes)
pytest tests/ -v
```

### Run the full graph end-to-end (programmatically)

`build_graph` is **async** (it opens a SQLite checkpointer), so await it. Note
`build_agent_kit()` must be called **outside** the event loop — the CDP wallet
constructor uses `asyncio.run()` internally (see the sync-blocking note below).

```python
import asyncio
from langgraph.types import Command
from wallet.setup import build_agent_kit
from agent.graph import build_graph

async def run(ak):
    g = await build_graph(ak)
    cfg = {"configurable": {"thread_id": "test-001"}}
    state = {
        "thread_id": "test-001",
        "user_message": "send 5 to mama at 0x742d35Cc6634C0532925a3b8D4C3b4E6C8e07e01",
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

ak = build_agent_kit()        # build OUTSIDE asyncio.run
asyncio.run(run(ak))
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
│   ├── fx.py                 # FX quote client (sync, run via asyncio.to_thread)
│   ├── sanctions.py          # sanctions screen client (sync)
│   └── _payments.py          # x402 settlement helpers (tx hash, status checks)
├── wallet/setup.py           # AgentKit factory + faucet helper
├── telegram_bot/             # NOT "telegram" — avoids shadowing the PTB library
│   ├── bot.py
│   └── handlers.py
├── scripts/
│   └── print_wallet_address.py   # create/inspect/fund the agent wallet
├── docs/DEMO.md              # 90-second demo recording guide
├── tests/                    # pytest suite (no creds/network needed)
└── .github/workflows/ci.yml  # CI: pytest on every push
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
  - x402 buyer: `x402.clients.x402_requests(account=...)` (sync session, see the
    sync-blocking note below), fed by `wallet_provider.to_signer()`, not
    `AsyncPayingClient(wallet_provider=...)`. An x402 session pays for **one**
    request only, so a fresh single-use session is built per tool call.
  - Settlement tx hash for the receipt is decoded from the `x-payment-response`
    header via `x402.clients.decode_x_payment_response`.
  - Network is the string `"base-sepolia"`, not CAIP-2 `eip155:84532`.
  - USDC transfer uses the `ERC20ActionProvider_transfer` action with the amount
    in **whole units** (AgentKit converts decimals); invoked via
    `agent_kit.get_actions()` → `action.invoke(...)` (there is no
    `execute_action`).
  - Faucet is requested through `wallet_provider.get_client()` (CDP client);
    `CdpEvmWalletProvider` has no `request_faucet`/token-arg `get_balance`.
- **AgentKit is sync-blocking** — `CdpEvmWalletProvider`'s constructor calls
  `asyncio.run()`, and its sign/send methods call `loop.run_until_complete()`,
  so they cannot run inside a running event loop. Remesa builds the kit *before*
  `asyncio.run` and drives every blocking CDP call (USDC transfer + x402 payment
  signing) through `asyncio.to_thread`. The x402 buyer therefore uses the **sync**
  `x402.clients.x402_requests` session (not the async `x402HttpxClient`) so the
  CDP wallet stays the payer.
- **x402 / AgentKit imports** are still loaded defensively where signatures may
  drift; mismatches log a clear warning instead of crashing.

### Quick wallet check

```bash
python scripts/print_wallet_address.py          # print address + balances
python scripts/print_wallet_address.py --faucet # also request Base Sepolia funds
```

Copy the printed address into `X402_RECEIVER_ADDRESS` in `.env` — the agent pays
its own tool fees, so the x402 receiver is its own wallet.

## Roadmap

- **Near-term:** Off-ramp via Bitso API (USDC → MXN → SPEI instant transfer to any Mexican bank)
- **Mid-term:** Multi-chain support (Polygon/Arbitrum) via CCTP V2 + multi-leg routing
- **Business case:** $64.7B corridor × 0.09% fee = $58M TAM at 0.1% market share

## License

MIT — see [LICENSE](LICENSE).
