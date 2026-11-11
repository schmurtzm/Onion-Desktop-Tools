import pytest

from conftest import make_onion_card, make_release_zip, make_stock_card, write
from onion_desktop.core.exceptions import ArchiveError, OdtError, OperationCancelled
from onion_desktop.core.progress import CancelToken
from onion_desktop.onion.detection import CardState, detect_card
from onion_desktop.onion.installer import InstallMode, execute_install, plan_install


def test_fresh_install(tmp_path):
    card = tmp_path / "card"
    card.mkdir()
    z = make_release_zip(tmp_path / "Onion-v4.3.1-1.zip")
    plan = plan_install(z, card)
    assert plan.mode is InstallMode.FRESH and not plan.requires_strong_confirmation
    res = execute_install(plan)
    assert res.ok
    assert res.card_after.state is CardState.ONION_INSTALL_PENDING
    assert res.card_after.version == "4.3.1-1"


def test_upgrade_preserves_user_data(tmp_path):
    card = make_onion_card(tmp_path / "card", "4.3.0")
    z = make_release_zip(tmp_path / "Onion-v4.3.1-1.zip")
    plan = plan_install(z, card)
    assert plan.mode is InstallMode.UPGRADE
    assert "kept" in plan.confirmation
    assert execute_install(plan).ok
    assert (card / "Roms/GBA/game1.gba").read_bytes() == b"G" * 300
    assert (card / "Saves/CurrentProfile/saves/game1.srm").read_bytes() == b"SAVE"
    assert detect_card(card).update_pending


def test_reinstall_and_downgrade_modes(tmp_path):
    z = make_release_zip(tmp_path / "Onion-v4.3.1-1.zip")
    assert plan_install(z, make_onion_card(tmp_path / "a", "4.3.1-1")).mode is InstallMode.REINSTALL
    plan = plan_install(z, make_onion_card(tmp_path / "b", "4.4.0"))
    assert plan.mode is InstallMode.DOWNGRADE and plan.warnings


def test_stock_and_other_require_strong_confirmation(tmp_path):
    z = make_release_zip(tmp_path / "Onion-v4.3.1.zip")
    assert plan_install(z, make_stock_card(tmp_path / "s")).mode is InstallMode.STOCK
    write(tmp_path / "o/file.txt")
    p = plan_install(z, tmp_path / "o")
    assert p.mode is InstallMode.OTHER and p.requires_strong_confirmation


def test_rejects_non_onion_archive(tmp_path):
    import zipfile
    z = tmp_path / "Onion-v1.0.0.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("hello.txt", "hi")
    (tmp_path / "c").mkdir()
    with pytest.raises(ArchiveError):
        plan_install(z, tmp_path / "c")


def test_card_changed_between_plan_and_execute(tmp_path):
    card = tmp_path / "card"
    card.mkdir()
    plan = plan_install(make_release_zip(tmp_path / "Onion-v4.3.1.zip"), card)
    write(card / "RApp/x")
    with pytest.raises(OdtError, match="changed"):
        execute_install(plan)


def test_insufficient_space(tmp_path, monkeypatch):
    card = tmp_path / "card"
    card.mkdir()
    plan = plan_install(make_release_zip(tmp_path / "Onion-v4.3.1.zip"), card)
    monkeypatch.setattr("onion_desktop.onion.installer.free_space", lambda p: 10)
    from onion_desktop.core.exceptions import InsufficientSpaceError
    with pytest.raises(InsufficientSpaceError):
        execute_install(plan)
    assert not (card / "miyoo").exists()


def test_cancel(tmp_path):
    card = tmp_path / "card"
    card.mkdir()
    plan = plan_install(make_release_zip(tmp_path / "Onion-v4.3.1.zip"), card)
    tok = CancelToken()
    tok.cancel()
    with pytest.raises(OperationCancelled):
        execute_install(plan, cancel=tok)


def test_interrupted_extraction_can_be_repaired(tmp_path, monkeypatch):
    card = tmp_path / "card"
    card.mkdir()
    z = make_release_zip(tmp_path / "Onion-v4.3.1.zip")
    import onion_desktop.core.archive as arch
    real = arch._extract_member
    calls = {"n": 0}

    def flaky(zf, info, target, cancel):
        calls["n"] += 1
        if calls["n"] == 3:
            raise OSError(5, "Input/output error")
        return real(zf, info, target, cancel)
    monkeypatch.setattr(arch, "_extract_member", flaky)
    res = execute_install(plan_install(z, card))
    assert not res.ok and res.extract.failed and not res.extract.verified
    monkeypatch.setattr(arch, "_extract_member", real)
    assert execute_install(plan_install(z, card)).ok


def test_non_fat_card_warns(tmp_path, monkeypatch):
    monkeypatch.setattr("onion_desktop.onion.detection.filesystem_type_of", lambda p: "exfat")
    card = tmp_path / "card"
    card.mkdir()
    plan = plan_install(make_release_zip(tmp_path / "Onion-v4.3.1.zip"), card)
    assert plan.requires_strong_confirmation and any("exfat" in w for w in plan.warnings)
