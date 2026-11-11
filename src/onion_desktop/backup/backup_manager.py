"""Backup of an Onion or stock SD card into a local folder.

Folder layout is compatible with upstream ODT backups
(``<yyyy-MM-dd HH.mm.ss>_<State>_<Version>/`` + ``Backupinfo_<date>.txt``), plus a
machine-readable ``odt_manifest.json`` with per-file SHA-256 used to verify restores.
"""

from __future__ import annotations

import fnmatch
import json
import re
import time
import zipfile
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path, PurePosixPath

from ..core.copier import ConflictPolicy, CopyItem, CopyReport, dedupe, execute_copy
from ..core.exceptions import InsufficientSpaceError, OdtError
from ..core.progress import CancelToken, Progress, ProgressCallback, null_progress
from ..core.safe_fs import free_space, walk_files
from ..onion.detection import VERSION_TXT, CardInfo, CardState
from .profiles import Category, available_categories

MANIFEST = "odt_manifest.json"
STOCK_BIOS_EXCLUDED_DIRS = {"cheats", "cheats备用版", "glupen64", "mupen64plus", "pscnbios", "scummvm"}
STOCK_BIOS_EXCLUDED_FILES = ("scph39*",)


@dataclass
class BackupPlan:
    source: Path
    card: CardInfo
    categories: tuple[Category, ...]
    items: list[CopyItem]
    skipped: list[tuple[str, str]] = field(default_factory=list)
    add_fbneo_cheats: bool = False

    @property
    def total_bytes(self) -> int:
        return sum(i.size for i in self.items)


@dataclass
class BackupResult:
    folder: Path
    report: CopyReport

    @property
    def ok(self) -> bool:
        return self.report.ok


def _items(root: Path, src_rel: str, dst_rel: str, skipped: list[tuple[str, str]], *,
           skip_dir_names: set[str] | None = None, file_glob: tuple[str, ...] | None = None,
           exclude_files: tuple[str, ...] = (), max_depth: int | None = None,
           skip_top_dirs: set[str] | None = None) -> list[CopyItem]:
    src = root / src_rel
    if not src.is_dir() or src.is_symlink():
        return []

    def skip_dir(rel: PurePosixPath) -> bool:
        if skip_dir_names and rel.name.lower() in skip_dir_names:
            return True
        return bool(skip_top_dirs and len(rel.parts) == 1 and rel.name.lower() in skip_top_dirs)

    def on_skip(rel: PurePosixPath, why: str) -> None:
        skipped.append((f"{src_rel}/{rel}", why))

    out = []
    for e in walk_files(src, skip_dir=skip_dir, on_skipped=on_skip, max_depth=max_depth):
        name = e.rel.name
        if file_glob and not any(fnmatch.fnmatch(name.lower(), g.lower()) for g in file_glob):
            continue
        if any(fnmatch.fnmatch(name.lower(), g.lower()) for g in exclude_files):
            continue
        out.append(CopyItem(e.path, PurePosixPath(dst_rel) / e.rel, e.size, e.mtime))
    return out


def plan_backup(card: CardInfo, categories: tuple[Category, ...] | list[Category]) -> BackupPlan:
    root = card.root
    allowed = set(available_categories(card.state))
    chosen = tuple(c for c in categories if c in allowed)
    if not chosen:
        raise OdtError("Nothing to back up: no available category selected for this card.")
    onion = (root / VERSION_TXT).is_file()
    skipped: list[tuple[str, str]] = []
    items: list[CopyItem] = []
    add_cheats = False
    for cat in chosen:
        if cat is Category.ROMS:
            items += _items(root, "Roms", "Roms", skipped, skip_dir_names={"imgs"})
        elif cat is Category.IMGS:
            items += _items(root, "Roms", "Roms", skipped, file_glob=("*.png",))
            stock_imgs = root / "Imgs"
            if stock_imgs.is_dir() and not stock_imgs.is_symlink():
                for sysdir in sorted(p for p in stock_imgs.iterdir() if p.is_dir() and not p.is_symlink()):
                    items += _items(root, f"Imgs/{sysdir.name}", f"Roms/{sysdir.name}/Imgs", skipped,
                                    file_glob=("*.png",))
        elif cat is Category.SAVES:
            if onion:
                items += _items(root, "Saves", "Saves", skipped)
        elif cat is Category.BIOS:
            if onion:
                items += _items(root, "BIOS", "BIOS", skipped)
            else:
                items += _items(root, "RetroArch/.retroarch/system", "BIOS", skipped,
                                skip_dir_names=STOCK_BIOS_EXCLUDED_DIRS - {"scummvm"},
                                skip_top_dirs={"scummvm"}, exclude_files=STOCK_BIOS_EXCLUDED_FILES)
                add_cheats = True
        elif cat is Category.RETROARCH:
            items += _items(root, "RetroArch/.retroarch", "RetroArch/.retroarch", skipped,
                            file_glob=("*.cfg",), max_depth=1)
        elif cat is Category.ONION_CONFIG:
            items += _items(root, ".tmp_update/config", ".tmp_update/config", skipped,
                            file_glob=(".*",))
    return BackupPlan(root, card, chosen, dedupe(items), skipped, add_cheats)


