<p align="center">
  <img src="brand/logo-lockup.png" alt="Remesa — AI remittances on Base" width="560">
</p>

# Remesa 🌎 — Your AI agent that sends money home, and pays its own way

> **Vision:** Sending money home should be as simple as a text — and honest by
> design. Remesa is an autonomous AI agent that moves USDC across borders in
> seconds and pays for its own tools onchain, replacing 5% remittance fees with
> auditable cents.

**Remesa is an autonomous AI remittance agent you simply *text* on Telegram.**
Say *"send $5 to mama at 0x…"* and the agent parses your intent with Claude,
fetches a live FX rate, runs an OFAC sanctions screen, asks you to confirm, and
sends **USDC on Base** in seconds — then hands back an itemized receipt with
**on-chain proof of every step**. The twist that makes *agentic commerce* real:
the agent **pays for its own tools**, settling micropayments from its own wallet
as it works.

---

## 💡 The Problem

- **45M Americans send $64.7B/year to Mexico** — the clearest real-world use case for stablecoins.
- **Western Union takes ~5%** (≈ **$9.90 on a $200 transfer**) and settles in **3–5 days**.
- Half of recipients are **unbanked**, and most "AI agents that transact" are demos that never move real money.

## ✨ What Remesa Does

1. **Parse** — Claude turns natural language into a structured transfer intent.
2. **Quote FX** — calls a priced API and **pays `$0.01` USDC via x402**.
3. **Screen** — runs a sanctions check and **pays `$0.05` USDC via x402**.
4. **Confirm** — the LangGraph state machine **hard-stops for human YES/NO** before any broadcast.
5. **Send** — executes a native **USDC transfer on Base**.
6. **Receipt** — returns an itemized receipt where **every fee is a real on-chain transaction**, with BaseScan links.

## 🤖 The Wow Moment — the AI paid for its own tools

```
✅ Remesa enviada / Remittance sent
📤 Sent: $5.00 USDC  →  0x742d…7e01  ≈ 86 MXN

🤖 Agent micropayments (your AI paid for its own tools):
  • FX Quote API:     $0.01 → tx 0xbf0e…34e2
  • Sanctions Screen: $0.05 → tx 0xeb20…1259

💰 Remesa fee: $0.06 flat (any amount)
📊 On a $200 remittance: Remesa $0.06 (0.03%) vs Western Union ~$9.90 → save $9.84
```

Remesa's fee is **flat — $0.06 regardless of amount**. The agent is a genuine
economic actor: it **earns and spends autonomously**, and every cent is auditable
onchain — no prepaid API keys, no hidden middlemen.

## 🏆 How We Used Each Sponsor

| Track | What we built |
|---|---|
| 🟦 **Coinbase CDP / AgentKit / x402** · *implemented* | Agent wallet is a **CDP Server Wallet v2** via AgentKit. **x402 is the core**: endpoints gated with `require_payment`; the agent pays by signing **EIP-3009** USDC authorizations with `wallet_provider.to_signer()`; the **facilitator** settles on Base; we decode the settlement tx hash from the `X-PAYMENT-RESPONSE` header for the receipt. The transfer uses `erc20_action_provider`. → **3 real on-chain txs per run.** |
| 🟢 **Circle USDC** · *implemented* (Paymaster / CCTP · *roadmap*) | All value moves as native **Circle USDC** (6-decimal, EIP-3009) — both the x402 micropayments and the remittance. Roadmap: **Circle Paymaster** for gasless recipients, **CCTP V2** for ~20s cross-chain settlement. |
| 🔵 **Base (L2)** · *implemented* | Deployed on **Base Sepolia** — native USDC, negligible fees, seconds to confirm. Mainnet is a one-line switch to `base-mainnet`. |

## 🧭 Architecture

```
User → Telegram → LangGraph StateGraph (durable checkpoint)
   parse_intent (Claude)
   → quote_fx ─────────x402 $0.01──► FastAPI ─► x402 Facilitator ─► Base Sepolia
   → check_sanctions ──x402 $0.05──► FastAPI ─► (same)
   → confirm_with_user [⏸ human YES / NO]
   → execute_transfer ─AgentKit erc20──► Base Sepolia (USDC)
   → generate_receipt → itemized receipt + BaseScan links
```

Failure or cancellation at any pre-execution node short-circuits straight to
`END`, so the agent **never broadcasts an unconfirmed or sanctioned transfer**.
*(Rendered system + x402 sequence diagrams are in the [repo README](https://github.com/SebAustin/remesa#architecture).)*

## 🛠️ Tech Stack

**LangGraph** (stateful agent + human-in-the-loop interrupts) · **Coinbase
AgentKit** (CDP Server Wallet v2) · **x402** · **Circle USDC** · **Base Sepolia** ·
**python-telegram-bot** · **FastAPI** · **Claude Sonnet 4.6** · **LangSmith**.

## 🔒 Safety by Design

- **Human-in-the-loop:** never broadcasts without an explicit `YES`.
- **Hard transfer cap** (`MAX_TRANSFER_USD`) + per-call x402 spend cap.
- **Sanctions screen** blocks OFAC-listed recipients before any transfer.
- Conditional routing short-circuits to `END` on any failure or cancellation.

## ✅ Status & Roadmap

**Working end-to-end on Base Sepolia** — a real USDC transfer plus two real x402
micropayments per run, human confirmation, and an itemized onchain receipt.
CI-tested.

- **Near-term:** Bitso/SPEI **off-ramp** (USDC → MXN to any Mexican bank account)
- **Mid-term:** Circle **Paymaster** (gasless recipients) + **CCTP V2** multi-corridor routing
- **Then:** mainnet launch · recipient SMS/WhatsApp notifications · more tool integrations
- **Business case:** $64.7B corridor × 0.09% ≈ **$58M TAM** at 0.1% market share

## 👤 Team

**Remesa** is a solo build.

| | |
|---|---|
| **Name** | _<your full name>_ |
| **Role** | Founder & Sole Engineer — Python / LangGraph / full-stack |
| **GitHub** | [@SebAustin](https://github.com/SebAustin) |
| **Contact** | _<email / X / Telegram>_ |

Built solo in a 48-hour sprint: the LangGraph agent, the CDP wallet + x402
payment layer, the FastAPI priced services, the Telegram UX, tests, and CI.

## 🔗 Links

- **GitHub:** https://github.com/SebAustin/remesa
- **Demo video:** https://youtu.be/Zulf-D8qEJs
- **Network:** Base Sepolia (testnet) — example txs on https://sepolia.basescan.org

---

*Tracks: **Payments** (primary) + **AI** · Sponsor bounties: **Coinbase (x402/AgentKit)**, **Circle (USDC)**, **Base**.*
