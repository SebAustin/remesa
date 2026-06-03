"""
Remesa Telegram front-end.

Named ``telegram_bot`` (NOT ``telegram``) on purpose: a local package named
``telegram`` would shadow the ``python-telegram-bot`` library, breaking every
``from telegram import ...`` import in this package.
"""
