"""Telegram bot handlers — /start, /today, and expense message handler."""

import logging
import time
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from config import ALLOWED_USER_IDS
from parser import parse_expense
from sheets import sheet

logger = logging.getLogger(__name__)

_recent_updates: dict[int, float] = {}
_recent_expenses: dict[tuple, float] = {}

CATEGORY_EMOJIS = {
    "Food": "🍔",
    "Transport": "🚕",
    "Metro": "🚇",
    "Health": "💊",
    "Bills": "💡",
    "Home": "🏠",
    "Entertainment": "🎬",
    "Shopping": "🛍️",
    "Other": "🏷️"
}

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
    
    totals_by_cat = {}
    total = 0.0
    count = 0
    
    for r in rows:
        if r and len(r) >= 4 and r[0].startswith(today_str):
            try:
                amt = float(r[3])
                cat = r[2]
                totals_by_cat[cat] = totals_by_cat.get(cat, 0.0) + amt
                total += amt
                count += 1
            except (ValueError, IndexError):
                pass

    if count == 0:
        await update.message.reply_text("No expenses found.")
        return

    lines = ["📅 Today\n"]
    for cat, amt in totals_by_cat.items():
        emoji = CATEGORY_EMOJIS.get(cat, "🏷️")
        lines.append(f"{emoji} {cat.ljust(13)} ₹{amt:.0f}")
        
    lines.append("\n────────────────\n")
    lines.append(f"💰 Total         ₹{total:.0f}")
    lines.append(f"📝 Transactions  {count}")
    
    await update.message.reply_text("\n".join(lines))


async def cmd_last(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update.effective_user.id):
        return
    rows = sheet.get_all_values()
    
    # Exclude header row if present
    if rows and len(rows[0]) >= 4 and rows[0][3] == "Amount":
        rows = rows[1:]
        
    if not rows:
        await update.message.reply_text("No expenses found.")
        return
        
    latest = rows[-5:]
    latest.reverse()
    
    lines = [f"🕒 Last {len(latest)} Expenses\n"]
    for r in latest:
        if len(r) >= 5:
            date_str, desc, cat, amt, acc = r[0], r[1], r[2], r[3], r[4]
            emoji = CATEGORY_EMOJIS.get(cat, "🏷️")
            lines.append(f"{emoji} {desc.title()}\n₹{amt} • {acc}\n")
            
    await update.message.reply_text("\n".join(lines).strip())


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update.effective_user.id):
        return
    result = parse_expense(update.message.text)
    if not result:
        await update.message.reply_text("Couldn't parse that. Try: chai 20 cash")
        return

    now = time.time()
    
    if update.update_id in _recent_updates:
        if now - _recent_updates[update.update_id] <= 5.0:
            await update.message.reply_text("⚠️ Duplicate expense ignored.")
            return

    dup_key = (
        update.effective_user.id,
        result["description"].lower(),
        result["amount"],
        result["account"]
    )

    if dup_key in _recent_expenses:
        if now - _recent_expenses[dup_key] <= 5.0:
            await update.message.reply_text("⚠️ Duplicate expense ignored.")
            return

    _recent_updates[update.update_id] = now
    _recent_expenses[dup_key] = now

    # Cleanup memory only when it grows beyond 100
    if len(_recent_expenses) > 100:
        for k in list(_recent_expenses.keys()):
            if now - _recent_expenses[k] > 10.0:
                del _recent_expenses[k]
                
    if len(_recent_updates) > 100:
        for k in list(_recent_updates.keys()):
            if now - _recent_updates[k] > 10.0:
                del _recent_updates[k]

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
