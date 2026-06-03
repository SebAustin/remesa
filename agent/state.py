"""
state.py — AgentState TypedDict for the Remesa LangGraph StateGraph.

Every node reads from and writes to this dict. LangGraph uses it as
the checkpoint schema, so field names are part of the public API.
"""
from typing import Optional, TypedDict


class Intent(TypedDict):
    action: str           # "send_usdc"
    amount_usd: float
    recipient_address: str
    recipient_name: str   # human label e.g. "mama"


class FxQuote(TypedDict):
    rate_mxn_per_usd: float
    fee_usd: float
    x402_tx_hash: str     # the micropayment hash for the quote tool call


class SanctionsResult(TypedDict):
    cleared: bool
    reason: str
    fee_usd: float        # cost of the screen ($0.05), itemized on the receipt
    x402_tx_hash: str     # the micropayment hash for the sanctions tool call


class AgentState(TypedDict):
    # Input
    thread_id: str                    # Telegram chat_id (str) used as LG thread
    user_message: str

    # Pipeline state
    intent: Optional[Intent]
    fx_quote: Optional[FxQuote]
    sanctions_result: Optional[SanctionsResult]

    # Execution
    transfer_tx_hash: Optional[str]
    receipt: Optional[dict]           # final itemized receipt sent to user

    # Control
    status: str   # "pending" | "confirmed" | "executed" | "failed" | "cancelled"
    error: Optional[str]
