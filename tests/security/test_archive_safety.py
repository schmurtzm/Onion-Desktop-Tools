import stat
import zipfile

import pytest

from onion_desktop.core.archive import extract_zip, inspect_zip
from onion_desktop.core.exceptions import ArchiveError, UnsafePathError


def mkzip(path, entries):
    with zipfile.ZipFile(path, "w") as zf:
        for e in entries:
            if isinstance(e, zipfile.ZipInfo):
                zf.writestr(e, b"target")
            else:
                zf.writestr(e[0], e[1])
    return path


@pytest.mark.parametrize("name", ["../evil.txt", "a/../../evil.txt", "/etc/passwd", "C:/x.txt",
                                  "a\\..\\b.txt", "x/./../../y"])
def test_traversal_rejected(tmp_path, name):
    z = mkzip(tmp_path / "a.zip", [(name, b"x")])
    with pytest.raises((UnsafePathError, ArchiveError)):
        inspect_zip(z)
    assert not (tmp_path / "evil.txt").exists()


def test_symlink_entry_rejected(tmp_path):
    zi = zipfile.ZipInfo("link")
    zi.external_attr = (stat.S_IFLNK | 0o777) << 16
    z = mkzip(tmp_path / "a.zip", [zi])
    with pytest.raises(UnsafePathError):
        inspect_zip(z)


def test_device_entry_rejected(tmp_path):
    zi = zipfile.ZipInfo("dev")
    zi.external_attr = (stat.S_IFCHR | 0o666) << 16
    with pytest.raises(UnsafePathError):
        inspect_zip(mkzip(tmp_path / "a.zip", [zi]))


def test_fat_invalid_names_rejected(tmp_path):
    with pytest.raises(ArchiveError):
        inspect_zip(mkzip(tmp_path / "a.zip", [("dir/a:b.txt", b"x")]))


def test_file_dir_conflict_rejected(tmp_path):
    with pytest.raises(ArchiveError):
        inspect_zip(mkzip(tmp_path / "a.zip", [("a", b"x"), ("a/b", b"y")]))


def test_bomb_ratio_rejected(tmp_path):
    p = tmp_path / "bomb.zip"
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("zeros.bin", b"\0" * (60 * 1024 * 1024))
    with pytest.raises(ArchiveError):
        inspect_zip(p)


def test_symlink_planted_in_destination_is_not_followed(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    dest = tmp_path / "card"
    dest.mkdir()
    (dest / "BIOS").symlink_to(outside)
    z = mkzip(tmp_path / "a.zip", [("BIOS/x.bin", b"evil")])
    with pytest.raises(UnsafePathError):
        extract_zip(z, dest)
    assert not (outside / "x.bin").exists()


def test_extract_overwrites_and_verifies(tmp_path):
    dest = tmp_path / "card"
    (dest / "a").mkdir(parents=True)
    (dest / "a/file.txt").write_text("old")
    z = mkzip(tmp_path / "a.zip", [("a/file.txt", b"new"), ("b/c.txt", b"c")])
    rep = extract_zip(z, dest)
    assert rep.ok and rep.verified
    assert (dest / "a/file.txt").read_bytes() == b"new"
    assert not list(dest.rglob(".odt-tmp-*"))
