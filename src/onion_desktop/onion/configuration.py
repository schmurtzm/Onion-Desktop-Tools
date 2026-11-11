"""Onion OS flag-file configuration (``<card>/.tmp_update/config/.<flag>``).

A flag is *enabled* when its file exists. Upstream ODT disables a flag by renaming it to
``<flag>_`` (so any content is kept); enabling renames it back, or creates an empty file.
Files the schema does not describe are never touched.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

from ..core.exceptions import OdtError, ValidationError
from ..core.safe_fs import fsync_dir, walk_files

CONFIG_DIR = Path(".tmp_update/config")
FLAG_NAME_RE = re.compile(r"^\.[A-Za-z0-9_]{1,64}$")


@dataclass(frozen=True)
class FlagDefinition:
    filename: str
    short_description: str
    description: str
    sub_option: bool
    section: str


def parse_schema(data: Any) -> dict[str, list[FlagDefinition]]:
    try:
        sections = data["Onion_Configuration"]
    except (TypeError, KeyError) as exc:
        raise ValidationError("Flag schema lacks 'Onion_Configuration'.") from exc
    if not isinstance(sections, dict):
        raise ValidationError("Flag schema 'Onion_Configuration' must be an object.")
    out: dict[str, list[FlagDefinition]] = {}
    for section, items in sections.items():
        if not isinstance(items, list):
            raise ValidationError(f"Section {section!r} must be a list.")
        defs = []
        for item in items:
            name = item.get("filename") if isinstance(item, dict) else None
            if not isinstance(name, str) or not FLAG_NAME_RE.match(name):
                raise ValidationError(f"Invalid flag filename in section {section!r}: {name!r}")
            defs.append(FlagDefinition(
                filename=name,
                short_description=str(item.get("short_description", name)),
                description=str(item.get("description", "")),
                sub_option=bool(item.get("sub_option", 0)),
                section=str(section),
            ))
        out[str(section)] = defs
    return out


def load_default_schema() -> dict[str, list[FlagDefinition]]:
    text = resources.files("onion_desktop.resources").joinpath("onion_flags.json").read_text(
        encoding="utf-8"
    )
    return parse_schema(json.loads(text))


class FlagStore:
    def __init__(self, card_root: Path) -> None:
        self.card_root = card_root
        self.directory = card_root / CONFIG_DIR

    def _path(self, name: str) -> Path:
        if not FLAG_NAME_RE.match(name):
            raise ValidationError(f"Invalid flag name: {name!r}")
        return self.directory / name

    def exists(self) -> bool:
        return self.directory.is_dir() and not self.directory.is_symlink()

    def is_enabled(self, name: str) -> bool:
        p = self._path(name)
        return p.is_file() and not p.is_symlink()

    def set_enabled(self, name: str, enabled: bool) -> None:
        if not self.exists():
            raise OdtError("This card has no Onion configuration folder (.tmp_update/config).")
        p = self._path(name)
        disabled = p.with_name(name + "_")
        for q in (p, disabled):
            if q.is_symlink() or (q.exists() and not q.is_file()):
                raise OdtError(f"Refusing to modify unexpected entry {q.name}.")
        if enabled:
            if p.exists():
                return
            if disabled.exists():
                os.replace(disabled, p)
            else:
                p.touch()
        else:
            if not p.exists():
                return
            os.replace(p, disabled)
        fsync_dir(self.directory)

    def unknown_flags(self, schema: dict[str, list[FlagDefinition]]) -> list[str]:
        known = {d.filename for defs in schema.values() for d in defs}
        known |= {k + "_" for k in known}
        if not self.exists():
            return []
        return sorted(
            e.name for e in os.scandir(self.directory)
            if e.name.startswith(".") and e.name not in known and e.is_file(follow_symlinks=False)
        )

    def snapshot(self) -> dict[str, bool]:
        """Current state of all dot-files (used to revert a session's changes)."""
        if not self.exists():
            return {}
        return {
            e.name: True for e in os.scandir(self.directory)
            if e.name.startswith(".") and FLAG_NAME_RE.match(e.name) and e.is_file(follow_symlinks=False)
        }


def backup_config(card_root: Path, snapshots_dir: Path) -> Path:
    """Copy ``.tmp_update/config`` dot-files to a timestamped snapshot folder."""
    src = card_root / CONFIG_DIR
    if not src.is_dir():
        raise OdtError("No Onion configuration folder to back up.")
    dest = snapshots_dir / time.strftime("%Y-%m-%d %H.%M.%S")
    suffix = 1
    while dest.exists():
        suffix += 1
        dest = snapshots_dir / (time.strftime("%Y-%m-%d %H.%M.%S") + f" ({suffix})")
    dest.mkdir(parents=True, exist_ok=False)
    for entry in walk_files(src, max_depth=1):
        if entry.path.name.startswith("."):
            shutil.copy2(entry.path, dest / entry.path.name, follow_symlinks=False)
    return dest


def restore_config(snapshot: Path, card_root: Path, schema: dict[str, list[FlagDefinition]]) -> None:
    """Restore the state of *known* flags from a snapshot folder (unknown files untouched)."""
    store = FlagStore(card_root)
    present = {p.name for p in snapshot.iterdir() if p.is_file() and not p.is_symlink()}
    for defs in schema.values():
        for d in defs:
            store.set_enabled(d.filename, d.filename in present)
