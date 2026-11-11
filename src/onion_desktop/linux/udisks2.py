"""UDisks2 client over the D-Bus system bus (jeepney, no Qt dependency).

Privileged operations are performed by the UDisks2 daemon and authorised by Polkit; the
D-Bus messages carry the *allow interactive authorisation* flag so the desktop's Polkit
agent can prompt the user. This process never runs as root.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from ..core.exceptions import BackendUnavailableError, DeviceError
from ..core.models import Disk, Partition
from .sysprobe import SysPaths, mmc_media_type

BUS = "org.freedesktop.UDisks2"
ROOT = "/org/freedesktop/UDisks2"
MANAGER = "/org/freedesktop/UDisks2/Manager"
I_BLOCK = "org.freedesktop.UDisks2.Block"
I_PART = "org.freedesktop.UDisks2.Partition"
I_PTABLE = "org.freedesktop.UDisks2.PartitionTable"
I_FS = "org.freedesktop.UDisks2.Filesystem"
I_DRIVE = "org.freedesktop.UDisks2.Drive"
I_LOOP = "org.freedesktop.UDisks2.Loop"
I_MANAGER = "org.freedesktop.UDisks2.Manager"
LONG_TIMEOUT = 3600.0


class Transport(Protocol):
    def call(self, path: str, interface: str, method: str, signature: str | None,
             body: tuple[Any, ...], *, interactive: bool = False,
             timeout: float | None = 30.0) -> tuple[Any, ...]: ...


class JeepneyTransport:
    """Real system-bus transport. One connection per call keeps it thread-safe."""

    def call(self, path: str, interface: str, method: str, signature: str | None,
             body: tuple[Any, ...], *, interactive: bool = False,
             timeout: float | None = 30.0) -> tuple[Any, ...]:
        try:
            from jeepney import DBusAddress, MessageFlag, new_method_call
            from jeepney.io.blocking import open_dbus_connection
            from jeepney.wrappers import DBusErrorResponse, unwrap_msg
        except ImportError as exc:  # pragma: no cover - dependency missing
            raise BackendUnavailableError("The 'jeepney' D-Bus library is not available.") from exc
        addr = DBusAddress(path, bus_name=BUS, interface=interface)
        msg = new_method_call(addr, method, signature, body)
        if interactive:
            msg.header.flags |= MessageFlag.allow_interactive_authorization
        try:
            conn = open_dbus_connection(bus="SYSTEM")
        except (OSError, ConnectionError, KeyError, ValueError) as exc:
            raise BackendUnavailableError(f"Cannot connect to the D-Bus system bus: {exc}") from exc
        try:
            reply = conn.send_and_get_reply(msg, timeout=timeout)
            result: tuple[Any, ...] = unwrap_msg(reply)
            return result
        except DBusErrorResponse as exc:
            name = getattr(exc, "name", "")
            text = exc.data[0] if getattr(exc, "data", None) else str(exc)
            if name == "org.freedesktop.DBus.Error.ServiceUnknown":
                raise BackendUnavailableError("The UDisks2 service is not running.") from exc
            if name.endswith("NotAuthorized") or name.endswith("NotAuthorizedCanObtain"):
                raise DeviceError("Authorisation was denied or cancelled.", hint=str(text)) from exc
            raise DeviceError(f"UDisks2 error: {text}") from exc
        except TimeoutError as exc:
            raise DeviceError("The disk service did not answer in time.") from exc
        finally:
            conn.close()


def unwrap(v: Any) -> Any:
    """Strip one jeepney variant wrapper ``(signature, value)``."""
    if isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], str):
        return v[1]
    return v


def unwrap_props(props: dict[str, Any]) -> dict[str, Any]:
    return {str(k): unwrap(v) for k, v in props.items()}


def bytestring(v: Any) -> str:
    """Decode UDisks ``ay`` NUL-terminated strings."""
    if isinstance(v, (bytes, bytearray)):
        return bytes(v).rstrip(b"\x00").decode("utf-8", "replace")
    if isinstance(v, list):
        return bytes(int(x) for x in v).rstrip(b"\x00").decode("utf-8", "replace")
    return str(v or "")


@dataclass(frozen=True)
class ManagedObjects:
    objects: dict[str, dict[str, dict[str, Any]]]

    def with_iface(self, iface: str) -> dict[str, dict[str, Any]]:
        return {p: ifs[iface] for p, ifs in self.objects.items() if iface in ifs}


def parse_disks(mo: ManagedObjects, paths: SysPaths | None = None) -> list[Disk]:
    blocks = mo.with_iface(I_BLOCK)
    drives = mo.with_iface(I_DRIVE)
    parts_by_table: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for path, props in mo.with_iface(I_PART).items():
        parts_by_table.setdefault(str(props.get("Table", "")), []).append((path, props))
    disks: list[Disk] = []
    for path, b in blocks.items():
        ifaces = mo.objects[path]
        if I_PART in ifaces or I_LOOP in ifaces:
            continue
        device = bytestring(b.get("Device"))
        kname = device.rsplit("/", 1)[-1]
        if not device or any(kname.startswith(p) for p in ("loop", "zram", "ram", "sr", "dm-", "md", "nbd")):
            continue
        drive_path = str(b.get("Drive", "/"))
        drive = drives.get(drive_path, {})
        if not drive and drive_path in ("", "/"):
            continue  # not backed by a physical drive
        size = int(b.get("Size", 0) or drive.get("Size", 0) or 0)
        if size == 0 and not drive.get("MediaAvailable", True):
            continue  # card reader without card
        partitions = []
        for ppath, pprops in sorted(parts_by_table.get(path, []), key=lambda x: int(x[1].get("Number", 0))):
            pb = blocks.get(ppath, {})
            fs = mo.objects.get(ppath, {}).get(I_FS, {})
            mps = tuple(bytestring(m) for m in fs.get("MountPoints", []) or [])
            partitions.append(Partition(
                device=bytestring(pb.get("Device")),
                number=int(pprops.get("Number", 0)),
                size=int(pprops.get("Size", 0) or pb.get("Size", 0)),
                fs_type=str(pb.get("IdType", "")),
                fs_version=str(pb.get("IdVersion", "")),
                label=str(pb.get("IdLabel", "")),
                uuid=str(pb.get("IdUUID", "")),
                mount_points=tuple(m for m in mps if m),
                object_path=ppath,
            ))
        whole_fs = ifaces.get(I_FS)
        if whole_fs is not None and not partitions:
            # Filesystem directly on the whole disk ("superfloppy"): model it as partition 0 so that
            # unmounting, protection checks and the target selector treat it like any other volume.
            mps = tuple(bytestring(m) for m in whole_fs.get("MountPoints", []) or [])
            partitions.append(Partition(
                device=device, number=0, size=int(b.get("Size", 0)), fs_type=str(b.get("IdType", "")),
                fs_version=str(b.get("IdVersion", "")), label=str(b.get("IdLabel", "")),
                uuid=str(b.get("IdUUID", "")), mount_points=tuple(m for m in mps if m), object_path=path,
            ))
        ptable = mo.objects[path].get(I_PTABLE, {})
        bus = str(drive.get("ConnectionBus", ""))
        disks.append(Disk(
            device=device,
            kernel_name=kname,
            size=size,
            model=str(drive.get("Model", "")),
            vendor=str(drive.get("Vendor", "")),
            serial=str(drive.get("Serial", "")),
            bus=bus,
            removable=bool(drive.get("MediaRemovable") or drive.get("Removable")),
            hotplug=bool(drive.get("Removable")) or bus in ("usb", "sdio", "ieee1394"),
            read_only=bool(b.get("ReadOnly", False)),
            partition_table=str(ptable.get("Type", "")) if ptable else "",
            fs_type=str(b.get("IdType", "")) if not ptable else "",
            partitions=tuple(partitions),
            object_path=path,
            drive_object_path=drive_path,
            drive_id=str(drive.get("Id", "")) or drive_path,
            media_type=mmc_media_type(kname, paths) if kname.startswith("mmcblk") else "",
            backend="udisks2",
        ))
    return disks


class UDisks2Client:
    name = "udisks2"
    can_modify = True

    def __init__(self, transport: Transport | None = None, paths: SysPaths | None = None) -> None:
        self.t = transport or JeepneyTransport()
        self.paths = paths

    # -- queries --------------------------------------------------------------------------
    def managed_objects(self) -> ManagedObjects:
        (raw,) = self.t.call(ROOT, "org.freedesktop.DBus.ObjectManager", "GetManagedObjects", None, ())
        return ManagedObjects({str(p): {str(i): unwrap_props(props) for i, props in ifs.items()} for p, ifs in raw.items()})

    def list_disks(self) -> list[Disk]:
        return parse_disks(self.managed_objects(), self.paths)

    def version(self) -> tuple[int, ...]:
        (v,) = self.t.call(MANAGER, "org.freedesktop.DBus.Properties", "Get", "ss", (I_MANAGER, "Version"))
        text = str(unwrap(v))
        try:
            return tuple(int(x) for x in text.split(".")[:3])
        except ValueError:
            return (0,)

    # -- operations (all interactive: Polkit may prompt) -----------------------------------
    @staticmethod
    def _opts(extra: dict[str, tuple[str, Any]] | None = None) -> dict[str, tuple[str, Any]]:
        o: dict[str, tuple[str, Any]] = {"auth.no_user_interaction": ("b", False)}
        if extra:
            o.update(extra)
        return o

    def mount(self, fs_path: str) -> str:
        (mp,) = self.t.call(fs_path, I_FS, "Mount", "a{sv}", (self._opts(),), interactive=True, timeout=120)
        return str(mp)

    def unmount(self, fs_path: str, force: bool = False) -> None:
        extra = {"force": ("b", True)} if force else None
        self.t.call(fs_path, I_FS, "Unmount", "a{sv}", (self._opts(extra),), interactive=True, timeout=120)

    def check(self, fs_path: str) -> bool:
        (ok,) = self.t.call(fs_path, I_FS, "Check", "a{sv}", (self._opts(),), interactive=True,
                            timeout=LONG_TIMEOUT)
        return bool(ok)

    def repair(self, fs_path: str) -> bool:
        (ok,) = self.t.call(fs_path, I_FS, "Repair", "a{sv}", (self._opts(),), interactive=True,
                            timeout=LONG_TIMEOUT)
        return bool(ok)

    def create_dos_table(self, block_path: str) -> None:
        self.t.call(block_path, I_BLOCK, "Format", "sa{sv}",
                    ("dos", self._opts({"tear-down": ("b", True)})),
                    interactive=True, timeout=LONG_TIMEOUT)

    def create_fat32_partition(self, block_path: str, label: str, force_fat32_arg: bool) -> str:
        fmt: dict[str, tuple[str, Any]] = {"label": ("s", label)}
        if force_fat32_arg:
            fmt["mkfs-args"] = ("as", ["-F", "32"])
        fmt.update(self._opts())
        (created,) = self.t.call(
            block_path, I_PTABLE, "CreatePartitionAndFormat", "ttsssa{sv}sa{sv}",
            (1024 * 1024, 0, "0x0c", "", self._opts(), "vfat", fmt),
            interactive=True, timeout=LONG_TIMEOUT,
        )
        return str(created)

    def power_off(self, drive_path: str) -> None:
        self.t.call(drive_path, I_DRIVE, "PowerOff", "a{sv}", (self._opts(),), interactive=True, timeout=120)

    def eject(self, drive_path: str) -> None:
        self.t.call(drive_path, I_DRIVE, "Eject", "a{sv}", (self._opts(),), interactive=True, timeout=120)

    def drive_props(self, drive_path: str) -> dict[str, Any]:
        (props,) = self.t.call(drive_path, "org.freedesktop.DBus.Properties", "GetAll", "s", (I_DRIVE,))
        result: dict[str, Any] = unwrap_props(props)
        return result


def probe(make: Callable[[], UDisks2Client] = UDisks2Client) -> UDisks2Client | None:
    """Return a working client, or None if UDisks2 is unreachable."""
    try:
        client = make()
        client.managed_objects()
        return client
    except (BackendUnavailableError, DeviceError, OSError):
        return None
