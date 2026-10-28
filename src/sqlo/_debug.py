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


# (handler, logger level, logger propagate, params logger level) before enable()
_saved: Optional[tuple[_StdoutHandler, int, bool, int]] = None


def enable(hide_params: bool = False) -> None:
    """Log queries to stdout. Calling it again replaces the previous setup."""
    global _saved
    disable()
    handler = _StdoutHandler()
    _saved = (handler, logger.level, logger.propagate, params_logger.level)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # the handler is the output: do not print twice
    if hide_params:
        params_logger.setLevel(logging.WARNING)


def disable() -> None:
    """Undo ``enable()``, restoring the logger settings it replaced."""
    global _saved
    if _saved is None:
        return
    handler, level, propagate, params_level = _saved
    logger.removeHandler(handler)
    logger.setLevel(level)
    logger.propagate = propagate
    params_logger.setLevel(params_level)
    _saved = None


def log_query(sql: str, params: tuple[Any, ...]) -> None:
    """Log a built query; nothing is formatted unless DEBUG is enabled."""
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("%s", sql)
        params_logger.debug("Params: %s", params)
