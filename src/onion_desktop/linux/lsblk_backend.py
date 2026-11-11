"""Read-only device enumeration through ``lsblk -J`` (used when UDisks2 is unavailable)."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

from ..core.exceptions import BackendUnavailableError, HostToolMissingError
from ..core.models import Disk, Partition
from .sysprobe import SysPaths, mmc_media_type

COLUMNS = ("NAME,KNAME,PATH,TYPE,SIZE,MODEL,VENDOR,SERIAL,TRAN,RM,HOTPLUG,RO,FSTYPE,FSVER,"
           "LABEL,UUID,MOUNTPOINT,FSAVAIL,PTTYPE,PARTN")
EXCLUDED_TYPES = {"loop", "rom", "zram", "ram"}


def _run_lsblk() -> dict[str, Any]:
    exe = shutil.which("lsblk")
    if not exe:
        raise HostToolMissingError("lsblk", "util-linux")
    try:
        cp = subprocess.run([exe, "-J", "-b", "-o", COLUMNS], capture_output=True, text=True,
                            timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BackendUnavailableError(f"lsblk failed: {exc}") from exc
    if cp.returncode != 0:
        # Older util-linux lacks some columns: retry with a minimal set.
        cp = subprocess.run([exe, "-J", "-b", "-o",
                             "NAME,KNAME,TYPE,SIZE,MODEL,SERIAL,TRAN,RM,HOTPLUG,RO,FSTYPE,LABEL,UUID,MOUNTPOINT"],
                            capture_output=True, text=True, timeout=15, check=False)
        if cp.returncode != 0:
            raise BackendUnavailableError(f"lsblk failed: {cp.stderr.strip()}")
    try:
        data = json.loads(cp.stdout)
    except ValueError as exc:
        raise BackendUnavailableError("lsblk returned invalid JSON") from exc
    return data if isinstance(data, dict) else {}


def _b(v: Any) -> bool:
    return v in (True, 1, "1", "true")


def _i(v: Any) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _s(v: Any) -> str:
    return str(v).strip() if v not in (None, "") else ""


def parse_lsblk(data: dict[str, Any], paths: SysPaths | None = None) -> list[Disk]:
    disks: list[Disk] = []
    for dev in data.get("blockdevices", []) or []:
        if not isinstance(dev, dict) or dev.get("type") != "disk":
            continue
        kname = _s(dev.get("kname") or dev.get("name"))
        if any(kname.startswith(p) for p in ("loop", "zram", "ram", "sr", "fd")):
            continue
        parts = []
        for i, ch in enumerate(dev.get("children") or [], start=1):
            if not isinstance(ch, dict) or ch.get("type") != "part":
                continue
            mp = ch.get("mountpoint")
            mps = tuple(m for m in (ch.get("mountpoints") or ([mp] if mp else [])) if m)
            fsavail = ch.get("fsavail")
            parts.append(Partition(
                device=_s(ch.get("path")) or f"/dev/{_s(ch.get('kname') or ch.get('name'))}",
                number=_i(ch.get("partn")) or i,
                size=_i(ch.get("size")),
                fs_type=_s(ch.get("fstype")),
                fs_version=_s(ch.get("fsver")),
                label=_s(ch.get("label")),
                uuid=_s(ch.get("uuid")),
                mount_points=mps,
                free_bytes=_i(fsavail) if fsavail not in (None, "") else None,
            ))
        if not parts and _s(dev.get("fstype")):
            mp = dev.get("mountpoint")
            parts.append(Partition(
                device=_s(dev.get("path")) or f"/dev/{kname}", number=0, size=_i(dev.get("size")),
                fs_type=_s(dev.get("fstype")), fs_version=_s(dev.get("fsver")), label=_s(dev.get("label")),
                uuid=_s(dev.get("uuid")), mount_points=tuple(m for m in (dev.get("mountpoints") or [mp]) if m),
                free_bytes=_i(dev.get("fsavail")) if dev.get("fsavail") not in (None, "") else None,
            ))
        disks.append(Disk(
            device=_s(dev.get("path")) or f"/dev/{kname}",
            kernel_name=kname,
            size=_i(dev.get("size")),
            model=_s(dev.get("model")),
            vendor=_s(dev.get("vendor")),
            serial=_s(dev.get("serial")),
            bus=_s(dev.get("tran")) or ("sdio" if kname.startswith("mmcblk") else ""),
            removable=_b(dev.get("rm")),
            hotplug=_b(dev.get("hotplug")),
            read_only=_b(dev.get("ro")),
            partition_table=_s(dev.get("pttype")),
            fs_type=_s(dev.get("fstype")),
            partitions=tuple(parts),
            drive_id=f"lsblk:{kname}:{_s(dev.get('serial'))}",
            media_type=mmc_media_type(kname, paths) if kname.startswith("mmcblk") else "",
            backend="lsblk",
        ))
    return disks


class LsblkBackend:
    name = "lsblk"
    can_modify = False

    def __init__(self, paths: SysPaths | None = None) -> None:
        self.paths = paths

    def list_disks(self) -> list[Disk]:
        return parse_lsblk(_run_lsblk(), self.paths)
