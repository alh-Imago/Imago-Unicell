"""
imago_log.py — Centralised logging for the Imago UniCell VM.

All diagnostic output from the VM (controller, pond, shore, compiler, etc.)
goes through this module. By default it behaves exactly as before (prints to
stdout). When used as a library (pip install imago-vm), callers can silence
or redirect all output with a single call.

Usage:
    # Silence all VM output (library use)
    import imago_log
    imago_log.set_level(imago_log.SILENT)

    # Or via environment variable (before importing imago)
    IMAGO_VERBOSE=0 python3 my_script.py

    # Redirect to Python logging
    import logging
    imago_log.set_handler(logging.getLogger("imago"))

    # From the imago package
    import imago
    imago.set_verbose(False)

Levels:
    SILENT  — no output at all
    ERROR   — errors and rejections only
    WARN    — warnings + errors
    INFO    — normal operation messages (default)
    DEBUG   — verbose internal state
"""

import os
import sys

# ── Levels ────────────────────────────────────────────────────────────────────

SILENT = 0
ERROR  = 1
WARN   = 2
INFO   = 3
DEBUG  = 4

_LEVEL_NAMES = {SILENT: "SILENT", ERROR: "ERROR", WARN: "WARN",
                INFO: "INFO", DEBUG: "DEBUG"}

# ── State ─────────────────────────────────────────────────────────────────────

_level:   int  = INFO    # current verbosity level
_handler        = None   # optional callable(msg) or logging.Logger
_stream         = sys.stdout

# Read from environment at import time
_env = os.environ.get("IMAGO_VERBOSE", "").strip().lower()
if _env in ("0", "false", "off", "silent", "no"):
    _level = SILENT
elif _env in ("1", "true", "on", "yes"):
    _level = INFO
elif _env == "debug":
    _level = DEBUG
elif _env == "error":
    _level = ERROR
elif _env == "warn":
    _level = WARN

# ── Public API ────────────────────────────────────────────────────────────────

def set_level(level: int) -> None:
    """Set verbosity level (SILENT, ERROR, WARN, INFO, DEBUG)."""
    global _level
    _level = level


def set_handler(handler) -> None:
    """
    Set a custom output handler.

    handler can be:
      - A Python logging.Logger (messages go via logger.info / logger.warning etc.)
      - Any callable that accepts a string message
      - None to restore default stdout printing
    """
    global _handler
    _handler = handler


def get_level() -> int:
    """Return current verbosity level."""
    return _level


def is_verbose() -> bool:
    """True if level >= INFO (normal default)."""
    return _level >= INFO


# ── Emit functions ────────────────────────────────────────────────────────────

def _emit(msg: str, level: int) -> None:
    if _level < level:
        return
    if _handler is not None:
        import logging as _logging
        if isinstance(_handler, _logging.Logger):
            if level <= ERROR:
                _handler.error(msg)
            elif level <= WARN:
                _handler.warning(msg)
            else:
                _handler.info(msg)
        else:
            _handler(msg)
    else:
        print(msg, file=_stream)


def info(msg: str) -> None:
    _emit(msg, INFO)


def warn(msg: str) -> None:
    _emit(msg, WARN)


def error(msg: str) -> None:
    _emit(msg, ERROR)


def debug(msg: str) -> None:
    _emit(msg, DEBUG)
