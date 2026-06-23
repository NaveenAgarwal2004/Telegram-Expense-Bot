"""
Tests for Google Sheets append in handlers.py.

Verifies that handle_message calls sheet.append_row with the exact
5-column row format: [date, description, category, amount, account].

The sheet object is already mocked by conftest.py.
handlers.sheets.sheet is patched per test so we can assert on call args.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


def _make_update(user_id: int, text: str) -> MagicMock:
    """Build a minimal mock Update object."""
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def allowed_update():
    return _make_update(user_id=111, text="lunch 80 cash")


@pytest.fixture
def disallowed_update():
    return _make_update(user_id=999, text="lunch 80 cash")


class TestSheetsAppend:
    async def test_append_row_called_on_valid_expense(self, mock_sheet, allowed_update):
        """Valid expense message → sheet.append_row called exactly once."""
        with patch("handlers.sheet", mock_sheet):
            from handlers import handle_message
            await handle_message(allowed_update, MagicMock())

        mock_sheet.append_row.assert_called_once()

    async def test_append_row_columns(self, mock_sheet, allowed_update):
        """Row passed to append_row has exactly 5 columns in correct order."""
        with patch("handlers.sheet", mock_sheet):
            from handlers import handle_message
            await handle_message(allowed_update, MagicMock())

        call_args = mock_sheet.append_row.call_args
        row = call_args[0][0]          # first positional argument

        assert len(row) == 5, f"Expected 5 columns, got {len(row)}: {row}"
        date_col, desc_col, cat_col, amount_col, account_col = row

        # Date format: DD-MM-YYYY HH:MM:SS
        datetime.strptime(date_col, "%d-%m-%Y %H:%M:%S")  # raises if wrong format

        assert desc_col   == "Lunch"
        assert cat_col    == "Food"
        assert amount_col == "80"
        assert account_col == "Cash"

    async def test_append_row_value_input_option(self, mock_sheet, allowed_update):
        """append_row must use value_input_option='USER_ENTERED'."""
        with patch("handlers.sheet", mock_sheet):
            from handlers import handle_message
            await handle_message(allowed_update, MagicMock())

        call_kwargs = mock_sheet.append_row.call_args[1]
        assert call_kwargs.get("value_input_option") == "USER_ENTERED"

    async def test_disallowed_user_does_not_append(self, mock_sheet, disallowed_update):
        """Messages from non-allowed users must never write to the sheet."""
        with patch("handlers.sheet", mock_sheet):
            from handlers import handle_message
            await handle_message(disallowed_update, MagicMock())

        mock_sheet.append_row.assert_not_called()

    async def test_unparseable_message_does_not_append(self, mock_sheet):
        """Unparseable text must not write to the sheet."""
        update = _make_update(user_id=111, text="hello there")
        with patch("handlers.sheet", mock_sheet):
            from handlers import handle_message
            await handle_message(update, MagicMock())

        mock_sheet.append_row.assert_not_called()

    async def test_sheet_error_replies_with_error_message(self, mock_sheet):
        """If sheet.append_row raises, bot replies with error message (not crash)."""
        mock_sheet.append_row.side_effect = Exception("network error")
        update = _make_update(user_id=111, text="chai 20 cash")

        with patch("handlers.sheet", mock_sheet):
            from handlers import handle_message
            await handle_message(update, MagicMock())

        update.message.reply_text.assert_called_once_with("Error saving to sheet. Try again.")

    async def test_bob_account_appended_correctly(self, mock_sheet):
        """BOB account keyword maps to display name 'BOB' in the sheet row."""
        update = _make_update(user_id=111, text="uber 137 bob")
        with patch("handlers.sheet", mock_sheet):
            from handlers import handle_message
            await handle_message(update, MagicMock())

        row = mock_sheet.append_row.call_args[0][0]
        assert row[4] == "BOB"      # account column

    async def test_upi_account_appended_correctly(self, mock_sheet):
        update = _make_update(user_id=111, text="medicine 250 upi")
        with patch("handlers.sheet", mock_sheet):
            from handlers import handle_message
            await handle_message(update, MagicMock())

        row = mock_sheet.append_row.call_args[0][0]
        assert row[4] == "UPI"
