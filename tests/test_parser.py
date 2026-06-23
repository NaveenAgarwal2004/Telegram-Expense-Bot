"""
Tests for parser.py — detect_category and parse_expense.

All cases are derived from the documented examples in SETUP.md.
No mocks required; parser is pure Python with no I/O.
"""

import pytest
from parser import detect_category, parse_expense


# ── detect_category ───────────────────────────────────────────────────────

class TestDetectCategory:
    def test_food_lunch(self):
        assert detect_category("lunch") == "Food"

    def test_food_chai(self):
        assert detect_category("chai") == "Food"

    def test_transport_uber(self):
        assert detect_category("uber") == "Transport"

    def test_metro(self):
        assert detect_category("metro") == "Metro"

    def test_health_medicine(self):
        assert detect_category("medicine") == "Health"

    def test_bills_light_bill(self):
        assert detect_category("light bill") == "Bills"

    def test_home_repair(self):
        assert detect_category("repair") == "Home"

    def test_entertainment_netflix(self):
        assert detect_category("netflix") == "Entertainment"

    def test_shopping_amazon(self):
        assert detect_category("amazon") == "Shopping"

    def test_unknown_returns_other(self):
        assert detect_category("something random xyz") == "Other"

    def test_case_insensitive(self):
        # detect_category lowercases internally
        assert detect_category("UBER") == "Transport"

    def test_keyword_embedded_in_phrase(self):
        # "light bill" keyword should match inside a phrase
        assert detect_category("paid the light bill today") == "Bills"


# ── parse_expense ─────────────────────────────────────────────────────────

class TestParseExpense:
    """Exact examples from SETUP.md."""

    def test_chai_20_cash(self):
        result = parse_expense("chai 20 cash")
        assert result == {
            "description": "Chai",
            "category":    "Food",
            "amount":      "20",
            "account":     "Cash",
        }

    def test_uber_137_bob(self):
        result = parse_expense("uber 137 bob")
        assert result == {
            "description": "Uber",
            "category":    "Transport",
            "amount":      "137",
            "account":     "BOB",
        }

    def test_metro_25_indusind(self):
        result = parse_expense("metro 25 indusind")
        assert result == {
            "description": "Metro",
            "category":    "Metro",
            "amount":      "25",
            "account":     "IndusInd",
        }

    def test_medicine_250_upi(self):
        result = parse_expense("medicine 250 upi")
        assert result == {
            "description": "Medicine",
            "category":    "Health",
            "amount":      "250",
            "account":     "UPI",
        }

    def test_light_bill_636_bob(self):
        result = parse_expense("light bill 636 bob")
        assert result == {
            "description": "Light Bill",
            "category":    "Bills",
            "amount":      "636",
            "account":     "BOB",
        }

    def test_repair_500_cash(self):
        result = parse_expense("repair 500 cash")
        assert result == {
            "description": "Repair",
            "category":    "Home",
            "amount":      "500",
            "account":     "Cash",
        }

    def test_no_account_defaults_to_cash(self):
        """'chai 20' — no account keyword → Cash by default."""
        result = parse_expense("chai 20")
        assert result is not None
        assert result["account"] == "Cash"
        assert result["amount"]  == "20"

    def test_decimal_amount(self):
        result = parse_expense("coffee 35.50 gpay")
        assert result is not None
        assert result["amount"]  == "35.50"
        assert result["account"] == "GPay"

    def test_no_amount_returns_none(self):
        assert parse_expense("just some text") is None

    def test_only_amount_returns_none(self):
        """Amount with no description should return None."""
        assert parse_expense("500") is None

    def test_only_amount_and_account_returns_none(self):
        """'500 cash' — no description after stripping account → None."""
        assert parse_expense("500 cash") is None

    def test_leading_trailing_whitespace(self):
        result = parse_expense("  lunch 80  ")
        assert result is not None
        assert result["description"] == "Lunch"

    def test_description_is_title_cased(self):
        result = parse_expense("light bill 200")
        assert result is not None
        assert result["description"] == "Light Bill"

    def test_all_known_accounts(self):
        accounts = {
            "bob": "BOB", "indusind": "IndusInd", "cash": "Cash",
            "upi": "UPI", "gpay": "GPay", "phonepe": "PhonePe",
            "paytm": "Paytm", "other": "Other",
        }
        for keyword, display in accounts.items():
            result = parse_expense(f"lunch 100 {keyword}")
            assert result is not None, f"Failed for account keyword: {keyword}"
            assert result["account"] == display, f"Wrong display for {keyword}"

    # ── New Natural Language Parser Tests ─────────────────────────────────────

    def test_chai_cash_20(self):
        result = parse_expense("chai cash 20")
        assert result == {"description": "Chai", "category": "Food", "amount": "20", "account": "Cash"}

    def test_20_chai(self):
        result = parse_expense("20 chai")
        assert result == {"description": "Chai", "category": "Food", "amount": "20", "account": "Cash"}

    def test_20_chai_cash(self):
        result = parse_expense("20 chai cash")
        assert result == {"description": "Chai", "category": "Food", "amount": "20", "account": "Cash"}

    def test_spent_20_on_chai(self):
        result = parse_expense("spent 20 on chai")
        assert result == {"description": "Spent On Chai", "category": "Food", "amount": "20", "account": "Cash"}

    def test_spent_20_on_chai_cash(self):
        result = parse_expense("spent 20 on chai cash")
        assert result == {"description": "Spent On Chai", "category": "Food", "amount": "20", "account": "Cash"}

    def test_food_shared_with_vivek(self):
        result = parse_expense("food shared with vivek 220 bob")
        assert result == {"description": "Food Shared With Vivek", "category": "Food", "amount": "220", "account": "BOB"}

    def test_uber_home_to_office(self):
        result = parse_expense("uber home to office 137 bob")
        assert result == {"description": "Uber Home To Office", "category": "Transport", "amount": "137", "account": "BOB"}

    def test_metro_card_recharge(self):
        result = parse_expense("metro card recharge 300 bob")
        assert result == {"description": "Metro Card Recharge", "category": "Metro", "amount": "300", "account": "BOB"}

    def test_light_bill_bob(self):
        result = parse_expense("light bill 636 bob")
        assert result == {"description": "Light Bill", "category": "Bills", "amount": "636", "account": "BOB"}
