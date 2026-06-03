"""
telegram_bot/bot.py — Telegram ApplicationBuilder setup with ConversationHandler.
"""
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN
from telegram_bot.handlers import (
    AWAITING_CONFIRM,
    handle_confirmation,
    handle_message,
    handle_start,
    set_graph,
)


def build_app(graph) -> Application:
    set_graph(graph)
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        ],
        states={
            AWAITING_CONFIRM: [
                MessageHandler(
                    filters.Regex(r"^(?i:yes|no)$"), handle_confirmation
                )
            ]
        },
        fallbacks=[CommandHandler("start", handle_start)],
    )

    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(conv_handler)
    return app
