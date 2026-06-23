import os
import re
import json
import logging
from datetime import datetime
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import gspread
from google.oauth2.service_account import Credentials

# ── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Health server (Render Free Web Service requires an HTTP port) ────────
health_app = Flask(__name__)

@health_app.get('/')
def home():
    return 'Bot is running', 200

@health_app.get('/health')
def health():
    return 'OK', 200

PORT = int(os.environ.get('PORT', 10000))

def run_health_server():
    health_app.run(host='0.0.0.0', port=PORT, use_reloader=False)

# ── Config ───────────────────────────────────────────────────────────────
BOT_TOKEN        = os.environ["TELEGRAM_BOT_TOKEN"]
SHEET_ID         = os.environ["GOOGLE_SHEET_ID"]
CREDS_FILE       = os.environ.get("GOOGLE_CREDS_FILE", "credentials.json")
ALLOWED_USER_IDS = set(os.environ.get("ALLOWED_USER_IDS", "").split(","))

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CATEGORIES = {
    "Transport":     ["uber", "ola", "auto", "bike", "taxi", "cab", "rapido", "rickshaw"],
    "Metro":         ["metro", "dmrc", "card recharge", "metro recharge"],
    "Food":          ["food", "lunch", "dinner", "breakfast", "chai", "tea", "coffee",
                      "juice", "snack", "biryani", "pizza", "restaurant", "dhaba",
                      "swiggy", "zomato", "thali", "roti"],
    "Bills":         ["bill", "electricity", "light bill", "water bill", "recharge",
                      "internet", "wifi", "broadband", "gas"],
    "Home":          ["repair", "maintenance", "plumber", "electrician", "carpenter",
                      "paint", "home", "furniture", "rent"],
    "Entertainment": ["movie", "cinema", "pvr", "inox", "netflix", "hotstar",
                      "concert", "show", "game"],
    "Shopping":      ["shopping", "clothes", "shirt", "shoes", "amazon", "flipkart",
                      "myntra", "meesho", "kirana", "grocery"],
    "Health":        ["medicine", "doctor", "pharmacy", "hospital", "clinic", "chemist",
                      "medical", "test"],
    "Other":         [],
}

ACCOUNTS = ["bob", "indusind", "cash", "upi", "gpay", "phonepe", "paytm", "other"]

ACCOUNT_DISPLAY = {
    "bob": "BOB", "indusind": "IndusInd", "cash": "Cash", "upi": "UPI",
    "gpay": "GPay", "phonepe": "PhonePe", "paytm": "Paytm", "other": "Other",
}

# ── Google Sheets ────────────────────────────────────────────────────────
creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
gc    = gspread.authorize(creds)
sheet = gc.open_by_key(SHEET_ID).sheet1

# ── Parser ───────────────────────────────────────────────────────────────
def detect_category(text):
    lower = text.lower()
    for cat, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw in lower:
                return cat
    return "Other"

def parse_expense(text):
    text = text.strip()
    match = re.search(r'(\d+(?:\.\d+)?)', text)
    if not match:
        return None
    amount = match.group(1)
    rest = (text[:match.start()] + " " + text[match.end():]).strip()
    words = rest.split()
    account = "Cash"
    desc_parts = []
    for w in words:
        if w.lower() in ACCOUNTS:
            account = ACCOUNT_DISPLAY.get(w.lower(), w.title())
        else:
            desc_parts.append(w)
    desc = " ".join(desc_parts).strip()
    if not desc:
        return None
    return {
        "description": desc.title(),
        "category":    detect_category(desc),
        "amount":      amount,
        "account":     account,
    }

# ── Auth ─────────────────────────────────────────────────────────────────
def is_allowed(uid):
    return str(uid) in ALLOWED_USER_IDS

# ── Handlers ─────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    today_str = datetime.now().strftime("%d-%m-%Y")
    rows = sheet.get_all_values()
    total = 0
    for r in rows:
        if r and r[0] == today_str:
            try:
                total += float(r[3])
            except (ValueError, IndexError):
                pass
    await update.message.reply_text(f"Today's total: ₹{total:.0f}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    result = parse_expense(update.message.text)
    if not result:
        await update.message.reply_text("Couldn't parse that. Try: chai 20 cash")
        return
    today_str = datetime.now().strftime("%d-%m-%Y")
    row = [today_str, result["description"], result["category"],
           result["amount"], result["account"]]
    try:
        sheet.append_row(row, value_input_option="USER_ENTERED")
        await update.message.reply_text(
            f"✓ Logged!\n"
            f"  {today_str}  |  {result['description']}\n"
            f"  {result['category']}  ·  ₹{result['amount']}  ·  {result['account']}"
        )
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        await update.message.reply_text("Error saving to sheet. Try again.")

# ── Main ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Health server in daemon thread — keeps Render Free Web Service alive
    Thread(target=run_health_server, daemon=True).start()
    logger.info("Health server started on port %s", PORT)

    # Build and run Telegram bot with polling
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot polling started")
    app.run_polling(drop_pending_updates=True)