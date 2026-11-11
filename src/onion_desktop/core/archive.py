"""Validated ZIP extraction.

All members are validated before anything is written. Files are streamed to a temporary
name in the destination directory, fsynced and atomically renamed over any existing file
(the equivalent of upstream's ``7z x -aoa``). A verification pass re-reads every written
file from the medium and compares its CRC-32 with the archive.
"""

from __future__ import annotations

import os
import stat
import time
import zipfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from .exceptions import (
    ArchiveError,
    IntegrityError,
    OdtError,
    OperationCancelled,
    UnsafePathError,
)
from .progress import CancelToken, Progress, ProgressCallback, null_progress
from .safe_fs import (
    FAT32_MAX_FILE_SIZE,
    check_fat_name,
    drop_cache,
    fsync_dir,
    open_new_file,
    safe_join,
    validate_relative,
)

CHUNK = 1024 * 1024
MAX_COMPRESSION_RATIO = 200  # per member; generous for real data, stops crafted bombs
MAX_MEMBERS = 200_000
TMP_PREFIX = ".odt-tmp-"


@dataclass(frozen=True)
class ArchiveMember:
    info: zipfile.ZipInfo
    rel: PurePosixPath
    is_dir: bool


@dataclass
class ArchiveManifest:
    members: list[ArchiveMember]
    total_size: int
    file_count: int

    def names(self) -> set[str]:
        return {str(m.rel) for m in self.members}


@dataclass
class ExtractReport:
    written: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    verified: bool = False
    bytes_written: int = 0

    @property
    def ok(self) -> bool:
        return not self.failed


def _member_mode(info: zipfile.ZipInfo) -> int:
    return (info.external_attr >> 16) & 0xFFFF


def inspect_zip(path: Path, *, fat_target: bool = True) -> ArchiveManifest:
    """Open and validate every member of *path*; raise ArchiveError/UnsafePathError if unsafe."""
    try:
        zf = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as exc:
        raise ArchiveError(f"'{path.name}' is not a valid ZIP archive ({exc}).") from exc
    with zf:
        infos = zf.infolist()
        if len(infos) > MAX_MEMBERS:
            raise ArchiveError(f"Archive has too many entries ({len(infos)}).")
        members: list[ArchiveMember] = []
        seen: dict[str, bool] = {}
        total = 0
        files = 0
        for info in infos:
            name = info.filename
            if info.flag_bits & 0x1:
                raise ArchiveError(f"Encrypted entries are not supported: {name!r}")
            mode = _member_mode(info)
            if mode and stat.S_ISLNK(mode):
                raise UnsafePathError(f"Archive contains a symbolic link: {name!r}")
            if mode and stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise UnsafePathError(f"Archive contains a special file: {name!r}")
            is_dir = name.endswith("/") or (bool(mode) and stat.S_ISDIR(mode))
            rel = validate_relative(name.rstrip("/") if is_dir else name)
            key = str(rel).lower()  # FAT is case-insensitive
            if key in seen and seen[key] != is_dir:
                raise ArchiveError(f"Archive entry conflicts with another entry: {name!r}")
            seen[key] = is_dir
            if fat_target:
                reason = check_fat_name(rel)
                if reason:
                    raise ArchiveError(f"Entry {name!r} cannot be written to FAT32: {reason}")
            if not is_dir:
                if info.file_size > FAT32_MAX_FILE_SIZE and fat_target:
                    raise ArchiveError(f"Entry {name!r} exceeds the FAT32 4 GB file size limit.")
                if (
                    info.compress_size > 0
                    and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO
                    and info.file_size > 50 * CHUNK
                ):
                    raise ArchiveError(f"Suspicious compression ratio for {name!r}.")
                total += info.file_size
                files += 1
            members.append(ArchiveMember(info, rel, is_dir))
        # A file entry must not also be used as a parent directory of another entry.
        file_keys = {k for k, d in seen.items() if not d}
        for key in seen:
            parent = PurePosixPath(key).parent
            while str(parent) not in (".", ""):
                if str(parent) in file_keys:
                    raise ArchiveError(f"Archive uses file '{parent}' as a directory.")
                parent = parent.parent
    return ArchiveManifest(members, total, files)


def _crc_of_file(path: Path) -> int:
    crc = 0
    fd = os.open(path, os.O_RDONLY)
    try:
        drop_cache(fd)
        while True:
            chunk = os.read(fd, CHUNK)
            if not chunk:
                break
            crc = zlib.crc32(chunk, crc)
    finally:
        os.close(fd)
    return crc & 0xFFFFFFFF


