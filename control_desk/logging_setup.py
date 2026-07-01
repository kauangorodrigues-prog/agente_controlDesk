from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

from .config import CFG

os.makedirs("logs", exist_ok=True)

_fmt = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)-22s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_console = logging.StreamHandler()
_console.setFormatter(_fmt)

_file = RotatingFileHandler(
    "logs/control_desk.log",
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
_file.setFormatter(_fmt)

_root = logging.getLogger("ControlDesk")
_root.setLevel(getattr(logging, CFG.LOG_LEVEL.upper(), logging.INFO))
_root.addHandler(_console)
_root.addHandler(_file)
_root.propagate = False


def get_logger(nome: str) -> logging.Logger:
    return _root.getChild(nome)


log = get_logger("core")
