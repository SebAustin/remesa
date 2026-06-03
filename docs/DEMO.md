# Remesa — Demo Recording Guide

A tight 90-second demo that lands the wow: an AI agent that sends USDC home and
**pays for its own tools** with real on-chain x402 micropayments.

---

## 0. Pre-flight (do this before hitting record)

```bash
# 1. Make sure the agent has USDC (each run burns $0.06 fees + the amount sent)
python scripts/print_wallet_address.py        # check USDC balance
#    Need more? Circle faucet gives 10 USDC/day on Base Sepolia:
#    https://faucet.circle.com  → select "Base Sepolia", paste the agent address

# 2. Start the agent (bot + x402 server)
python main.py
#    Wait for: "Telegram bot polling; x402 server starting"
```

Checklist:
- [ ] Agent wallet has ≥ $5.10 USDC (so a `$5` send + `$0.06` fees clears)
- [ ] `ACTIVE_NETWORK = base-sepolia` (🧪 testnet — no real funds)
- [ ] `main.py` running, no errors in the log
- [ ] Telegram open to your bot; send `/start` once to clear the screen
- [ ] (optional) LangSmith trace view open: https://smith.langchain.com
- [ ] (optional) BaseScan open: https://sepolia.basescan.org

### Window layout (for screen capture)
```
┌─────────────────────────┬───────────────────────────┐
│  Telegram chat (focus)  │  terminal: main.py logs    │
│                         ├───────────────────────────┤
│                         │  browser: BaseScan tab     │
└─────────────────────────┴───────────────────────────┘
```
Record with QuickTime (⌘⇧5), Loom, or OBS. Keep the Telegram chat the hero.

---

## 1. Script (≈90 seconds)

**0:00–0:10 — The problem (talking head or title card)**
> "Forty-five million Americans send sixty-four *billion* dollars a year to
> Mexico. Western Union takes about five percent — and it's slow."

**0:10–0:22 — The pitch (show the Telegram chat, empty)**
> "Remesa is an AI agent you text. It sends USDC on Base in seconds — and here's
> the twist: it pays for its *own* tools with x402 micropayments."

**0:22–0:50 — Live run (type in Telegram)**
Type and send:
```
send 5 to mama at 0x742d35Cc6634C0532925a3b8D4C3b4E6C8e07e01
```
> "It parses my request, pays one cent for a live FX quote, five cents for a
> sanctions screen — then asks me to confirm before sending anything."

When the confirmation appears, reply:
```
YES
```

**0:50–1:12 — The receipt (the wow)**
Point at the receipt as it lands:
> "Done. And look — an itemized receipt. The agent paid for its FX quote and its
> sanctions check itself, each a real transaction. Total fee: six cents, flat.
> On a typical two-hundred-dollar remittance that's three *hundredths* of a
> percent — versus Western Union's $9.90."

**1:12–1:25 — Prove it's real (click BaseScan)**
Click the **View transfer on BaseScan** link; let the confirmed tx load.
> "Every one of these is a real on-chain transaction — the transfer, and the two
> micropayments the agent made. Auditable, onchain, settled in seconds."

**1:25–1:30 — Close**
> "Remesa. Built with Coinbase AgentKit, x402, Circle USDC, and LangGraph."

---

## 2. The three on-chain proofs to show
From the receipt, open each tx on https://sepolia.basescan.org/tx/<hash> :
1. **The USDC transfer** (the `View transfer on BaseScan` link)
2. **FX Quote micropayment** — $0.01 USDC
3. **Sanctions Screen micropayment** — $0.05 USDC

Tip: the micropayments are self-payments (agent → agent) on testnet — that's
expected and still produces real, viewable transactions.

---

## 3. Talking points if a judge asks
- **Human-in-the-loop:** the graph hard-stops at `confirm_with_user` — it never
  broadcasts without a `YES`. Plus a `MAX_TRANSFER_USD` cap.
- **Why x402 matters:** the agent is a real economic actor — it earns/pays for
  services autonomously, with every cent auditable onchain. No prepaid API keys.
- **Path to production:** swap the mock FX/sanctions for live providers, add a
  Bitso/SPEI off-ramp (USDC→MXN to any Mexican bank), and flip the network to
  `base-mainnet` (one config line) with Circle Paymaster for gasless recipients.
