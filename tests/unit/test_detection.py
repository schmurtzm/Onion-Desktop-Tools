from conftest import make_onion_card, make_stock_card, write
from onion_desktop.onion.detection import CardState, detect_card, strings_version


def test_empty(tmp_path):
    (tmp_path / "System Volume Information").mkdir()
    assert detect_card(tmp_path).state is CardState.EMPTY


def test_onion_version_txt(tmp_path):
    info = detect_card(make_onion_card(tmp_path, "4.3.1-1"))
    assert info.state is CardState.ONION
    assert info.version == "4.3.1-1"
    assert not info.update_pending
    assert info.free_bytes and info.free_bytes > 0


def test_onion_version_from_binary_when_txt_missing(tmp_path):
    write(tmp_path / ".tmp_update/bin/installUI", b"\x7fELF\x00\x01junk\x00--version\x00\x00v4.2.3\x00more")
    info = detect_card(tmp_path)
    assert info.state is CardState.ONION and info.version == "4.2.3"


def test_onion_update_pending(tmp_path):
    make_onion_card(tmp_path)
    write(tmp_path / "miyoo/app/.tmp_update/onion.pak", b"x")
    assert detect_card(tmp_path).update_pending


def test_install_pending(tmp_path):
    write(tmp_path / ".tmp_update/updater", b"x")
    write(tmp_path / "miyoo/app/.tmp_update/onion.pak", b"x")
    write(tmp_path / "miyoo/app/.tmp_update/bin/installUI", b"--version\x004.4.0-beta-20260120\x00")
    info = detect_card(tmp_path)
    assert info.state is CardState.ONION_INSTALL_PENDING
    assert info.version == "4.4.0-beta-20260120"


def test_stock_and_other(tmp_path):
    assert detect_card(make_stock_card(tmp_path / "s")).state is CardState.STOCK
    write(tmp_path / "o/photos/a.jpg")
    assert detect_card(tmp_path / "o").state is CardState.OTHER


def test_unreadable(tmp_path):
    assert detect_card(tmp_path / "missing").state is CardState.UNREADABLE


def test_strings_version_no_marker(tmp_path):
    p = write(tmp_path / "bin", b"nothing here 1.2.3")
    assert strings_version(p) is None
