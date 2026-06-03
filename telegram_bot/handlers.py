"""
telegram_bot/handlers.py — Bridge between Telegram messages and the LangGraph agent.

Handles the two-phase flow:
  1. user sends a transfer request → graph runs until the confirm interrupt
  2. user replies YES/NO → graph resumes via Command(resume=...) and finishes
"""
import structlog
from langgraph.types import Command
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

log = structlog.get_logger()

# Injected at bot startup by build_app().
_graph = None


def set_graph(graph) -> None:
    global _graph
    _graph = graph


AWAITING_CONFIRM = 1  # ConversationHandler state


def _extract_interrupt_message(result: dict) -> str | None:
    """Pull the confirmation prompt out of a graph interrupt payload."""
    interrupts = result.get("__interrupt__")
    if not interrupts:
        return None
    first = interrupts[0]
    value = getattr(first, "value", first)
    if isinstance(value, dict):
        return value.get("message")
    return str(value)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: user sends a new transfer request."""
    chat_id = str(update.effective_chat.id)
    text = update.message.text.strip()

    await update.message.reply_text("🔍 Analyzing your request...")

    config = {"configurable": {"thread_id": chat_id}}
    initial_state = {
        "thread_id": chat_id,
        "user_message": text,
        "status": "pending",
        "intent": None,
        "fx_quote": None,
        "sanctions_result": None,
        "transfer_tx_hash": None,
        "receipt": None,
        "error": None,
    }

    try:
        result = await _graph.ainvoke(initial_state, config)

        if result.get("status") in ("failed", "cancelled"):
            await update.message.reply_text(
                f"❌ {result.get('error', 'Unknown error')}"
            )
            return ConversationHandler.END

        confirm_msg = _extract_interrupt_message(result)
        if confirm_msg is None:
            # No interrupt and not failed — unexpected, but surface a receipt if any.
            if result.get("receipt"):
                await update.message.reply_text(
                    result["receipt"]["telegram_msg"],
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                )
                return ConversationHandler.END
            await update.message.reply_text("⚠️ Unexpected state. Check logs.")
            return ConversationHandler.END

        await update.message.reply_text(confirm_msg, parse_mode="Markdown")
        return AWAITING_CONFIRM

    except Exception as exc:  # noqa: BLE001
        log.error("Graph invoke failed", error=str(exc))
        await update.message.reply_text(f"❌ System error: {exc}")
        return ConversationHandler.END


async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Resume the graph after the user replies YES or NO."""
    chat_id = str(update.effective_chat.id)
    reply = update.message.text.strip().upper()
    config = {"configurable": {"thread_id": chat_id}}

    try:
        result = await _graph.ainvoke(Command(resume=reply), config)

        if result.get("status") == "cancelled":
            await update.message.reply_text("↩️ Transfer cancelled.")
        elif result.get("status") == "failed":
            await update.message.reply_text(
                f"❌ {result.get('error', 'Transfer failed')}"
            )
        elif result.get("receipt"):
            await update.message.reply_text(
                result["receipt"]["telegram_msg"],
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
        else:
            await update.message.reply_text("⚠️ Unexpected state. Check logs.")
    except Exception as exc:  # noqa: BLE001
        log.error("Graph resume failed", error=str(exc))
        await update.message.reply_text(f"❌ Resume error: {exc}")

    return ConversationHandler.END


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 *Welcome to Remesa!*\n\n"
        "Send money to LATAM via USDC on Base.\n\n"
        "Example:\n"
        "`send 10 to mama at 0x742d35Cc6634C0532925a3b8D4C3b4E6C8e07e01`\n\n"
        "Your AI agent pays for its own tools via x402 micropayments. "
        "Every fee is onchain and auditable.",
        parse_mode="Markdown",
    )
