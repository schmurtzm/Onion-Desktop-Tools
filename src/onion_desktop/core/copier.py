"""Planned file copy engine used by backup, restore and the package manager.

A copy is two steps: a *plan* (list of CopyItem, computed without writing anything — used for
space checks and conflict prompts) and an *execution* that reports exactly which files were
copied, skipped and failed. Nothing is ever reported as success if a file failed.
"""

from __future__ import annotations

import enum
import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from .exceptions import OdtError, OperationCancelled, UnsafePathError
from .progress import CancelToken, Progress, ProgressCallback, null_progress
from .safe_fs import (
    FAT32_MAX_FILE_SIZE,
    check_fat_name,
    fsync_dir,
    open_new_file,
    safe_join,
)

CHUNK = 1024 * 1024
TMP_PREFIX = ".odt-tmp-"


class ConflictPolicy(enum.Enum):
    SKIP = "skip"  # keep the existing destination file
    OVERWRITE = "overwrite"  # replace differing destination files


@dataclass(frozen=True)
class CopyItem:
    src: Path
    dst_rel: PurePosixPath
    size: int
    mtime: float = 0.0


@dataclass
class CopyReport:
    copied: list[str] = field(default_factory=list)
    identical: list[str] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    bytes_copied: int = 0
    hashes: dict[str, str] = field(default_factory=dict)
    cancelled: bool = False

    @property
    def ok(self) -> bool:
        return not self.failed and not self.cancelled

    def merge(self, other: CopyReport) -> None:
        self.copied += other.copied
        self.identical += other.identical
        self.skipped += other.skipped
        self.failed += other.failed
        self.bytes_copied += other.bytes_copied
        self.hashes.update(other.hashes)
        self.cancelled = self.cancelled or other.cancelled

    def summary(self) -> str:
        parts = [f"{len(self.copied)} copied"]
        if self.identical:
            parts.append(f"{len(self.identical)} already identical")
        if self.skipped:
            parts.append(f"{len(self.skipped)} skipped")
        if self.failed:
            parts.append(f"{len(self.failed)} FAILED")
        if self.cancelled:
            parts.append("cancelled")
        return ", ".join(parts)


def dedupe(items: list[CopyItem]) -> list[CopyItem]:
    seen: set[str] = set()
    out: list[CopyItem] = []
    for it in items:
        key = str(it.dst_rel).lower()
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out


def _same_file(item: CopyItem, dst: Path) -> bool:
    try:
        st = dst.stat()
    except OSError:
        return False
    # FAT stores mtime with 2 s granularity.
    return st.st_size == item.size and abs(st.st_mtime - item.mtime) <= 2.0


def find_conflicts(items: list[CopyItem], dest_root: Path) -> list[CopyItem]:
    """Items whose destination exists and differs (size or mtime)."""
    conflicts: list[CopyItem] = []
    for it in items:
        try:
            dst = safe_join(dest_root, it.dst_rel)
        except UnsafePathError:
            continue
        if dst.exists() and not _same_file(it, dst):
            conflicts.append(it)
    return conflicts


def bytes_needed(items: list[CopyItem], dest_root: Path, policy: ConflictPolicy) -> int:
    """Upper bound of additional bytes needed on the destination."""
    need = 0
    for it in items:
        try:
            dst = safe_join(dest_root, it.dst_rel)
            existing = dst.stat().st_size if dst.is_file() else None
        except (UnsafePathError, OSError):
            existing = None
        if existing is None:
            need += it.size
        elif policy is ConflictPolicy.OVERWRITE:
            need += max(0, it.size - existing) + it.size  # temp copy exists during replace
    return need


def execute_copy(
    items: list[CopyItem],
    dest_root: Path,
    *,
    policy: ConflictPolicy = ConflictPolicy.SKIP,
    fat_target: bool = False,
    compute_hashes: bool = False,
    fsync: bool = True,
    progress: ProgressCallback = null_progress,
    cancel: CancelToken | None = None,
    label: str = "Copying",
) -> CopyReport:
    cancel = cancel or CancelToken()
    report = CopyReport()
    total = sum(i.size for i in items) or 1
    done = 0
    dirs: set[Path] = set()
    try:
        for idx, item in enumerate(items):
            cancel.raise_if_cancelled()
            rel = str(item.dst_rel)
            progress(Progress(f"{label}: {rel} ({idx + 1}/{len(items)})", done, total))
            try:
                if fat_target:
                    reason = check_fat_name(item.dst_rel)
                    if reason:
                        report.failed.append((rel, reason))
                        continue
                    if item.size > FAT32_MAX_FILE_SIZE:
                        report.failed.append((rel, "file is larger than the FAT32 limit of 4 GB"))
                        continue
                dst = safe_join(dest_root, item.dst_rel)
                if dst.exists():
                    if dst.is_dir():
                        report.failed.append((rel, "a folder exists where a file is expected"))
                        continue
                    if _same_file(item, dst):
                        report.identical.append(rel)
                        done += item.size
                        continue
                    if policy is ConflictPolicy.SKIP:
                        report.skipped.append((rel, "destination exists and differs (kept)"))
                        done += item.size
                        continue
                dst.parent.mkdir(parents=True, exist_ok=True)
                safe_join(dest_root, item.dst_rel)  # re-validate after mkdir
                digest = _copy_one(item, dst, cancel, compute_hashes, fsync)
            except OperationCancelled:
                raise
            except UnsafePathError as exc:
                report.failed.append((rel, exc.message))
                continue
            except (OSError, OdtError) as exc:
                msg = exc.message if isinstance(exc, OdtError) else (exc.strerror or str(exc))
                report.failed.append((rel, msg))
                continue
            dirs.add(dst.parent)
            report.copied.append(rel)
            report.bytes_copied += item.size
            if digest:
                report.hashes[rel] = digest
            done += item.size
    except OperationCancelled:
        report.cancelled = True
    if fsync:
        for d in dirs:
            fsync_dir(d)
    progress(Progress(f"{label}: finished ({report.summary()})", total, total))
    return report


def _copy_one(item: CopyItem, dst: Path, cancel: CancelToken, want_hash: bool, fsync: bool) -> str:
    tmp = dst.with_name(f"{TMP_PREFIX}{dst.name}")
    h = hashlib.sha256() if want_hash else None
    copied = 0
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(item.src, flags)
    except OSError as exc:
        raise OdtError(f"cannot open source: {exc.strerror or exc}") from exc
    try:
        with os.fdopen(fd, "rb") as src, os.fdopen(open_new_file(tmp), "wb") as out:
            while True:
                cancel.raise_if_cancelled()
                chunk = src.read(CHUNK)
                if not chunk:
                    break
                out.write(chunk)
                copied += len(chunk)
                if h is not None:
                    h.update(chunk)
            out.flush()
            if fsync:
                os.fsync(out.fileno())
        if copied != item.size:
            raise OdtError("source changed size during copy")
        os.replace(tmp, dst)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    if item.mtime > 0:
        try:
            os.utime(dst, (item.mtime, item.mtime))
        except OSError:
            pass
    return h.hexdigest() if h is not None else ""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()
