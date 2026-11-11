"""Persistent application settings (JSON in the XDG config directory)."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from . import paths

log = logging.getLogger(__name__)
THEMES = ("system", "light", "dark", "dracula")


@dataclass
class Settings:
    theme: str = "system"
    downloads_dir: str = ""
    backups_dir: str = ""
    check_updates_on_start: bool = False
    verify_after_install: bool = True
    play_sounds: bool = False

    @property
    def downloads_path(self) -> Path:
        return Path(self.downloads_dir) if self.downloads_dir else paths.default_downloads_dir()

    @property
    def backups_path(self) -> Path:
        return Path(self.backups_dir) if self.backups_dir else paths.default_backups_dir()

    def validate(self) -> None:
        if self.theme not in THEMES:
            self.theme = "system"
        for name in ("downloads_dir", "backups_dir"):
            v = getattr(self, name)
            if v and not os.path.isabs(v):
                setattr(self, name, "")


def settings_file() -> Path:
    return paths.config_dir() / "settings.json"


def load(path: Path | None = None) -> Settings:
    path = path or settings_file()
    s = Settings()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return s
    except (OSError, ValueError) as exc:
        log.warning("Ignoring unreadable settings file %s: %s", path, exc)
        return s
    if isinstance(data, dict):
        for f in fields(Settings):
            if f.name in data and isinstance(data[f.name], type(getattr(s, f.name))):
                setattr(s, f.name, data[f.name])
    s.validate()
    return s


def save(s: Settings, path: Path | None = None) -> None:
    path = path or settings_file()
    s.validate()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(s), indent=2), encoding="utf-8")
    os.replace(tmp, path)
