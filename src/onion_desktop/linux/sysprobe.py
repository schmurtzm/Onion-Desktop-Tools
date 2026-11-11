"""Find the physical disks that host the running system (read-only sysfs/procfs probing).

A disk is a *system disk* if it (or a device stacked on it: LVM, dm-crypt, MD RAID) backs
a critical mount point or an active swap area.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

CRITICAL_MOUNTS = ("/", "/boot", "/boot/efi", "/efi", "/home", "/usr", "/var", "/opt", "/srv",
                   "/nix", "/snap", "/tmp")


@dataclass
class SysPaths:
    sys_root: Path = Path("/sys")
    proc_root: Path = Path("/proc")
    dev_root: Path = Path("/dev")


def _unescape(field: str) -> str:
    return field.replace("\\040", " ").replace("\\011", "\t").replace("\\012", "\n").replace("\\134", "\\")


def _majmin_kernel_name(majmin: str, paths: SysPaths) -> str | None:
    link = paths.sys_root / "dev/block" / majmin
    try:
        return os.path.basename(os.path.realpath(link))
    except OSError:
        return None


def _parent_disk(kname: str, paths: SysPaths) -> str:
    """Whole-disk name for a partition (sda1 → sda); disks map to themselves."""
    cls = paths.sys_root / "class/block" / kname
    if (cls / "partition").exists():
        try:
            return os.path.basename(os.path.dirname(os.path.realpath(cls)))
        except OSError:
            return kname
    return kname


def _physical_disks(kname: str, paths: SysPaths, seen: set[str] | None = None) -> set[str]:
    seen = seen or set()
    if kname in seen:
        return set()
    seen.add(kname)
    disk = _parent_disk(kname, paths)
    slaves_dir = paths.sys_root / "class/block" / kname / "slaves"
    if not slaves_dir.is_dir():
        slaves_dir = paths.sys_root / "class/block" / disk / "slaves"
    try:
        slaves = os.listdir(slaves_dir) if slaves_dir.is_dir() else []
    except OSError:
        slaves = []
    if not slaves:
        return {disk}
    out: set[str] = set()
    for s in slaves:
        out |= _physical_disks(s, paths, seen)
    return out


def _mount_sources(paths: SysPaths) -> list[tuple[str, str, str]]:
    """(mount_point, major:minor, source) from mountinfo."""
    out: list[tuple[str, str, str]] = []
    try:
        text = (paths.proc_root / "self/mountinfo").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 10 or "-" not in parts:
            continue
        sep = parts.index("-")
        out.append((_unescape(parts[4]), parts[2], parts[sep + 2] if len(parts) > sep + 2 else ""))
    return out


def system_disks(paths: SysPaths | None = None) -> dict[str, list[str]]:
    """Map kernel disk name → list of reasons it is a system disk."""
    paths = paths or SysPaths()
    reasons: dict[str, list[str]] = {}

    def add(kname: str | None, why: str) -> None:
        if not kname:
            return
        for disk in _physical_disks(kname, paths):
            reasons.setdefault(disk, [])
            if why not in reasons[disk]:
                reasons[disk].append(why)

    for mnt, majmin, source in _mount_sources(paths):
        if mnt in CRITICAL_MOUNTS:
            kname = None
            if not majmin.startswith("0:"):
                kname = _majmin_kernel_name(majmin, paths)
            elif source.startswith("/dev/"):
                # btrfs/zfs report anonymous dev numbers; fall back to the source device.
                kname = os.path.basename(os.path.realpath(source))
            add(kname, f"hosts system mount point {mnt}")
    try:
        swaps = (paths.proc_root / "swaps").read_text(encoding="utf-8").splitlines()[1:]
    except OSError:
        swaps = []
    for line in swaps:
        dev = line.split()[0] if line.split() else ""
        if dev.startswith("/dev/"):
            add(os.path.basename(os.path.realpath(dev)), "hosts active swap")
    return reasons


def mmc_media_type(kname: str, paths: SysPaths | None = None) -> str:
    """'SD' for SD cards, 'MMC' for soldered eMMC, '' if not an MMC device."""
    paths = paths or SysPaths()
    try:
        return (paths.sys_root / "block" / kname / "device/type").read_text().strip()
    except OSError:
        return ""
