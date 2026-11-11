"""Destructive-operation safeguards, exercised against fake backends (no real disks)."""

from dataclasses import replace

import pytest

from onion_desktop.core.exceptions import BackendUnavailableError, DeviceChangedError, DeviceError, ProtectedDeviceError
from onion_desktop.core.models import Disk, Partition
from onion_desktop.linux.disk_manager import DiskManager


def sd(**kw):
    base = dict(device="/dev/sdb", kernel_name="sdb", size=32_000_000_000, model="SD Reader", serial="S1",
                bus="usb", removable=True, hotplug=True, object_path="/b/sdb", drive_object_path="/d/1",
                drive_id="drive-1",
                partitions=(Partition("/dev/sdb1", 1, 31_000_000_000, "vfat", "FAT32", "OLD",
                                      mount_points=("/media/u/OLD",), object_path="/b/sdb1"),))
    base.update(kw)
    return Disk(**base)


class FakeUDisks:
    name = "fake"
    can_modify = True

    def __init__(self, disks, fat_version="FAT32"):
        self.disks = list(disks)
        self.calls = []
        self.fat_version = fat_version
        self.swap_after = None  # replace disk list after N calls (simulate card swap)

    def list_disks(self):
        if self.swap_after is not None and len(self.calls) >= self.swap_after:
            return [replace(self.disks[0], serial="OTHER")]
        return list(self.disks)

    def unmount(self, path):
        self.calls.append(("unmount", path))
        d = self.disks[0]
        self.disks[0] = replace(d, partitions=tuple(replace(p, mount_points=()) for p in d.partitions))

    def create_dos_table(self, path):
        self.calls.append(("table", path))
        self.disks[0] = replace(self.disks[0], partitions=())

    def version(self):
        return (2, 10, 1)

    def create_fat32_partition(self, path, label, mkfs):
        self.calls.append(("part", path, label, mkfs))
        p = Partition("/dev/sdb1", 1, 31_000_000_000, "vfat", self.fat_version, label, object_path="/b/sdb1")
        self.disks[0] = replace(self.disks[0], partitions=(p,))
        return "/b/sdb1"

    def mount(self, path):
        self.calls.append(("mount", path))
        return "/media/u/ONION"


def mgr(backend, system=None):
    return DiskManager(backend, system_probe=lambda: system or {})


def test_format_happy_path():
    b = FakeUDisks([sd()])
    m = mgr(b)
    disk = m.list_disks()[0]
    res = m.format_fat32(disk.identity, confirmed_device_text="/dev/sdb")
    assert res.partition.is_fat32 and res.mount_point == "/media/u/ONION"
    assert [c[0] for c in b.calls] == ["unmount", "table", "part", "mount"]
    assert b.calls[2][2] == "ONION" and b.calls[2][3] is True


def test_requires_typed_confirmation():
    m = mgr(FakeUDisks([sd()]))
    with pytest.raises(ProtectedDeviceError):
        m.format_fat32(m.list_disks()[0].identity, confirmed_device_text="/dev/sdc")


def test_system_disk_refused():
    b = FakeUDisks([sd()])
    m = mgr(b, {"sdb": ["hosts system mount point /"]})
    disk = m.list_disks()[0]
    assert disk.is_protected
    with pytest.raises(ProtectedDeviceError):
        m.format_fat32(disk.identity, confirmed_device_text="/dev/sdb")
    assert b.calls == []


@pytest.mark.parametrize("change", [
    dict(removable=False, hotplug=False, bus="nvme"),
    dict(read_only=True),
    dict(size=4 * 1024**4),
    dict(media_type="MMC", bus="sdio", removable=False, hotplug=False),
    dict(partitions=(Partition("/dev/sdb1", 1, 10, "ext4", mount_points=("/home",)),)),
])
def test_ineligible_disks_refused(change):
    b = FakeUDisks([sd(**change)])
    m = mgr(b)
    with pytest.raises(ProtectedDeviceError):
        m.format_fat32(m.list_disks()[0].identity, confirmed_device_text="/dev/sdb")
    assert ("table", "/b/sdb") not in b.calls


def test_card_swapped_before_format():
    b = FakeUDisks([sd()])
    m = mgr(b)
    ident = m.list_disks()[0].identity
    b.swap_after = 0
    with pytest.raises(DeviceChangedError):
        m.format_fat32(ident, confirmed_device_text="/dev/sdb")
    assert b.calls == []


def test_card_swapped_mid_operation():
    b = FakeUDisks([sd()])
    m = mgr(b)
    ident = m.list_disks()[0].identity
    b.swap_after = 1  # after unmount, a different card appears
    with pytest.raises(DeviceChangedError):
        m.format_fat32(ident, confirmed_device_text="/dev/sdb")
    assert ("table", "/b/sdb") not in b.calls


def test_device_removed():
    b = FakeUDisks([sd()])
    m = mgr(b)
    ident = m.list_disks()[0].identity
    b.disks = []
    with pytest.raises(DeviceChangedError):
        m.format_fat32(ident, confirmed_device_text="/dev/sdb")


def test_verification_failure_not_fat32():
    m = mgr(FakeUDisks([sd()], fat_version="FAT16"))
    with pytest.raises(DeviceError, match="not FAT32"):
        m.format_fat32(m.list_disks()[0].identity, confirmed_device_text="/dev/sdb")


def test_read_only_backend_fails_closed():
    class RO:
        name, can_modify = "lsblk", False

        def list_disks(self):
            return [sd()]
    m = mgr(RO())
    with pytest.raises(BackendUnavailableError):
        m.format_fat32(m.list_disks()[0].identity, confirmed_device_text="/dev/sdb")
