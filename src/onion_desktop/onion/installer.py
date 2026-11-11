"""Onion installation / upgrade / repair planning and execution.

Semantics follow upstream ``Onion_Install_Extract.ps1``: the release ZIP is extracted to the
card root, overwriting existing files; the Miyoo performs the actual installation on its next
boot. ROMs, saves and RetroArch configuration are not part of the archive and are preserved.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path

from ..core.archive import ArchiveManifest, ExtractReport, extract_zip, inspect_zip
from ..core.exceptions import ArchiveError, InsufficientSpaceError, OdtError
from ..core.progress import CancelToken, Progress, ProgressCallback, null_progress
from ..core.safe_fs import free_space, safe_join
from .detection import PENDING_PAK, CardInfo, CardState, detect_card
from .versions import parse_version, version_from_asset_name

REQUIRED_MEMBERS = ("miyoo/app/.tmp_update/onion.pak",)
SPACE_MARGIN = 16 * 1024 * 1024


class InstallMode(enum.Enum):
    FRESH = "fresh"
    UPGRADE = "upgrade"
    REINSTALL = "reinstall"  # same version → repair
    DOWNGRADE = "downgrade"
    PENDING = "pending"  # card already holds a not-yet-run Onion install
    STOCK = "stock"  # strongly discouraged
    OTHER = "other"  # card holds unknown data


@dataclass
class InstallPlan:
    archive: Path
    target: Path
    card: CardInfo
    mode: InstallMode
    archive_version: str | None
    manifest: ArchiveManifest
    required_bytes: int
    available_bytes: int | None
    warnings: list[str] = field(default_factory=list)
    confirmation: str = ""
    requires_strong_confirmation: bool = False


@dataclass
class InstallResult:
    plan: InstallPlan
    extract: ExtractReport
    card_after: CardInfo

    @property
    def ok(self) -> bool:
        return self.extract.ok and self.extract.verified


def _bytes_required(manifest: ArchiveManifest, target: Path) -> int:
    """Net additional bytes: new files fully, overwritten files only their growth."""
    need = 0
    for m in manifest.members:
        if m.is_dir:
            continue
        try:
            existing = safe_join(target, m.rel)
            cur = existing.stat().st_size if existing.is_file() else 0
        except (OdtError, OSError):
            cur = 0
        # During replace both the temp copy and the old file exist: count the larger file.
        need += m.info.file_size if cur == 0 else max(0, m.info.file_size - cur) + m.info.file_size
    return need


def validate_onion_archive(archive: Path) -> ArchiveManifest:
    manifest = inspect_zip(archive)
    names = manifest.names()
    missing = [r for r in REQUIRED_MEMBERS if r not in names]
    if missing:
        raise ArchiveError(
            f"'{archive.name}' does not look like an Onion OS release (missing {missing[0]})."
        )
    return manifest


def plan_install(archive: Path, target: Path) -> InstallPlan:
    if not target.is_dir():
        raise OdtError(f"Target {target} is not an accessible folder.")
    manifest = validate_onion_archive(archive)
    card = detect_card(target)
    if card.state is CardState.UNREADABLE:
        raise OdtError(f"Cannot read the SD card at {target}: {card.error}")
    archive_version = version_from_asset_name(archive.name)
    new_v = parse_version(archive_version) if archive_version else None
    old_v = parse_version(card.version) if card.version else None
    name = archive.name
    warnings: list[str] = []
    strong = False

    if card.state is CardState.EMPTY:
        mode = InstallMode.FRESH
        text = f"You're about to install {name}.\nAre you sure that you want to install it on {target}?"
    elif card.state is CardState.ONION:
        if new_v and old_v and new_v < old_v:
            mode = InstallMode.DOWNGRADE
            warnings.append(f"The card has a newer Onion ({card.version}) than the archive.")
        elif new_v and old_v and new_v == old_v:
            mode = InstallMode.REINSTALL
        else:
            mode = InstallMode.UPGRADE
        verb = {InstallMode.DOWNGRADE: "downgrade", InstallMode.REINSTALL: "reinstall (repair)"}.get(
            mode, "upgrade"
        )
        text = (
            f"You're about to {verb} Onion OS\n\"{card.version_label}\" to \"{name}\".\n\n"
            "Saves, ROMs and configuration will be kept.\nAre you sure?"
        )
        if card.update_pending:
            warnings.append("An update was already copied to this card but has not been applied yet.")
    elif card.state is CardState.ONION_INSTALL_PENDING:
        mode = InstallMode.PENDING
        text = (
            f"This card contains Onion OS files ({card.version_label}) whose installation has never "
            f"been run on the console.\nThey will be replaced by {name}.\n\n"
            "If the card holds no data of yours, formatting it first is cleaner.\n"
            "Are you sure that you want to update?"
        )
    elif card.state is CardState.STOCK:
        mode = InstallMode.STOCK
        strong = True
        text = (
            f"You're about to install {name} over the Miyoo STOCK operating system.\n\n"
            "This is NOT recommended or supported and can cause many side effects. Use a new, "
            "genuine SD card for Onion and migrate your stock data with Backup & Restore.\n\n"
            "Do you really want to force this installation?"
        )
    else:
        mode = InstallMode.OTHER
        strong = True
        text = (
            f"You're about to install {name} on a card that already contains other data.\n"
            "This is possible but not recommended; formatting the card first is preferred.\n\n"
            "Do you really want to force this installation?"
        )
    if card.fs_type and card.fs_type != "vfat":
        warnings.append(
            f"The card's file system is '{card.fs_type}', which Onion does not support. "
            "Format it as FAT32 first."
        )
        strong = True

    required = _bytes_required(manifest, target) + SPACE_MARGIN
    available = card.free_bytes
    return InstallPlan(
        archive=archive, target=target, card=card, mode=mode, archive_version=archive_version,
        manifest=manifest, required_bytes=required, available_bytes=available, warnings=warnings,
        confirmation=text, requires_strong_confirmation=strong,
    )


def execute_install(
    plan: InstallPlan,
    *,
    progress: ProgressCallback = null_progress,
    cancel: CancelToken | None = None,
) -> InstallResult:
    cancel = cancel or CancelToken()
    # Re-check: the card must still be the one that was planned for.
    now = detect_card(plan.target)
    if now.state is not plan.card.state or now.version != plan.card.version:
        raise OdtError(
            "The SD card content changed since the installation was planned. Please review again."
        )
    available = free_space(plan.target)
    if available < plan.required_bytes:
        raise InsufficientSpaceError(plan.required_bytes, available, "the Onion installation")
    progress(Progress(f"Extracting {plan.archive.name} to {plan.target}", 0, 0))
    report = extract_zip(
        plan.archive, plan.target, manifest=plan.manifest, progress=progress, cancel=cancel,
        verify=True, fat_target=True,
    )
    after = detect_card(plan.target)
    if report.ok and not (plan.target / PENDING_PAK).is_file():
        report.failed.append((str(PENDING_PAK), "missing after extraction"))
    return InstallResult(plan, report, after)
