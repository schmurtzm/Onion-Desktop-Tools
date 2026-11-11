"""XDG base directories for settings, data, cache and logs."""

from __future__ import annotations

import os
from pathlib import Path

from . import APP_ID


def _xdg(var: str, default: str) -> Path:
    value = os.environ.get(var, "")
    base = Path(value) if value and os.path.isabs(value) else Path.home() / default
    return base / APP_ID


def config_dir() -> Path:
    return _xdg("XDG_CONFIG_HOME", ".config")


def data_dir() -> Path:
    return _xdg("XDG_DATA_HOME", ".local/share")


def cache_dir() -> Path:
    return _xdg("XDG_CACHE_HOME", ".cache")


def state_dir() -> Path:
    return _xdg("XDG_STATE_HOME", ".local/state")


def default_downloads_dir() -> Path:
    return data_dir() / "downloads"


def default_backups_dir() -> Path:
    return data_dir() / "backups"


def config_snapshots_dir() -> Path:
    return data_dir() / "config-snapshots"


def log_dir() -> Path:
    return state_dir() / "logs"
