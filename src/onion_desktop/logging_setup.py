"""Logging configuration with secret redaction."""

from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

_SECRET_PATTERNS = [
    re.compile(r'(psk\s*=\s*)("[^"\n]*"|\S+)', re.IGNORECASE),
    re.compile(r'((?:password|passwd|passphrase|secret|token)\s*[=:]\s*)("[^"\n]*"|\S+)', re.IGNORECASE),
]


def redact(text: str) -> str:
    for pat in _SECRET_PATTERNS:
        text = pat.sub(lambda m: m.group(1) + "***", text)
    return text


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        red = redact(msg)
        if red != msg:
            record.msg, record.args = red, ()
        return True


def configure(log_dir: Path | None, debug: bool = False) -> Path | None:
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    console.addFilter(RedactingFilter())
    console.setLevel(logging.DEBUG if debug else logging.WARNING)
    root.addHandler(console)
    log_file = None
    if log_dir is not None:
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "odt.log"
            fh = RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
            fh.setFormatter(fmt)
            fh.addFilter(RedactingFilter())
            root.addHandler(fh)
        except OSError:
            log_file = None
    return log_file
