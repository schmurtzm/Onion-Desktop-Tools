"""Onion package manager data (``App/PackageManager/data/{Emu,RApp,App}``).

Layout: ``data/<Type>/<Package name>/<Type>/<folder>`` (+ optional ``Roms/<system>``).
* Installed  : ``<card>/<Type>/<folder>`` exists (upstream ODT rule).
* ROMs present: not installed but ``<card>/Roms/<system>`` contains entries.
* Install    : merge the package tree into the card root (upstream ``Copy-Item -Recurse -Force``)
               but never overwrite existing files under ``Roms/``.
* Uninstall  : Onion's own package-manager semantics — delete only files that also exist in the
               package data, then empty folders; never touch ``Roms/``. User files survive.
Package ``install.sh``/``uninstall.sh`` scripts are device-side and are not executed here.
"""

from __future__ import annotations

import enum
import os
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from ..core.copier import ConflictPolicy, CopyItem, CopyReport, execute_copy
from ..core.exceptions import OdtError, UnsafePathError
from ..core.progress import CancelToken, ProgressCallback, null_progress
from ..core.safe_fs import safe_join, walk_files

PACK_TYPES = ("Emu", "RApp", "App")
DATA_DIR = Path("App/PackageManager/data")


class PackageStatus(enum.Enum):
    INSTALLED = "installed"
    ROMS_PRESENT = "roms_present"
    NOT_INSTALLED = "not_installed"


@dataclass(frozen=True)
class Package:
    name: str
    pack_type: str
    folder: str
    rom_folder: str
    status: PackageStatus
    data_path: Path
    has_device_script: bool

    @property
    def key(self) -> str:
        return f"{self.pack_type}/{self.name}/{self.folder}"


@dataclass
class PackageOpReport:
    package: str
    copy: CopyReport = field(default_factory=CopyReport)
    removed: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.copy.ok and not self.failed


def _subdirs(p: Path) -> list[str]:
    try:
        return sorted(
            e.name for e in os.scandir(p) if e.is_dir(follow_symlinks=False)
        )
    except OSError:
        return []


def _has_entries(p: Path) -> bool:
    try:
        with os.scandir(p) as it:
            return any(True for _ in it)
    except OSError:
        return False


def scan_packages(card_root: Path) -> list[Package]:
    data_root = card_root / DATA_DIR
    if not data_root.is_dir() or data_root.is_symlink():
        return []
    out: list[Package] = []
    for pack_type in PACK_TYPES:
        type_dir = data_root / pack_type
        for name in _subdirs(type_dir):
            pack_dir = type_dir / name
            roms_dir = pack_dir / "Roms"
            rom_folders = _subdirs(roms_dir) if roms_dir.is_dir() else []
            rom_folder = rom_folders[-1] if rom_folders else ""
            for folder in _subdirs(pack_dir / pack_type):
                if not rom_folders and folder == "romscripts":
                    continue
                content = pack_dir / pack_type / folder
                device_script = (content / "install.sh").is_file() or (content / "uninstall.sh").is_file()
                installed = (card_root / pack_type / folder).is_dir()
                if installed:
                    status = PackageStatus.INSTALLED
                elif rom_folder and _has_entries(card_root / "Roms" / rom_folder):
                    status = PackageStatus.ROMS_PRESENT
                else:
                    status = PackageStatus.NOT_INSTALLED
                out.append(Package(name, pack_type, folder, rom_folder, status, pack_dir, device_script))
    return out


def _package_files(pkg: Package) -> list[CopyItem]:
    return [
        CopyItem(e.path, e.rel, e.size, e.mtime) for e in walk_files(pkg.data_path)
    ]


def install_package(
    card_root: Path, pkg: Package, *, progress: ProgressCallback = null_progress,
    cancel: CancelToken | None = None,
) -> PackageOpReport:
    rep = PackageOpReport(pkg.name)
    items = _package_files(pkg)
    roms = [i for i in items if i.dst_rel.parts[:1] == ("Roms",)]
    others = [i for i in items if i.dst_rel.parts[:1] != ("Roms",)]
    # Create package ROM folders (often empty) even when they contain no files.
    roms_src = pkg.data_path / "Roms"
    if roms_src.is_dir():
        for sub in _subdirs(roms_src):
            try:
                safe_join(card_root, PurePosixPath("Roms", sub)).mkdir(parents=True, exist_ok=True)
            except (OSError, UnsafePathError) as exc:
                rep.failed.append((f"Roms/{sub}", str(exc)))
    rep.copy.merge(execute_copy(others, card_root, policy=ConflictPolicy.OVERWRITE, fat_target=True,
                                progress=progress, cancel=cancel, label=f"Installing {pkg.name}"))
    rep.copy.merge(execute_copy(roms, card_root, policy=ConflictPolicy.SKIP, fat_target=True,
                                progress=progress, cancel=cancel, label=f"Installing {pkg.name}"))
    return rep


def uninstall_package(card_root: Path, pkg: Package) -> PackageOpReport:
    rep = PackageOpReport(pkg.name)
    dirs: set[PurePosixPath] = set()
    for item in _package_files(pkg):
        if item.dst_rel.parts[:1] == ("Roms",):
            continue
        try:
            target = safe_join(card_root, item.dst_rel)
        except UnsafePathError as exc:
            rep.failed.append((str(item.dst_rel), exc.message))
            continue
        parent = item.dst_rel.parent
        while str(parent) not in (".", ""):
            dirs.add(parent)
            parent = parent.parent
        if target.is_file():
            try:
                target.unlink()
                rep.removed.append(str(item.dst_rel))
            except OSError as exc:
                rep.failed.append((str(item.dst_rel), exc.strerror or str(exc)))
    # Remove now-empty folders, deepest first, but never top-level type folders or Roms.
    for d in sorted(dirs, key=lambda p: len(p.parts), reverse=True):
        if len(d.parts) < 2:
            continue
        try:
            path = safe_join(card_root, d)
        except UnsafePathError:
            continue
        if path.is_dir():
            try:
                path.rmdir()
            except OSError:
                if d.parts[:2] == (pkg.pack_type, pkg.folder):
                    rep.kept.append(str(d))
    return rep


def check_card_has_package_manager(card_root: Path) -> None:
    if not (card_root / DATA_DIR).is_dir():
        raise OdtError(
            "Onion's package data (App/PackageManager/data) was not found on this card.",
            hint="Install Onion OS and boot it once on the console first.",
        )
