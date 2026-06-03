# Remesa — DoraHacks BUIDL Submission

> Paste-ready copy for the DoraHacks BUIDL page. Swap in the demo-video URL and
> the live links at the bottom before submitting.

---

## Name
**Remesa** — Your AI agent that sends money home, and pays its own way.

## One-liner
A Telegram AI agent that sends USDC on Base in seconds — and pays for its own FX
quote and sanctions screen with real on-chain x402 micropayments, returning an
itemized receipt that proves every fee onchain.

## Tracks
- 🟦 **Coinbase CDP / AgentKit / x402**
- 🟢 **Circle USDC**
- 🔵 **Base (L2)**

---

## The Problem
45 million Americans send **$64.7B/year to Mexico**. Western Union charges ~5%
(**$9.90 on a $200 transfer**), settlement takes 3–5 days, and half of recipients
are unbanked. Remittances are the clearest real-world case for stablecoins — but
the UX is still too hard for non-crypto users, and "AI agents that transact" are
usually demos with no real money movement.

## The Solution
Remesa is an autonomous remittance agent you simply **text on Telegram**:

1. **Parse** — Claude turns "send $5 to mama at 0x…" into a structured intent.
2. **Quote FX** — the agent calls a priced API and **pays $0.01 USDC via x402**.
3. **Screen** — it runs an OFAC sanctions check and **pays $0.05 USDC via x402**.
4. **Confirm** — the graph hard-stops for human YES/NO before any broadcast.
5. **Send** — executes a native USDC transfer on Base.
6. **Receipt** — returns an itemized receipt with **every fee as a real onchain
   tx**, plus BaseScan links.

The agent is a real economic actor: it **earns and spends autonomously**, and
every cent is auditable onchain — no prepaid API keys, no hidden middlemen.

## The Wow Moment
The receipt makes "agentic commerce" concrete for any non-technical judge — the
AI literally paid for its own tools:

```
✅ Remesa enviada / Remittance sent
📤 Sent: $5.00 USDC   →   0x742d…7e01   ≈ 86 MXN

🤖 Agent micropayments (your AI paid for its own tools):
  • FX Quote API:     $0.01 → tx 0xbf0e…34e2
  • Sanctions Screen: $0.05 → tx 0xeb20…1259

💰 Remesa fee: $0.06 flat (any amount)
📊 On a $200 remittance: Remesa $0.06 (0.03%) vs Western Union ~$9.90 → save $9.84
```

---

## How Each Sponsor Is Used

### 🟦 Coinbase CDP / AgentKit / x402 — *fully implemented*
- The agent wallet is a **CDP Server Wallet v2** via AgentKit's
  `CdpEvmWalletProvider` (keys in a TEE; we hold the Wallet Secret).
- **x402 is the heart of the project**: every tool call is a paid HTTP request.
  Our FastAPI endpoints are gated with `x402.fastapi.middleware.require_payment`;
  the agent (buyer) pays by signing an **EIP-3009 USDC authorization** with the
  CDP wallet (`wallet_provider.to_signer()`), the **x402 facilitator** settles it
  on Base, and we decode the settlement tx hash from the `X-PAYMENT-RESPONSE`
  header for the receipt.
- The remittance itself uses AgentKit's **`erc20_action_provider`** transfer.
- Result: **3 real on-chain transactions per run** (2 micropayments + 1 transfer).

### 🟢 Circle USDC — *fully implemented* · Paymaster / CCTP — *roadmap*
- All value moves as native **Circle USDC** (6-decimal, EIP-3009) — both the x402
  micropayments and the remittance.
- **Roadmap:** Circle **Paymaster** to sponsor gas so recipients with no ETH
  receive funds with zero setup; **CCTP V2 Fast Transfer** for ~20s cross-chain
  settlement and multi-corridor routing.

### 🔵 Base (L2) — *fully implemented*
- Deployed on **Base Sepolia** (`base-sepolia`): USDC is native, fees are
  negligible, txs confirm in seconds. Mainnet is a one-line switch to
  `base-mainnet`.

---

## Architecture (high level)
```
User → Telegram → LangGraph StateGraph (durable checkpoint)
   parse_intent(Claude) → quote_fx ─x402 $0.01→ FastAPI ─► x402 Facilitator ─► Base Sepolia
                        → check_sanctions ─x402 $0.05→ FastAPI ─► (same)
                        → confirm_with_user [⏸ human YES/NO]
                        → execute_transfer ─AgentKit erc20→ Base Sepolia (USDC)
                        → generate_receipt → itemized receipt + BaseScan links
```
Full diagrams (system + x402 sequence) in the repo README.

## Tech Stack
LangGraph · Coinbase AgentKit (CDP Server Wallet v2) · x402 · Circle USDC · Base
Sepolia · python-telegram-bot · FastAPI · Claude Sonnet 4.6 · LangSmith.

## Safety / Trust
- **Human-in-the-loop**: the graph never broadcasts without an explicit `YES`.
- **Hard transfer cap** (`MAX_TRANSFER_USD`) and a per-call x402 spend cap.
- **Sanctions screen** blocks OFAC-listed recipients before any transfer.
- Conditional routing short-circuits to END on any failure/cancellation.

## Status
**Working end-to-end on Base Sepolia** — real USDC transfer + two real x402
micropayments per run, human confirmation, itemized onchain receipt. CI-tested.

## Roadmap
- Bitso/SPEI **off-ramp** (USDC → MXN to any Mexican bank account)
- Circle **Paymaster** (gasless recipients) + **CCTP V2** multi-corridor routing
- Mainnet launch · recipient SMS/WhatsApp notifications · more tool integrations
- **Business case:** $64.7B corridor × 0.09% = ~$58M TAM at 0.1% share

## Links
- **GitHub:** https://github.com/SebAustin/remesa
- **Demo video:** _<add URL>_
- **Network:** Base Sepolia (testnet) — example txs on https://sepolia.basescan.org
