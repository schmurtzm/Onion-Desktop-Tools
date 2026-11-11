"""Device enumeration, protection classification and guarded destructive operations.

Rules enforced here (and only here) for any operation that modifies a device:

1. The caller passes the ``DiskIdentity`` the user confirmed. Immediately before *each*
   privileged step the device list is re-read and the identity compared (TOCTOU guard).
2. The disk must be eligible (``eligibility_problems`` empty): not hosting the running
   system, removable/hot-pluggable, writable, at most 2 TiB, not eMMC.
3. Only UDisks2 (Polkit-authorised) performs modifications; without it we fail closed.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any, Protocol

from ..core.exceptions import (
    BackendUnavailableError,
    DeviceChangedError,
    DeviceError,
    ProtectedDeviceError,
)
from ..core.models import Disk, DiskIdentity, Partition
from ..core.progress import Progress, ProgressCallback, null_progress
from .sysprobe import SysPaths, system_disks

log = logging.getLogger(__name__)

MAX_SD_SIZE = 2 * 1024**4  # SDXC maximum
REMOVABLE_BUSES = {"usb", "sdio", "mmc", "ieee1394", "firewire"}
FAT_LABEL = "ONION"


class Backend(Protocol):
    name: str
    can_modify: bool

    def list_disks(self) -> list[Disk]: ...


def eligibility_problems(disk: Disk, system: dict[str, list[str]]) -> list[str]:
    """Reasons a disk must never be offered for destructive operations."""
    problems = list(system.get(disk.kernel_name, []))
    for p in disk.partitions:
        for mp in p.mount_points:
            if mp in ("/", "/boot", "/boot/efi", "/efi", "/home", "/usr", "/var") or mp.startswith(("/usr/", "/var/")):
                problems.append(f"partition {p.device} is mounted at {mp}")
    if disk.media_type == "MMC" or disk.kernel_name.endswith(("boot0", "boot1", "rpmb")):
        problems.append("internal eMMC storage")
    if not (disk.removable or disk.hotplug or disk.bus in REMOVABLE_BUSES or disk.media_type == "SD"):
        problems.append("not a removable or hot-pluggable device")
    if disk.read_only:
        problems.append("device is read-only (check the SD card's lock switch)")
    if disk.size <= 0:
        problems.append("no medium / zero size")
    elif disk.size > MAX_SD_SIZE:
        problems.append("larger than 2 TB (not an SD card)")
    # de-duplicate, keep order
    return list(dict.fromkeys(problems))


def is_candidate_sd(disk: Disk) -> bool:
    """Heuristic for display ordering — never used as a safety decision on its own."""
    return not disk.protected_reasons and (disk.media_type == "SD" or disk.bus in ("usb", "sdio"))


@dataclass(frozen=True)
class FormatResult:
    disk: Disk
    partition: Partition
    mount_point: str | None


class DiskManager:
    def __init__(
        self,
        backend: Backend,
        system_probe: Callable[[], dict[str, list[str]]] | None = None,
    ) -> None:
        self.backend = backend
        self._system_probe = system_probe or (lambda: system_disks(SysPaths()))

    @property
    def can_modify(self) -> bool:
        return bool(getattr(self.backend, "can_modify", False))

    # -- read-only ------------------------------------------------------------------------
    def list_disks(self) -> list[Disk]:
        system = self._system_probe()
        disks = []
        for d in self.backend.list_disks():
            disks.append(replace(d, protected_reasons=tuple(eligibility_problems(d, system))))
        disks.sort(key=lambda d: (bool(d.protected_reasons), d.device))
        return disks

    def removable_disks(self) -> list[Disk]:
        return [d for d in self.list_disks() if not d.protected_reasons]

    def find(self, identity: DiskIdentity) -> Disk:
        """Re-enumerate and return the disk matching *identity* exactly, else raise."""
        matches = [d for d in self.list_disks() if d.device == identity.device]
        if not matches:
            raise DeviceChangedError(f"{identity.device} is no longer present. Was the card removed?")
        d = matches[0]
        cur = d.identity
        diffs = [f for f in ("size", "serial", "model", "drive_id") if getattr(cur, f) != getattr(identity, f)]
        if diffs:
            raise DeviceChangedError(
                f"{identity.device} is not the same device you confirmed (changed: {', '.join(diffs)}).",
                hint="Re-select the card and confirm again.",
            )
        return d

    def _require_eligible(self, identity: DiskIdentity) -> Disk:
        d = self.find(identity)
        if d.protected_reasons:
            raise ProtectedDeviceError(
                f"Refusing to modify {d.device}: " + "; ".join(d.protected_reasons)
            )
        return d

    def _client(self) -> Any:
        if not self.can_modify:
            raise BackendUnavailableError(
                "Modifying disks requires the UDisks2 service, which is not available.",
                hint="Install and start 'udisks2' (it is standard on GNOME and KDE desktops).",
            )
        return self.backend

    # -- non-destructive operations -------------------------------------------------------
    def mount(self, partition: Partition) -> str:
        client = self._client()
        if partition.mounted:
            return partition.mount_points[0]
        return str(client.mount(partition.object_path))

    def unmount(self, partition: Partition) -> None:
        self._client().unmount(partition.object_path)

    def eject(self, identity: DiskIdentity) -> None:
        """Unmount all partitions and power off the drive (upstream: RemoveDrive.exe)."""
        client = self._client()
        d = self.find(identity)
        for p in d.mounted_partitions():
            client.unmount(p.object_path)
        try:
            client.power_off(d.drive_object_path)
        except DeviceError:
            client.eject(d.drive_object_path)

    def check_filesystem(self, partition: Partition, repair: bool = False) -> bool:
        """Equivalent of upstream ``chkdsk /F /X`` (UDisks2 Check/Repair → fsck.vfat)."""
        client = self._client()
        if partition.mounted:
            client.unmount(partition.object_path)
        return bool(client.repair(partition.object_path) if repair else client.check(partition.object_path))

    # -- destructive ----------------------------------------------------------------------
    def format_fat32(
        self,
        identity: DiskIdentity,
        *,
        confirmed_device_text: str,
        mount_after: bool = True,
        progress: ProgressCallback = null_progress,
    ) -> FormatResult:
        """Erase the whole disk: new MBR table + one FAT32 partition labelled ONION."""
        if confirmed_device_text.strip() != identity.device:
            raise ProtectedDeviceError("The typed device name does not match the selected device.")
        client = self._client()
        progress(Progress("Verifying the selected device…"))
        d = self._require_eligible(identity)
        log.info("Formatting %s (%s, %d bytes) as FAT32", d.device, d.display_name, d.size)

        for p in d.mounted_partitions():
            progress(Progress(f"Unmounting {p.device}…"))
            client.unmount(p.object_path)

        d = self._require_eligible(identity)
        if d.mounted_partitions():
            raise DeviceError(f"{d.device} still has mounted partitions; close programs using it.")
        progress(Progress("Creating a new partition table…"))
        client.create_dos_table(d.object_path)

        self._require_eligible(identity)
        progress(Progress("Creating the FAT32 partition…"))
        try:
            mkfs_arg = client.version() >= (2, 10)
        except DeviceError:
            mkfs_arg = False
        part_path = client.create_fat32_partition(d.object_path, FAT_LABEL, mkfs_arg)

        progress(Progress("Verifying the new file system…"))
        d = self.find(identity)
        part = next((p for p in d.partitions if p.object_path == part_path), None)
        if part is None and len(d.partitions) == 1:
            part = d.partitions[0]
        if part is None:
            raise DeviceError("The new partition could not be found after formatting.")
        if part.fs_type != "vfat" or part.fs_version.upper() != "FAT32":
            raise DeviceError(
                f"Formatting finished but the result is {part.fs_type or 'unknown'} "
                f"{part.fs_version}, not FAT32.",
                hint="The card may be too small for FAT32 or the formatting tool chose another FAT type.",
            )
        mp = None
        if mount_after:
            progress(Progress("Mounting the card…"))
            try:
                mp = self.mount(part)
            except DeviceError as exc:
                log.warning("Mount after format failed: %s", exc)
        progress(Progress("Format complete", 1, 1))
        return FormatResult(d, part, mp)


def create_default_manager() -> DiskManager:
    """UDisks2 if reachable, else read-only lsblk."""
    from .lsblk_backend import LsblkBackend
    from .udisks2 import probe

    client = probe()
    if client is not None:
        return DiskManager(client)
    log.warning("UDisks2 not available; using read-only lsblk backend")
    return DiskManager(LsblkBackend())
