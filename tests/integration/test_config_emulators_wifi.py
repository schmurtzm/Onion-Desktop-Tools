import pytest

from conftest import write
from onion_desktop.core.exceptions import OdtError
from onion_desktop.onion import wifi
from onion_desktop.onion.configuration import (
    FlagStore,
    backup_config,
    load_default_schema,
    parse_schema,
    restore_config,
)
from onion_desktop.onion.emulators import PackageStatus, install_package, scan_packages, uninstall_package


def test_schema_loads_all_upstream_flags():
    schema = load_default_schema()
    assert set(schema) == {"System", "Time", "User interface", "Network"}
    assert any(d.sub_option for d in schema["Network"])


def test_schema_rejects_bad_names():
    from onion_desktop.core.exceptions import ValidationError
    with pytest.raises(ValidationError):
        parse_schema({"Onion_Configuration": {"S": [{"filename": "../../etc/passwd"}]}})


def test_flag_toggle_semantics(onion_card, tmp_path):
    s = FlagStore(onion_card)
    schema = load_default_schema()
    snap = backup_config(onion_card, tmp_path / "snaps")
    assert s.is_enabled(".noAutoStart") and not s.is_enabled(".showRecents")
    s.set_enabled(".showRecents", True)  # renamed back from .showRecents_
    assert s.is_enabled(".showRecents") and not (s.directory / ".showRecents_").exists()
    s.set_enabled(".noAutoStart", False)
    assert (s.directory / ".noAutoStart_").exists()
    s.set_enabled(".logging", True)  # created
    assert (s.directory / ".logging").read_bytes() == b""
    assert s.unknown_flags(schema) == [".customUnknownFlag"]
    restore_config(snap, onion_card, schema)
    assert s.is_enabled(".noAutoStart") and not s.is_enabled(".showRecents") and not s.is_enabled(".logging")
    assert (s.directory / ".customUnknownFlag").read_text() == "keep"


def _pm(card):
    d = card / "App/PackageManager/data"
    write(d / "Emu/Nintendo - GBA (gpSP)/Emu/GBA/config.json", "{}")
    write(d / "Emu/Nintendo - GBA (gpSP)/Emu/GBA/launch.sh", "sh")
    (d / "Emu/Nintendo - GBA (gpSP)/Roms/GBA").mkdir(parents=True)
    write(d / "Emu/Sega - MD (PicoDrive)/Emu/MD/config.json", "{}")
    (d / "Emu/Sega - MD (PicoDrive)/Roms/MD").mkdir(parents=True)
    write(d / "App/Tool (X)/App/Tool/launch.sh", "sh")
    write(d / "App/Tool (X)/App/Tool/install.sh", "sh")
    write(d / "RApp/Scripts/RApp/romscripts/x.sh", "sh")


def test_package_scan_install_uninstall(onion_card):
    _pm(onion_card)
    pk = {p.name: p for p in scan_packages(onion_card)}
    assert set(pk) == {"Nintendo - GBA (gpSP)", "Sega - MD (PicoDrive)", "Tool (X)"}
    assert pk["Nintendo - GBA (gpSP)"].status is PackageStatus.ROMS_PRESENT
    assert pk["Sega - MD (PicoDrive)"].status is PackageStatus.NOT_INSTALLED
    assert pk["Tool (X)"].has_device_script

    rep = install_package(onion_card, pk["Nintendo - GBA (gpSP)"])
    assert rep.ok and (onion_card / "Emu/GBA/launch.sh").exists()
    assert (onion_card / "Roms/GBA/game1.gba").exists()
    assert {p.name: p for p in scan_packages(onion_card)}["Nintendo - GBA (gpSP)"].status is PackageStatus.INSTALLED

    write(onion_card / "Emu/GBA/user_custom.cfg", "mine")
    rep = uninstall_package(onion_card, pk["Nintendo - GBA (gpSP)"])
    assert rep.ok and not (onion_card / "Emu/GBA/launch.sh").exists()
    assert (onion_card / "Emu/GBA/user_custom.cfg").exists() and rep.kept == ["Emu/GBA"]
    assert (onion_card / "Roms/GBA/game1.gba").exists()


def test_wifi_queue_and_cancel(onion_card):
    original = (onion_card / wifi.RUNTIME).read_text()
    wifi.add_network(onion_card, "Home", "password123")
    wifi.add_network(onion_card, "Office", "")
    assert wifi.has_pending(onion_card) and wifi.pending_ssid_count(onion_card) == 2
    assert (onion_card / wifi.RUNTIME_ORI).read_text() == original
    data = (onion_card / wifi.PENDING_FILE).read_text()
    assert 'ssid="Home"' in data and "key_mgmt=NONE" in data
    assert wifi.cancel_pending(onion_card)
    assert (onion_card / wifi.RUNTIME).read_text() == original
    assert not (onion_card / wifi.PENDING_FILE).exists()


def test_wifi_refuses_non_onion(tmp_path):
    with pytest.raises(OdtError):
        wifi.add_network(tmp_path, "Home", "password123")
