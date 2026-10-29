"""Debug logging: built queries are logged on the ``sqlo`` logger at DEBUG level.

The SQL goes to ``sqlo`` and the parameters to ``sqlo.params``, so the values
(which may be sensitive) can be silenced on their own with ordinary logging
configuration. ``Q.set_debug()`` is a shortcut that prints both to stdout.
"""

import logging
import sys
from typing import Any, Optional

logger = logging.getLogger("sqlo")
params_logger = logging.getLogger("sqlo.params")


class _StdoutHandler(logging.Handler):
    """Writes to whatever ``sys.stdout`` is when a record is emitted.

    A ``StreamHandler`` would keep the stream it was created with and ignore a
    later ``redirect_stdout()``.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setFormatter(logging.Formatter("[sqlo DEBUG] %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            sys.stdout.write(self.format(record) + "\n")
            sys.stdout.flush()
        except Exception:
            self.handleError(record)


class _State:
    """What ``enable()`` replaced, so that ``disable()`` can put it back."""

    # (handler, logger level, logger propagate, params logger level)
    saved: Optional[tuple[_StdoutHandler, int, bool, int]] = None


_state = _State()


def enable(hide_params: bool = False) -> None:
    """Log queries to stdout. Calling it again replaces the previous setup."""
    disable()
    handler = _StdoutHandler()
    _state.saved = (handler, logger.level, logger.propagate, params_logger.level)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # the handler is the output: do not print twice
    if hide_params:
        params_logger.setLevel(logging.WARNING)


def disable() -> None:
    """Undo ``enable()``, restoring the logger settings it replaced."""
    if _state.saved is None:
        return
    handler, level, propagate, params_level = _state.saved
    logger.removeHandler(handler)
    logger.setLevel(level)
    logger.propagate = propagate
    params_logger.setLevel(params_level)
    _state.saved = None


def log_query(sql: str, params: tuple[Any, ...]) -> None:
    """Log a built query; nothing is formatted unless DEBUG is enabled."""
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("%s", sql)
        params_logger.debug("Params: %s", params)
