"""Device data model shared by the disk backends and the GUI."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Partition:
    device: str  # /dev/sdb1
    number: int
    size: int
    fs_type: str = ""  # vfat, exfat, ext4 …
    fs_version: str = ""  # FAT32, FAT16 …
    label: str = ""
    uuid: str = ""
    mount_points: tuple[str, ...] = ()
    free_bytes: int | None = None
    object_path: str = ""  # UDisks2 block object

    @property
    def mounted(self) -> bool:
        return bool(self.mount_points)

    @property
    def mount_point(self) -> str | None:
        return self.mount_points[0] if self.mount_points else None

    @property
    def is_fat32(self) -> bool:
        return self.fs_type == "vfat" and self.fs_version.upper() == "FAT32"


@dataclass(frozen=True)
class DiskIdentity:
    """Facts the user implicitly confirmed; re-checked right before privileged actions."""

    device: str
    size: int
    serial: str
    model: str
    drive_id: str  # UDisks Drive.Id / object path or sysfs-derived id

    def describe(self) -> str:
        return f"{self.device} — {self.model or 'unknown model'} ({self.size} bytes, serial {self.serial or 'n/a'})"


@dataclass(frozen=True)
class Disk:
    device: str  # /dev/sdb, /dev/mmcblk0
    kernel_name: str  # sdb, mmcblk0
    size: int
    model: str = ""
    vendor: str = ""
    serial: str = ""
    bus: str = ""  # usb, sdio, ata, nvme …
    removable: bool = False
    hotplug: bool = False
    read_only: bool = False
    partition_table: str = ""  # dos, gpt, ""
    fs_type: str = ""  # filesystem directly on the whole disk (superfloppy)
    partitions: tuple[Partition, ...] = ()
    object_path: str = ""  # UDisks2 block object of the whole disk
    drive_object_path: str = ""
    drive_id: str = ""
    media_type: str = ""  # "SD", "MMC" (sysfs mmc type) or ""
    protected_reasons: tuple[str, ...] = field(default=())
    backend: str = ""

    @property
    def display_name(self) -> str:
        name = " ".join(p for p in (self.vendor.strip(), self.model.strip()) if p)
        return name or "Unknown device"

    @property
    def is_protected(self) -> bool:
        return bool(self.protected_reasons)

    @property
    def identity(self) -> DiskIdentity:
        return DiskIdentity(
            device=self.device,
            size=self.size,
            serial=self.serial,
            model=self.model,
            drive_id=self.drive_id or self.drive_object_path,
        )

    def mounted_partitions(self) -> list[Partition]:
        return [p for p in self.partitions if p.mounted]


def human_size(n: int | None) -> str:
    if n is None:
        return "—"
    value = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1000 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1000
    return f"{n} B"  # pragma: no cover
