"""SD card content classification — the upstream ``Get_SDcardType`` rules, made reusable."""

from __future__ import annotations

import enum
import os
import re
from dataclasses import dataclass
from pathlib import Path

from ..core.safe_fs import filesystem_type_of, free_space, total_space

VERSION_TXT = Path(".tmp_update/onionVersion/version.txt")
INSTALLUI = Path(".tmp_update/bin/installUI")
PENDING_PAK = Path("miyoo/app/.tmp_update/onion.pak")
PENDING_INSTALLUI = Path("miyoo/app/.tmp_update/bin/installUI")
RUNTIME_SH = Path(".tmp_update/runtime.sh")

# Entries created by desktop OSes that do not make a card "non-empty".
IGNORED_ROOT_ENTRIES = {"System Volume Information", "lost+found", ".Trashes", ".Spotlight-V100",
                        ".fseventsd", "$RECYCLE.BIN"}

_MAX_BINARY_SCAN = 16 * 1024 * 1024
_PRINTABLE_RUN = re.compile(rb"[\x20-\x7e]{4,}")
_VERSION_TOKEN = re.compile(r"^v?\d+\.\d+(?:\.\d+)?(?:-[0-9A-Za-z.\-]+)?$")


class CardState(enum.Enum):
    EMPTY = "empty"
    ONION = "Onion"
    ONION_INSTALL_PENDING = "Onion_InstallPending"
    STOCK = "Stock"
    OTHER = "Other"
    UNREADABLE = "Unreadable"

    @property
    def label(self) -> str:
        return {
            CardState.EMPTY: "Empty SD card",
            CardState.ONION: "Onion OS installed",
            CardState.ONION_INSTALL_PENDING: "Onion OS files copied, installation not run yet",
            CardState.STOCK: "Miyoo stock OS",
            CardState.OTHER: "Unknown content (not Onion or stock)",
            CardState.UNREADABLE: "Cannot read card",
        }[self]


@dataclass(frozen=True)
class CardInfo:
    root: Path
    state: CardState
    version: str | None
    update_pending: bool  # onion.pak present on an installed Onion (update not applied yet)
    fs_type: str | None
    free_bytes: int | None
    total_bytes: int | None
    error: str | None = None

    @property
    def version_label(self) -> str:
        return self.version or "unknown version"

    @property
    def is_fat32_compatible(self) -> bool:
        return self.fs_type in (None, "vfat")


def strings_version(path: Path) -> str | None:
    """Re-implementation of upstream ``strings installUI | --version\\s+(.*?)\\s``.

    Scans printable runs of the binary and returns the first version-like token after
    the ``--version`` literal.
    """
    try:
        with open(path, "rb") as f:
            data = f.read(_MAX_BINARY_SCAN)
    except OSError:
        return None
    runs = [r.decode("ascii") for r in _PRINTABLE_RUN.findall(data)]
    for i, run in enumerate(runs):
        if run.strip() == "--version":
            for candidate in runs[i + 1 : i + 8]:
                token = candidate.strip()
                if _VERSION_TOKEN.match(token):
                    return str(token.lstrip("v"))
    return None


def read_version_txt(root: Path) -> str | None:
    p = root / VERSION_TXT
    try:
        if p.is_symlink() or not p.is_file():
            return None
        text = p.read_text(encoding="utf-8", errors="replace")[:200].strip().lstrip("﻿")
    except OSError:
        return None
    text = text.lstrip("vV").strip()
    return text or None


def _is_file(p: Path) -> bool:
    return p.is_file() and not p.is_symlink()


def _is_dir(p: Path) -> bool:
    return p.is_dir() and not p.is_symlink()


def detect_card(root: Path) -> CardInfo:
    """Classify the mounted card at *root* (read-only)."""
    fs_type = filesystem_type_of(root)
    free: int | None
    total: int | None
    try:
        free = free_space(root)
        total = total_space(root)
    except OSError:
        free = total = None
    try:
        entries = [e for e in os.listdir(root) if e not in IGNORED_ROOT_ENTRIES]
    except OSError as exc:
        return CardInfo(root, CardState.UNREADABLE, None, False, fs_type, free, total,
                        error=str(exc.strerror or exc))

    pending_pak = _is_file(root / PENDING_PAK)
    if not entries:
        return CardInfo(root, CardState.EMPTY, None, False, fs_type, free, total)

    if _is_file(root / INSTALLUI) or _is_file(root / VERSION_TXT):
        version = read_version_txt(root) or strings_version(root / INSTALLUI)
        return CardInfo(root, CardState.ONION, version, pending_pak, fs_type, free, total)

    if _is_dir(root / ".tmp_update") and pending_pak:
        version = strings_version(root / PENDING_INSTALLUI)
        return CardInfo(root, CardState.ONION_INSTALL_PENDING, version, True, fs_type, free, total)

    if _is_dir(root / "RApp"):
        return CardInfo(root, CardState.STOCK, None, False, fs_type, free, total)

    return CardInfo(root, CardState.OTHER, None, False, fs_type, free, total)
