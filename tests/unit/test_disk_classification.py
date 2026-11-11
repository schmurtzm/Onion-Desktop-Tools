import json
from pathlib import Path

from onion_desktop.core.models import Disk
from onion_desktop.linux.disk_manager import eligibility_problems
from onion_desktop.linux.lsblk_backend import parse_lsblk
from onion_desktop.linux.sysprobe import SysPaths, system_disks
from onion_desktop.linux.udisks2 import ManagedObjects, parse_disks

LSBLK = {"blockdevices": [
    {"name": "nvme0n1", "kname": "nvme0n1", "path": "/dev/nvme0n1", "type": "disk", "size": 512110190592,
     "model": "Samsung SSD", "serial": "X", "tran": "nvme", "rm": False, "hotplug": False, "ro": False,
     "pttype": "gpt", "children": [
        {"name": "nvme0n1p2", "kname": "nvme0n1p2", "path": "/dev/nvme0n1p2", "type": "part", "size": 500,
         "fstype": "ext4", "mountpoint": "/", "partn": 2}]},
    {"name": "sdb", "kname": "sdb", "path": "/dev/sdb", "type": "disk", "size": 31914983424,
     "model": "SD/MMC", "vendor": "Generic", "serial": "123", "tran": "usb", "rm": True, "hotplug": True,
     "ro": False, "pttype": "dos", "children": [
        {"name": "sdb1", "kname": "sdb1", "path": "/dev/sdb1", "type": "part", "size": 31913934848,
         "fstype": "vfat", "fsver": "FAT32", "label": "ONION", "mountpoint": "/media/u/ONION",
         "fsavail": "1000", "partn": 1}]},
    {"name": "loop0", "kname": "loop0", "type": "loop", "size": 1},
]}


def test_parse_lsblk():
    disks = parse_lsblk(LSBLK)
    assert [d.device for d in disks] == ["/dev/nvme0n1", "/dev/sdb"]
    sdb = disks[1]
    assert sdb.partitions[0].is_fat32 and sdb.partitions[0].mount_point == "/media/u/ONION"
    assert sdb.partitions[0].free_bytes == 1000


def test_eligibility():
    nvme, sdb = parse_lsblk(LSBLK)
    assert eligibility_problems(sdb, {}) == []
    probs = eligibility_problems(nvme, {"nvme0n1": ["hosts system mount point /"]})
    assert "hosts system mount point /" in probs
    assert any("mounted at /" in p for p in probs)
    assert any("removable" in p for p in probs)
    sdcard = Disk("/dev/mmcblk0", "mmcblk0", 32 * 10**9, bus="sdio", media_type="SD")
    assert eligibility_problems(sdcard, {}) == []
    emmc = Disk("/dev/mmcblk1", "mmcblk1", 32 * 10**9, bus="sdio", media_type="MMC")
    assert "internal eMMC storage" in eligibility_problems(emmc, {})


def _fake_sys(tmp_path: Path) -> SysPaths:
    """Root on LUKS (dm-0) over nvme0n1p2; swap on sda2."""
    s, p = tmp_path / "sys", tmp_path / "proc"
    blk = s / "class/block"
    dev_nvme = s / "devices/nvme0n1"
    (dev_nvme / "nvme0n1p2").mkdir(parents=True)
    (dev_nvme / "nvme0n1p2/partition").write_text("2")
    (s / "devices/dm-0/slaves").mkdir(parents=True)
    (s / "devices/dm-0/slaves/nvme0n1p2").mkdir()
    (s / "devices/sda/sda2").mkdir(parents=True)
    (s / "devices/sda/sda2/partition").write_text("2")
    blk.mkdir(parents=True)
    for name, target in [("nvme0n1", dev_nvme), ("nvme0n1p2", dev_nvme / "nvme0n1p2"),
                         ("dm-0", s / "devices/dm-0"), ("sda", s / "devices/sda"), ("sda2", s / "devices/sda/sda2")]:
        (blk / name).symlink_to(target)
    (s / "dev/block").mkdir(parents=True)
    (s / "dev/block/253:0").symlink_to(s / "devices/dm-0")
    (p / "self").mkdir(parents=True)
    (p / "self/mountinfo").write_text(
        "22 1 253:0 / / rw,relatime - ext4 /dev/mapper/root rw\n"
        "30 22 0:40 / /media/u/X rw - vfat /dev/sdc1 rw\n")
    (p / "swaps").write_text("Filename Type Size Used Priority\n/dev/sda2 partition 1 0 -2\n")
    return SysPaths(s, p, tmp_path / "dev")


def test_system_disks_through_dm(tmp_path, monkeypatch):
    paths = _fake_sys(tmp_path)
    import os
    real = os.path.realpath
    monkeypatch.setattr(os.path, "realpath",
                        lambda x: real(str(tmp_path / "sys/devices/sda/sda2")) if x == "/dev/sda2" else real(x))
    res = system_disks(paths)
    assert "nvme0n1" in res and "hosts system mount point /" in res["nvme0n1"]
    assert "sda" in res and "hosts active swap" in res["sda"]


def test_parse_udisks_objects():
    raw = json.loads((Path(__file__).parents[1] / "fixtures/udisks_objects.json").read_text())

    def conv(v):
        if isinstance(v, dict) and "__bytes__" in v:
            return v["__bytes__"].encode() + b"\0"
        if isinstance(v, list):
            return [conv(x) for x in v]
        if isinstance(v, dict):
            return {k: conv(x) for k, x in v.items()}
        return v
    disks = parse_disks(ManagedObjects(conv(raw)))
    assert len(disks) == 1
    d = disks[0]
    assert d.device == "/dev/sdb" and d.bus == "usb" and d.removable and d.drive_id == "Generic-SD-123"
    assert d.partitions[0].mount_points == ("/run/media/u/ONION",) and d.partitions[0].is_fat32


def test_superfloppy_modelled_as_partition_zero():
    data = {"blockdevices": [{"name": "sdd", "kname": "sdd", "path": "/dev/sdd", "type": "disk", "size": 8 * 10**9,
                              "tran": "usb", "rm": True, "hotplug": True, "fstype": "vfat", "fsver": "FAT32",
                              "mountpoint": "/media/u/CARD"}]}
    (d,) = parse_lsblk(data)
    assert d.partitions[0].number == 0 and d.partitions[0].mount_point == "/media/u/CARD"
    assert d.mounted_partitions()
    mo = ManagedObjects({
        "/b/sdd": {"org.freedesktop.UDisks2.Block": {"Device": b"/dev/sdd\0", "Size": 8 * 10**9, "Drive": "/d/x",
                                                     "IdType": "vfat", "IdVersion": "FAT32"},
                   "org.freedesktop.UDisks2.Filesystem": {"MountPoints": [b"/media/u/CARD\0"]}},
        "/d/x": {"org.freedesktop.UDisks2.Drive": {"ConnectionBus": "usb", "Removable": True, "Id": "x"}}})
    (u,) = parse_disks(mo)
    assert u.partitions[0].object_path == "/b/sdd" and u.partitions[0].mount_points == ("/media/u/CARD",)
