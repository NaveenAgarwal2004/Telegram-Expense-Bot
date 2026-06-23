"""Telegram Expense Bot — main entry point."""

import logging
from threading import Thread

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from config import BOT_TOKEN, PORT
from health import run_health_server
from handlers import cmd_start, cmd_today, cmd_last, handle_message

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Health server in daemon thread — keeps Render Free Web Service alive
    Thread(target=run_health_server, daemon=True).start()
    logger.info("Health server starting on port %s", PORT)

    # Build and run Telegram bot with polling
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("last", cmd_last))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot polling started")
    app.run_polling(drop_pending_updates=True)