from __future__ import annotations

import zipfile
from pathlib import Path

import pytest


def write(p: Path, data: bytes | str = b"x") -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data.encode() if isinstance(data, str) else data)
    return p


def make_release_zip(path: Path, version: str = "4.3.1-1", extra: dict[str, bytes] | None = None) -> Path:
    files = {
        "miyoo/app/.tmp_update/onion.pak": b"PAK" * 1000,
        "miyoo/app/.tmp_update/install.sh": b"#!/bin/sh\n",
        "miyoo/app/.tmp_update/bin/installUI": b"\x00ELF\x00--version\x00" + version.encode() + b"\x00",
        ".tmp_update/updater": b"#!/bin/sh\n",
        "BIOS/gba_bios_placeholder.txt": b"bios",
        "RetroArch/retroarch.pak": b"RA" * 500,
    }
    files.update(extra or {})
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("miyoo/", b"")
        for name, data in files.items():
            zf.writestr(name, data)
    return path


def make_onion_card(root: Path, version: str = "4.3.0") -> Path:
    write(root / ".tmp_update/onionVersion/version.txt", f"v{version}")
    write(root / ".tmp_update/bin/installUI", b"\x00--version\x00" + version.encode() + b"\x00")
    write(root / ".tmp_update/runtime.sh", "#!/bin/sh\necho original\n")
    write(root / ".tmp_update/config/.noAutoStart", b"")
    write(root / ".tmp_update/config/.showRecents_", b"")
    write(root / ".tmp_update/config/.customUnknownFlag", b"keep")
    write(root / "Roms/GBA/game1.gba", b"G" * 300)
    write(root / "Roms/GBA/Imgs/game1.png", b"PNG1")
    write(root / "Roms/GBA/cover.png", b"PNG2")
    write(root / "Roms/FC/mario.nes", b"N" * 100)
    write(root / "Saves/CurrentProfile/saves/game1.srm", b"SAVE")
    write(root / "BIOS/gba_bios.bin", b"B" * 50)
    write(root / "RetroArch/.retroarch/retroarch.cfg", "video_smooth = false\n")
    write(root / "RetroArch/.retroarch/sub/deep.cfg", "x\n")
    return root


def make_stock_card(root: Path) -> Path:
    write(root / "RApp/readme.txt", "stock")
    write(root / "Roms/GBA/stockgame.gba", b"S" * 10)
    write(root / "Imgs/GBA/stockgame.png", b"IMG")
    write(root / "RetroArch/.retroarch/system/gba_bios.bin", b"BIOS")
    write(root / "RetroArch/.retroarch/system/scph39001.bin", b"EXCL")
    write(root / "RetroArch/.retroarch/system/cheats/a.ini", b"EXCL")
    write(root / "RetroArch/.retroarch/system/scummvm/x.dat", b"EXCL")
    return root


@pytest.fixture
def onion_card(tmp_path: Path) -> Path:
    return make_onion_card(tmp_path / "card")


@pytest.fixture
def stock_card(tmp_path: Path) -> Path:
    return make_stock_card(tmp_path / "stock")


@pytest.fixture(autouse=True)
def _cards_are_fat32(monkeypatch, request):
    """Temp dirs live on ext4/tmpfs; pretend they are FAT32 unless a test opts out."""
    if "real_fs_type" in request.keywords:
        return
    monkeypatch.setattr("onion_desktop.onion.detection.filesystem_type_of", lambda p: "vfat")
