"""
Tests for Telegram bot startup — handler registration and polling wiring.

Strategy: We inspect bot.py statically (without executing the __main__ block)
to verify that the wiring calls are correct, and test the health server
thread configuration by examining bot.py's source via AST analysis.

For runtime assertions we test the individual components:
  - health.run_health_server is a callable
  - config.BOT_TOKEN is read from env
  - handlers are importable and are coroutines
  - Thread daemon=True is verified by inspecting bot.py source
"""

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
import inspect


_BOT_SRC = (Path(__file__).parent.parent / "bot.py").read_text(encoding="utf-8")
_BOT_TREE = ast.parse(_BOT_SRC)


def _get_main_block_src() -> ast.If:
    """Extract the if __name__ == '__main__' block from bot.py AST."""
    for node in ast.walk(_BOT_TREE):
        if (
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and node.test.left.id == "__name__"
        ):
            return node
    raise AssertionError("No if __name__ == '__main__' block found in bot.py")


class TestTelegramStartupStatic:
    """AST-based tests — verify wiring without executing the __main__ block."""

    def test_main_block_exists(self):
        """bot.py must have an if __name__ == '__main__' guard."""
        block = _get_main_block_src()
        assert block is not None

    def test_thread_created_with_daemon_true(self):
        """Thread() call in __main__ block must pass daemon=True."""
        block = _get_main_block_src()
        src = ast.unparse(block)
        assert "daemon=True" in src, (
            "Thread must be started with daemon=True in the __main__ block"
        )

    def test_thread_target_is_run_health_server(self):
        """Thread target in __main__ block must be run_health_server."""
        block = _get_main_block_src()
        src = ast.unparse(block)
        assert "run_health_server" in src, (
            "run_health_server must be used as Thread target in __main__ block"
        )

    def test_run_polling_called_with_drop_pending(self):
        """run_polling call must include drop_pending_updates=True."""
        block = _get_main_block_src()
        src = ast.unparse(block)
        assert "drop_pending_updates=True" in src, (
            "run_polling must be called with drop_pending_updates=True"
        )

    def test_four_add_handler_calls(self):
        """Exactly 4 add_handler calls must appear in the __main__ block."""
        block = _get_main_block_src()
        calls = [
            node for node in ast.walk(block)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_handler"
            )
        ]
        assert len(calls) == 4, f"Expected 4 add_handler calls, found {len(calls)}"

    def test_command_handler_start_registered(self):
        """A CommandHandler for 'start' must be registered."""
        block = _get_main_block_src()
        src = ast.unparse(block)
        assert '"start"' in src or "'start'" in src, (
            "CommandHandler for 'start' not found in __main__ block"
        )

    def test_command_handler_today_registered(self):
        """A CommandHandler for 'today' must be registered."""
        block = _get_main_block_src()
        src = ast.unparse(block)
        assert '"today"' in src or "'today'" in src, (
            "CommandHandler for 'today' not found in __main__ block"
        )

    def test_command_handler_last_registered(self):
        """A CommandHandler for 'last' must be registered."""
        block = _get_main_block_src()
        src = ast.unparse(block)
        assert '"last"' in src or "'last'" in src, (
            "CommandHandler for 'last' not found in __main__ block"
        )


class TestTelegramStartupRuntime:
    """Runtime tests — verify callable types and config without starting the bot."""

    def test_run_health_server_is_callable(self):
        from health import run_health_server
        assert callable(run_health_server)

    def test_cmd_start_is_coroutine_function(self):
        from handlers import cmd_start
        assert inspect.iscoroutinefunction(cmd_start), \
            "cmd_start must be an async function"

    def test_cmd_today_is_coroutine_function(self):
        from handlers import cmd_today
        assert inspect.iscoroutinefunction(cmd_today), \
            "cmd_today must be an async function"

    def test_cmd_last_is_coroutine_function(self):
        from handlers import cmd_last
        assert inspect.iscoroutinefunction(cmd_last), \
            "cmd_last must be an async function"

    def test_handle_message_is_coroutine_function(self):
        from handlers import handle_message
        assert inspect.iscoroutinefunction(handle_message), \
            "handle_message must be an async function"

    def test_bot_token_loaded_from_env(self):
        from config import BOT_TOKEN
        assert BOT_TOKEN == "test-token-123"

    def test_port_loaded_from_env(self):
        from config import PORT
        assert PORT == 8080

    def test_allowed_user_ids_parsed_correctly(self):
        from config import ALLOWED_USER_IDS
        assert "111" in ALLOWED_USER_IDS
        assert "222" in ALLOWED_USER_IDS
        assert "999" not in ALLOWED_USER_IDS
