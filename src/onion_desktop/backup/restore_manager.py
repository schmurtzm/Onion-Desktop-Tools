"""Listing backups and restoring them onto an Onion SD card."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from ..core.copier import (
    ConflictPolicy,
    CopyItem,
    CopyReport,
    bytes_needed,
    dedupe,
    execute_copy,
    find_conflicts,
    sha256_file,
)
from ..core.exceptions import InsufficientSpaceError, OdtError
from ..core.progress import CancelToken, Progress, ProgressCallback, null_progress
from ..core.safe_fs import free_space, safe_join, walk_files
from ..onion.detection import CardInfo, CardState
from .backup_manager import MANIFEST
from .profiles import Category

CATEGORY_DIRS: dict[Category, str] = {
    Category.ROMS: "Roms",
    Category.IMGS: "Roms",
    Category.SAVES: "Saves",
    Category.BIOS: "BIOS",
    Category.RETROARCH: "RetroArch/.retroarch",
    Category.ONION_CONFIG: ".tmp_update/config",
}


@dataclass(frozen=True)
class BackupInfo:
    path: Path
    name: str
    info_text: str
    categories: tuple[Category, ...]
    manifest: dict[str, Any] | None

    @property
    def complete(self) -> bool | None:
        return None if self.manifest is None else bool(self.manifest.get("complete"))


def read_backup(path: Path) -> BackupInfo:
    texts = []
    for f in sorted(path.glob("Backupinfo_*.txt")):
        try:
            texts.append(f.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            pass
    cats = tuple(c for c, d in CATEGORY_DIRS.items() if (path / d).is_dir() and not (path / d).is_symlink())
    manifest = None
    try:
        data = json.loads((path / MANIFEST).read_text(encoding="utf-8"))
        manifest = data if isinstance(data, dict) else None
    except (OSError, ValueError):
        manifest = None
    return BackupInfo(path, path.name, "\n".join(texts) or "Backup information not available.", cats, manifest)


def list_backups(backups_dir: Path) -> list[BackupInfo]:
    if not backups_dir.is_dir():
        return []
    dirs = [p for p in backups_dir.iterdir() if p.is_dir() and not p.is_symlink()]
    return [read_backup(p) for p in sorted(dirs, key=lambda p: p.name, reverse=True)]


@dataclass
class RestorePlan:
    backup: BackupInfo
    target: Path
    card: CardInfo
    categories: tuple[Category, ...]
    items: list[CopyItem]
    conflicts: list[CopyItem]
    skipped: list[tuple[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def total_bytes(self) -> int:
        return sum(i.size for i in self.items)


def _in_imgs(rel: PurePosixPath) -> bool:
    return any(p.lower() == "imgs" for p in rel.parts[:-1])


def plan_restore(backup: BackupInfo, card: CardInfo, categories: tuple[Category, ...] | list[Category]) -> RestorePlan:
    chosen = tuple(c for c in categories if c in backup.categories)
    if not chosen:
        raise OdtError("Select at least one category present in the backup.")
    skipped: list[tuple[str, str]] = []
    items: list[CopyItem] = []
    for cat in chosen:
        sub = CATEGORY_DIRS[cat]
        src = backup.path / sub
        def on_skip(r: PurePosixPath, why: str, s: str = sub) -> None:
            skipped.append((f"{s}/{r}", why))

        for e in walk_files(src, on_skipped=on_skip):
            if cat is Category.ROMS and _in_imgs(e.rel):
                continue
            if cat is Category.IMGS and not (_in_imgs(e.rel) or e.rel.name.lower().endswith(".png")):
                continue
            items.append(CopyItem(e.path, PurePosixPath(sub) / e.rel, e.size, e.mtime))
    items = dedupe(items)
    warnings = []
    if card.state is not CardState.ONION:
        warnings.append(f"The target card is not a ready Onion installation ({card.state.label}).")
    if card.fs_type and card.fs_type != "vfat":
        warnings.append(f"The target file system is '{card.fs_type}', not FAT32.")
    if backup.complete is False:
        warnings.append("This backup was recorded as incomplete (some files failed when it was made).")
    return RestorePlan(backup, card.root, card, chosen, items, find_conflicts(items, card.root),
                       skipped, warnings)


@dataclass
class RestoreResult:
    report: CopyReport
    verify_failures: list[str]

    @property
    def ok(self) -> bool:
        return self.report.ok and not self.verify_failures


def run_restore(
    plan: RestorePlan, policy: ConflictPolicy, *, verify: bool = True,
    progress: ProgressCallback = null_progress, cancel: CancelToken | None = None,
) -> RestoreResult:
    cancel = cancel or CancelToken()
    need = bytes_needed(plan.items, plan.target, policy)
    avail = free_space(plan.target)
    if need > avail:
        raise InsufficientSpaceError(need, avail, "the restoration")
    report = execute_copy(plan.items, plan.target, policy=policy, fat_target=True,
                          progress=progress, cancel=cancel, label="Restoring")
    report.skipped = plan.skipped + report.skipped
    failures: list[str] = []
    files = (plan.backup.manifest or {}).get("files", {})
    if verify and isinstance(files, dict) and not report.cancelled:
        for i, rel in enumerate(report.copied):
            cancel.raise_if_cancelled()
            expected = files.get(rel, {}).get("sha256") if isinstance(files.get(rel), dict) else None
            if not expected:
                continue
            progress(Progress(f"Verifying {rel}", i, len(report.copied)))
            try:
                if sha256_file(safe_join(plan.target, rel)) != expected:
                    failures.append(rel)
            except OSError:
                failures.append(rel)
    return RestoreResult(report, failures)
