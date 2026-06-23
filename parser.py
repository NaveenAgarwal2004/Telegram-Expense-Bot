"""Expense text parser — extracts description, amount, category, account."""

import re

from config import CATEGORIES, ACCOUNT_DISPLAY


def detect_category(text: str) -> str:
    """Match text against category keywords. Returns first match or 'Other'."""
    lower = text.lower()
    for cat, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw in lower:
                return cat
    return "Other"


def parse_expense(text: str) -> dict[str, str] | None:
    """Parse 'description amount [account]' into structured expense dict.

    Returns None if no amount found or description is empty.
    """
    text = text.strip()
    words = text.split()
    if not words:
        return None

    amount = None
    amount_idx = -1
    
    # 1. Find the amount: first standalone number
    for i, w in enumerate(words):
        if re.match(r'^\d+(?:\.\d+)?$', w):
            amount = w
            amount_idx = i
            break

    if amount is None:
        return None

    # 2. Find the account: last standalone account keyword
    account = "Cash"
    account_idx = -1
    account_candidates = []
    
    for i, w in enumerate(words):
        if i == amount_idx:
            continue
        clean_w = w.lower()
        if clean_w in ACCOUNT_DISPLAY:
            account_candidates.append((i, clean_w))
            
    if account_candidates:
        account_idx, acc_kw = account_candidates[-1]
        account = ACCOUNT_DISPLAY[acc_kw]

    # 3. Build description from remaining words
    desc_parts: list[str] = []
    for i, w in enumerate(words):
        if i == amount_idx:
            continue
        if i == account_idx:
            continue
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
