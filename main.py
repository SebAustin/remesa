"""
main.py — Entry point.

Starts the x402 FastAPI server and the Telegram bot concurrently in a single
event loop.

NOTE: ``Application.run_polling()`` cannot be used here — it creates and owns its
own event loop, so it can't be awaited alongside uvicorn inside one loop. Instead
we drive the python-telegram-bot lifecycle manually (initialize → start →
updater.start_polling) and let uvicorn's ``serve()`` own the foreground until
shutdown, then tear everything down cleanly.
"""
import asyncio

import structlog
import uvicorn

import config
from agent.graph import build_graph
from services.x402_server import app as x402_app
from telegram_bot.bot import build_app
from wallet.setup import build_agent_kit, ensure_funded

log = structlog.get_logger()


async def main() -> None:
    log.info("Remesa starting up...")
    config.require_runtime_secrets()

    # 1. Init wallet and AgentKit
    agent_kit = build_agent_kit()
    await ensure_funded(agent_kit)

    # 2. Build LangGraph (durable SQLite checkpointer)
    graph = await build_graph(agent_kit)

    # 3. Build Telegram app
    tg_app = build_app(graph)

    # 4. Configure the x402 server
    x402_config = uvicorn.Config(
        x402_app,
        host="0.0.0.0",
        port=config.X402_SERVER_PORT,
        log_level="warning",
    )
    x402_server = uvicorn.Server(x402_config)

    # 5. Run both: start the bot in the background, let uvicorn hold the foreground.
    await tg_app.initialize()
    await tg_app.start()
    await tg_app.updater.start_polling()
    log.info("Telegram bot polling; x402 server starting", port=config.X402_SERVER_PORT)

    try:
        await x402_server.serve()  # blocks until SIGINT/SIGTERM
    finally:
        log.info("Shutting down...")
        await tg_app.updater.stop()
        await tg_app.stop()
        await tg_app.shutdown()
        aclose = getattr(graph, "aclose", None)
        if aclose is not None:
            await aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Remesa stopped.")