_SAFE_COMPONENT = re.compile(r"[^0-9A-Za-z.\-+ ()]")


def backup_folder_name(card: CardInfo, when: time.struct_time | None = None) -> str:
    when = when or time.localtime()
    version = _SAFE_COMPONENT.sub("_", card.version or "(unknown version)")[:60]
    return f"{time.strftime('%Y-%m-%d %H.%M.%S', when)}_{card.state.value}_{version}"


def _new_folder(backups_dir: Path, name: str) -> Path:
    backups_dir.mkdir(parents=True, exist_ok=True)
    candidate = backups_dir / name
    n = 1
    while True:
        try:
            candidate.mkdir(exist_ok=False)
            return candidate
        except FileExistsError:
            n += 1
            candidate = backups_dir / f"{name} ({n})"


def run_backup(
    plan: BackupPlan, backups_dir: Path, description: str, *,
    progress: ProgressCallback = null_progress, cancel: CancelToken | None = None,
) -> BackupResult:
    cancel = cancel or CancelToken()
    backups_dir.mkdir(parents=True, exist_ok=True)
    avail = free_space(backups_dir)
    if avail < plan.total_bytes + 64 * 1024 * 1024:
        raise InsufficientSpaceError(plan.total_bytes, avail, "the backup")
    when = time.localtime()
    folder = _new_folder(backups_dir, backup_folder_name(plan.card, when))
    stamp = time.strftime("%Y-%m-%d_%H.%M.%S", when)
    info = (f"Date: {stamp}\r\nSource: {plan.card.state.value} "
            f"{plan.card.version or '(unknown version)'}\r\nDescription:\r\n{description}\r\n")
    (folder / f"Backupinfo_{stamp}.txt").write_text(info, encoding="utf-8")

    report = execute_copy(plan.items, folder, policy=ConflictPolicy.SKIP, compute_hashes=True,
                          fsync=False, progress=progress, cancel=cancel, label="Backing up")
    report.skipped = plan.skipped + report.skipped
    if plan.add_fbneo_cheats and not report.cancelled:
        try:
            _add_cheats(folder / "BIOS/fbneo/cheats")
        except (OSError, zipfile.BadZipFile) as exc:
            report.failed.append(("BIOS/fbneo/cheats/cheat.dat", str(exc)))
    manifest = {
        "format": 1,
        "created": stamp,
        "source_state": plan.card.state.value,
        "source_version": plan.card.version,
        "categories": [c.value for c in plan.categories],
        "complete": report.ok,
        "files": {rel: {"sha256": h} for rel, h in report.hashes.items()},
        "failed": report.failed,
        "skipped": report.skipped,
    }
    (folder / MANIFEST).write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    progress(Progress(f"Backup finished: {report.summary()}", 1, 1))
    return BackupResult(folder, report)


def _add_cheats(dest: Path) -> None:
    """Upstream replaces stock's thousands of FBNeo .ini cheats by the single cheat.dat pack."""
    dest.mkdir(parents=True, exist_ok=True)
    with resources.as_file(resources.files("onion_desktop.resources").joinpath("fbneo_cheat.zip")) as z, \
            zipfile.ZipFile(z) as zf, zf.open("cheat.dat") as src, open(dest / "cheat.dat", "wb") as out:
        while chunk := src.read(1024 * 1024):
            out.write(chunk)


def is_stock_card(card: CardInfo) -> bool:
    return card.state is CardState.STOCK
