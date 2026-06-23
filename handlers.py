"""Telegram bot handlers — /start, /today, and expense message handler."""

import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from config import ALLOWED_USER_IDS
from parser import parse_expense
from sheets import sheet

logger = logging.getLogger(__name__)


def is_allowed(uid: int) -> bool:
    """Check if user ID is in the allowed set."""
    return str(uid) in ALLOWED_USER_IDS


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update.effective_user.id):
        return
    await update.message.reply_text(
        "Hey! Send expenses like:\n"
        "  chai 20 cash\n"
        "  uber 137 bob\n"
        "  lunch 80\n\n"
        "Commands:\n"
        "  /today — today's total"
    )


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update.effective_user.id):
        return
    today_str = datetime.now().strftime("%d-%m-%Y")
    rows = sheet.get_all_values()
    total = 0
    for r in rows:
        if r and r[0].startswith(today_str):
            try:
                total += float(r[3])
            except (ValueError, IndexError):
                pass
    await update.message.reply_text(f"Today's total: ₹{total:.0f}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update.effective_user.id):
        return
    result = parse_expense(update.message.text)
    if not result:
        await update.message.reply_text("Couldn't parse that. Try: chai 20 cash")
        return
    today_str = datetime.now().strftime("%d-%m-%Y")
    timestamp_str = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    row = [timestamp_str, result["description"], result["category"],
           result["amount"], result["account"]]
    try:
        sheet.append_row(row, value_input_option="USER_ENTERED")
        await update.message.reply_text(
            f"✓ Logged!\n"
            f"  {timestamp_str}  |  {result['description']}\n"
            f"  {result['category']}  ·  ₹{result['amount']}  ·  {result['account']}"
        )
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        await update.message.reply_text("Error saving to sheet. Try again.")
