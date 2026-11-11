"""Path-safety helpers. Card contents and archive names are untrusted input."""

from __future__ import annotations

import os
import stat
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .exceptions import UnsafePathError

# Characters that FAT32 cannot store; used to give a clear error before writing.
FAT_FORBIDDEN_CHARS = set('<>:"\\|?*') | {chr(c) for c in range(0x20)}
FAT32_MAX_FILE_SIZE = 4 * 1024**3 - 1


def validate_relative(rel: str | PurePosixPath) -> PurePosixPath:
    """Validate a POSIX relative path coming from an untrusted source.

    Rejects absolute paths, Windows drive letters, backslashes, NUL bytes, empty
    components and any ``..`` component.
    """
    text = str(rel)
    if not text or "\x00" in text:
        raise UnsafePathError(f"Invalid path: {text!r}")
    if "\\" in text:
        raise UnsafePathError(f"Backslash in path is not allowed: {text!r}")
    if text.startswith("/") or (len(text) >= 2 and text[1] == ":"):
        raise UnsafePathError(f"Absolute path is not allowed: {text!r}")
    parts = [p for p in text.split("/") if p not in ("", ".")]
    if not parts:
        raise UnsafePathError(f"Empty path: {text!r}")
    if any(p == ".." for p in parts):
        raise UnsafePathError(f"Parent directory reference is not allowed: {text!r}")
    return PurePosixPath(*parts)


def safe_join(root: Path, rel: str | PurePosixPath) -> Path:
    """Join *rel* under *root*, refusing traversal and symlinked components.

    Existing components between *root* and the final path must not be symlinks, so a
    planted symlink on a card cannot redirect writes elsewhere.
    """
    clean = validate_relative(rel)
    root_resolved = root.resolve()
    current = root_resolved
    for part in clean.parts:
        current = current / part
        try:
            st = os.lstat(current)
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(st.st_mode):
            raise UnsafePathError(f"Refusing to follow symbolic link: {current}")
    final = root_resolved.joinpath(*clean.parts)
    if os.path.commonpath([str(root_resolved), str(final)]) != str(root_resolved):
        raise UnsafePathError(f"Path escapes target directory: {rel}")
    return final


@dataclass(frozen=True)
class WalkEntry:
    path: Path
    rel: PurePosixPath
    size: int
    mtime: float


def walk_files(
    root: Path,
    *,
    skip_dir: Callable[[PurePosixPath], bool] | None = None,
    on_skipped: Callable[[PurePosixPath, str], None] | None = None,
    max_depth: int | None = None,
) -> Iterator[WalkEntry]:
    """Yield regular files under *root* without following symlinks.

    Symlinks and special files are reported through *on_skipped*. ``max_depth=1`` lists only
    files directly in *root*.
    """
    if not root.is_dir() or root.is_symlink():
        return
    stack: list[tuple[Path, PurePosixPath, int]] = [(root, PurePosixPath(), 1)]
    while stack:
        directory, rel_dir, depth = stack.pop()
        try:
            with os.scandir(directory) as it:
                entries = sorted(it, key=lambda e: e.name)
        except OSError as exc:
            if on_skipped:
                on_skipped(rel_dir, f"cannot read directory: {exc.strerror or exc}")
            continue
        subdirs: list[tuple[Path, PurePosixPath, int]] = []
        for entry in entries:
            rel = rel_dir / entry.name
            try:
                st = entry.stat(follow_symlinks=False)
            except OSError as exc:
                if on_skipped:
                    on_skipped(rel, f"cannot stat: {exc.strerror or exc}")
                continue
            if stat.S_ISLNK(st.st_mode):
                if on_skipped:
                    on_skipped(rel, "symbolic link (not followed)")
                continue
            if stat.S_ISDIR(st.st_mode):
                if max_depth is not None and depth >= max_depth:
                    continue
                if skip_dir is not None and skip_dir(rel):
                    continue
                subdirs.append((Path(entry.path), rel, depth + 1))
            elif stat.S_ISREG(st.st_mode):
                yield WalkEntry(Path(entry.path), rel, st.st_size, st.st_mtime)
            elif on_skipped:
                on_skipped(rel, "special file (not copied)")
        stack.extend(reversed(subdirs))


def free_space(path: Path) -> int:
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize


def total_space(path: Path) -> int:
    st = os.statvfs(path)
    return st.f_blocks * st.f_frsize


def _unescape_mount(field: str) -> str:
    return (
        field.replace("\\040", " ").replace("\\011", "\t").replace("\\012", "\n")
        .replace("\\134", "\\")
    )


def filesystem_type_of(path: Path, mounts_file: Path = Path("/proc/self/mounts")) -> str | None:
    """Return the filesystem type of the mount containing *path* (longest prefix match)."""
    try:
        target = str(path.resolve())
        text = mounts_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    best: tuple[int, str] | None = None
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 3:
            continue
        mnt = _unescape_mount(fields[1])
        if target == mnt or target.startswith(mnt.rstrip("/") + "/") or mnt == "/":
            if best is None or len(mnt) > best[0]:
                best = (len(mnt), fields[2])
    return best[1] if best else None


def is_fat_filesystem(fs_type: str | None) -> bool:
    return fs_type in {"vfat", "msdos", "fat"}


def check_fat_name(rel: PurePosixPath) -> str | None:
    """Return a reason string if *rel* cannot be stored on FAT32, else None."""
    for part in rel.parts:
        bad = sorted({c for c in part if c in FAT_FORBIDDEN_CHARS})
        if bad:
            return f"name contains characters FAT32 cannot store: {''.join(bad)!r}"
        if part.endswith((" ", ".")) and part not in (".", ".."):
            return "name ends with a space or dot (not allowed on FAT32)"
    return None


def open_new_file(path: Path, mode: int = 0o644) -> int:
    """Create *path* exclusively without following symlinks; returns an fd.

    A leftover entry at *path* (e.g. a temp file planted on an untrusted card, possibly a symlink)
    is unlinked first — unlinking removes the link itself, never its target.
    """
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        pass
    else:
        if stat.S_ISDIR(st.st_mode):
            raise UnsafePathError(f"Unexpected folder at temporary path {path}")
        os.unlink(path)
    return os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), mode)


def fsync_dir(path: Path) -> None:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def drop_cache(fd: int) -> None:
    """Ask the kernel to drop cached pages so a verify pass re-reads the medium."""
    if hasattr(os, "posix_fadvise"):
        try:
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        except OSError:
            pass
