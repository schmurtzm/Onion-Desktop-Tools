import json

import pytest

from conftest import write
from onion_desktop.backup.backup_manager import plan_backup, run_backup
from onion_desktop.backup.profiles import ALL, Category, available_categories
from onion_desktop.backup.restore_manager import list_backups, plan_restore, run_restore
from onion_desktop.core.copier import ConflictPolicy
from onion_desktop.core.exceptions import OdtError
from onion_desktop.onion.detection import CardState, detect_card


def rels(plan):
    return sorted(str(i.dst_rel) for i in plan.items)


def test_onion_backup_categories(onion_card):
    card = detect_card(onion_card)
    p = plan_backup(card, [Category.ROMS])
    assert rels(p) == ["Roms/FC/mario.nes", "Roms/GBA/cover.png", "Roms/GBA/game1.gba"]
    assert rels(plan_backup(card, [Category.IMGS])) == ["Roms/GBA/Imgs/game1.png", "Roms/GBA/cover.png"]
    assert rels(plan_backup(card, [Category.RETROARCH])) == ["RetroArch/.retroarch/retroarch.cfg"]
    assert rels(plan_backup(card, [Category.ONION_CONFIG])) == [
        ".tmp_update/config/.customUnknownFlag", ".tmp_update/config/.noAutoStart", ".tmp_update/config/.showRecents_"]


def test_stock_backup_rules(stock_card):
    card = detect_card(stock_card)
    assert card.state is CardState.STOCK
    assert set(available_categories(card.state)) == {Category.ROMS, Category.IMGS, Category.BIOS}
    p = plan_backup(card, list(ALL))
    assert "Roms/GBA/Imgs/stockgame.png" in rels(p)
    assert "BIOS/gba_bios.bin" in rels(p)
    assert not any("scph39" in r or "cheats/" in r or "scummvm" in r for r in rels(p))
    assert p.add_fbneo_cheats


def test_other_card_nothing_to_backup(tmp_path):
    write(tmp_path / "random.txt")
    with pytest.raises(OdtError):
        plan_backup(detect_card(tmp_path), list(ALL))


def test_backup_then_restore_roundtrip(onion_card, tmp_path):
    card = detect_card(onion_card)
    res = run_backup(plan_backup(card, list(ALL)), tmp_path / "backups", "my description")
    assert res.ok
    info = next(res.folder.glob("Backupinfo_*.txt")).read_text()
    assert "Source: Onion 4.3.0" in info and "my description" in info
    manifest = json.loads((res.folder / "odt_manifest.json").read_text())
    assert manifest["complete"] and "Saves/CurrentProfile/saves/game1.srm" in manifest["files"]

    # second backup in the same second must not overwrite the first
    res2 = run_backup(plan_backup(card, [Category.SAVES]), tmp_path / "backups", "")
    assert res2.folder != res.folder and len(list_backups(tmp_path / "backups")) == 2

    target = tmp_path / "newcard"
    from conftest import make_onion_card
    make_onion_card(target, "4.3.1")
    (target / "Roms").rename(tmp_path / "trash")
    write(target / "Saves/CurrentProfile/saves/game1.srm", b"NEWER-DIFFERENT")
    backup = next(b for b in list_backups(tmp_path / "backups") if b.path == res.folder)
    assert set(backup.categories) == set(ALL)
    plan = plan_restore(backup, detect_card(target), list(ALL))
    assert [str(c.dst_rel) for c in plan.conflicts] == ["Saves/CurrentProfile/saves/game1.srm"]

    r = run_restore(plan, ConflictPolicy.SKIP)
    assert r.ok
    assert (target / "Roms/GBA/game1.gba").read_bytes() == b"G" * 300
    assert (target / "Roms/GBA/Imgs/game1.png").exists()
    assert (target / "Saves/CurrentProfile/saves/game1.srm").read_bytes() == b"NEWER-DIFFERENT"
    assert any("game1.srm" in s for s, _ in r.report.skipped)

    r2 = run_restore(plan_restore(backup, detect_card(target), [Category.SAVES]), ConflictPolicy.OVERWRITE)
    assert r2.ok and (target / "Saves/CurrentProfile/saves/game1.srm").read_bytes() == b"SAVE"


def test_stock_backup_adds_cheats(stock_card, tmp_path):
    res = run_backup(plan_backup(detect_card(stock_card), [Category.BIOS]), tmp_path / "b", "")
    assert (res.folder / "BIOS/fbneo/cheats/cheat.dat").stat().st_size == 13902823


def test_restore_detects_corruption(onion_card, tmp_path):
    res = run_backup(plan_backup(detect_card(onion_card), [Category.SAVES]), tmp_path / "b", "")
    (res.folder / "Saves/CurrentProfile/saves/game1.srm").write_bytes(b"EVIL")
    target = tmp_path / "t"
    target.mkdir()
    r = run_restore(plan_restore(list_backups(tmp_path / "b")[0], detect_card(target), [Category.SAVES]),
                    ConflictPolicy.SKIP)
    assert r.verify_failures == ["Saves/CurrentProfile/saves/game1.srm"] and not r.ok


def test_backup_reports_unreadable_files(onion_card, tmp_path):
    import os
    if os.geteuid() == 0:
        pytest.skip("root can read everything")
    (onion_card / "Saves/CurrentProfile/saves/game1.srm").chmod(0)
    res = run_backup(plan_backup(detect_card(onion_card), [Category.SAVES]), tmp_path / "b", "")
    assert not res.ok and res.report.failed