def extract_zip(
    archive: Path,
    dest: Path,
    *,
    manifest: ArchiveManifest | None = None,
    progress: ProgressCallback = null_progress,
    cancel: CancelToken | None = None,
    verify: bool = True,
    fat_target: bool = True,
) -> ExtractReport:
    """Extract *archive* into *dest*, overwriting existing files. See module docstring."""
    cancel = cancel or CancelToken()
    manifest = manifest or inspect_zip(archive, fat_target=fat_target)
    report = ExtractReport()
    total = manifest.total_size or 1
    done = 0
    touched_dirs: set[Path] = set()
    with zipfile.ZipFile(archive) as zf:
        for member in manifest.members:
            cancel.raise_if_cancelled()
            target = safe_join(dest, member.rel)
            if member.is_dir:
                if target.exists() and not target.is_dir():
                    report.failed.append((str(member.rel), "a file exists where a folder is expected"))
                    continue
                target.mkdir(parents=True, exist_ok=True)
                continue
            progress(Progress(f"Extracting {member.rel}", done, total))
            parent = target.parent
            try:
                if parent.exists() and not parent.is_dir():
                    raise OdtError("a file exists where a folder is expected")
                parent.mkdir(parents=True, exist_ok=True)
                safe_join(dest, member.rel)  # re-check after mkdir (no symlink raced in)
                if target.is_dir():
                    raise OdtError("a folder exists where a file is expected")
                written = _extract_member(zf, member.info, target, cancel)
            except (UnsafePathError, OperationCancelled):
                raise
            except (OSError, OdtError, zipfile.BadZipFile) as exc:
                msg = exc.message if isinstance(exc, OdtError) else (getattr(exc, "strerror", None) or str(exc))
                report.failed.append((str(member.rel), msg))
                continue
            touched_dirs.add(parent)
            done += written
            report.bytes_written += written
            report.written.append(str(member.rel))
    for d in touched_dirs:
        fsync_dir(d)
    progress(Progress("Extraction finished", total, total))
    if verify and report.ok:
        verify_extraction(archive, dest, manifest, progress=progress, cancel=cancel)
        report.verified = True
    return report


def _extract_member(
    zf: zipfile.ZipFile, info: zipfile.ZipInfo, target: Path, cancel: CancelToken
) -> int:
    tmp = target.with_name(f"{TMP_PREFIX}{target.name}")
    written = 0
    try:
        with zf.open(info) as src, os.fdopen(open_new_file(tmp), "wb") as out:
            while True:
                cancel.raise_if_cancelled()
                chunk = src.read(CHUNK)
                if not chunk:
                    break
                written += len(chunk)
                if written > info.file_size:
                    raise IntegrityError(f"Entry {info.filename!r} is larger than declared.")
                out.write(chunk)
            out.flush()
            os.fsync(out.fileno())
        if written != info.file_size:
            raise IntegrityError(f"Entry {info.filename!r} is truncated.")
        os.replace(tmp, target)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    try:
        y, mo, d, h, mi, s = info.date_time
        ts = time.mktime((y, mo, d, h, mi, s, 0, 0, -1))
        os.utime(target, (ts, ts))
    except (OverflowError, ValueError, OSError):
        pass
    return written


def verify_extraction(
    archive: Path,
    dest: Path,
    manifest: ArchiveManifest,
    *,
    progress: ProgressCallback = null_progress,
    cancel: CancelToken | None = None,
) -> None:
    """Re-read every extracted file and compare size and CRC-32 with the archive."""
    cancel = cancel or CancelToken()
    files = [m for m in manifest.members if not m.is_dir]
    for i, member in enumerate(files):
        cancel.raise_if_cancelled()
        progress(Progress(f"Verifying {member.rel}", i, len(files)))
        target = safe_join(dest, member.rel)
        try:
            size = target.stat().st_size
        except OSError as exc:
            raise IntegrityError(f"Verification failed: {member.rel} is missing ({exc}).") from exc
        if size != member.info.file_size:
            raise IntegrityError(f"Verification failed: size mismatch for {member.rel}.")
        if _crc_of_file(target) != member.info.CRC:
            raise IntegrityError(f"Verification failed: checksum mismatch for {member.rel}.")
    progress(Progress("Verification finished", len(files), len(files)))


def cleanup_temp_files(root: Path) -> int:
    """Remove leftovers of interrupted extractions/copies. Returns count removed."""
    removed = 0
    for dirpath, _dirs, files in os.walk(root, followlinks=False):
        for f in files:
            if f.startswith(TMP_PREFIX):
                try:
                    os.unlink(os.path.join(dirpath, f))
                    removed += 1
                except OSError:
                    pass
    return removed
