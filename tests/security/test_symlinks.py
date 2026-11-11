from pathlib import PurePosixPath

import pytest

from onion_desktop.core.exceptions import UnsafePathError
from onion_desktop.core.safe_fs import safe_join, walk_files


def test_safe_join_rejects_symlink_component(tmp_path):
    (tmp_path / "real").mkdir()
    (tmp_path / "link").symlink_to("/etc")
    with pytest.raises(UnsafePathError):
        safe_join(tmp_path, "link/passwd")
    assert safe_join(tmp_path, "real/x") == (tmp_path / "real/x").resolve()


def test_walk_does_not_follow_links(tmp_path):
    (tmp_path / "d").mkdir()
    (tmp_path / "d/a.txt").write_text("a")
    (tmp_path / "d/link.txt").symlink_to("/etc/hostname")
    (tmp_path / "d/dirlink").symlink_to("/etc")
    skipped = []
    files = [e.rel for e in walk_files(tmp_path, on_skipped=lambda r, w: skipped.append(r))]
    assert files == [PurePosixPath("d/a.txt")]
    assert {str(s) for s in skipped} == {"d/link.txt", "d/dirlink"}


def test_planted_temp_symlink_is_not_followed(tmp_path):
    """A crafted card may contain '.odt-tmp-<name>' symlinks pointing outside the card."""
    import zipfile

    from onion_desktop.core.archive import extract_zip
    from onion_desktop.core.copier import CopyItem, execute_copy
    victim = tmp_path / "victim.txt"
    victim.write_text("precious")
    card = tmp_path / "card"
    (card / "BIOS").mkdir(parents=True)
    (card / "BIOS/.odt-tmp-x.bin").symlink_to(victim)
    z = tmp_path / "a.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("BIOS/x.bin", b"payload")
    assert extract_zip(z, card).ok
    assert victim.read_text() == "precious" and (card / "BIOS/x.bin").read_bytes() == b"payload"

    (card / "BIOS/.odt-tmp-y.bin").symlink_to(victim)
    src = tmp_path / "src.bin"
    src.write_bytes(b"data")
    rep = execute_copy([CopyItem(src, PurePosixPath("BIOS/y.bin"), 4)], card)
    assert rep.ok and victim.read_text() == "precious"
