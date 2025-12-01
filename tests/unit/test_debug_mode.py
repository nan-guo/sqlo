"""Tests for debug mode functionality."""

from contextlib import redirect_stdout
from io import StringIO

from sqlo import Q


def test_debug_mode_basic():
    """Test basic debug mode functionality."""
    # Enable debug mode
    Q.set_debug(True)

    # Capture stdout
    f = StringIO()
    with redirect_stdout(f):
        q = Q.select("id").from_("users").where("id", 1)
        q.build()

    output = f.getvalue()

    # Verify debug output
    assert "[sqlo DEBUG]" in output
    assert "SELECT `id` FROM `users` WHERE `id` = %s" in output
    assert "Params: (1,)" in output

    # Disable debug mode
    Q.set_debug(False)


def test_debug_mode_disabled():
    """Test that debug mode can be disabled."""
    Q.set_debug(False)

    f = StringIO()
    with redirect_stdout(f):
        q = Q.select("id").from_("users").where("id", 1)
        q.build()

    output = f.getvalue()

    # Should not have debug output
    assert "[sqlo DEBUG]" not in output
