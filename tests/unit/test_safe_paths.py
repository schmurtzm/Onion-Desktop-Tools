from pathlib import PurePosixPath

import pytest

from onion_desktop.core.exceptions import UnsafePathError
from onion_desktop.core.safe_fs import check_fat_name, filesystem_type_of, validate_relative


@pytest.mark.parametrize("bad", ["", "/abs", "../x", "a/../../x", "C:x", "a\\b", "a\x00b", "."])
def test_validate_relative_rejects(bad):
    with pytest.raises(UnsafePathError):
        validate_relative(bad)


def test_validate_relative_normalises():
    assert validate_relative("a//./b/") == PurePosixPath("a/b")


def test_fat_names():
    assert check_fat_name(PurePosixPath("Roms/ok name.gba")) is None
    assert check_fat_name(PurePosixPath("Roms/what?.gba"))
    assert check_fat_name(PurePosixPath("Roms/trailing."))


def test_filesystem_type_of(tmp_path):
    mounts = tmp_path / "mounts"
    mounts.write_text("/dev/vda1 / ext4 rw 0 0\n/dev/sdb1 /media/u/My\\040Card vfat rw 0 0\n")
    assert filesystem_type_of(tmp_path, mounts) == "ext4"
    from pathlib import Path
    assert filesystem_type_of(Path("/media/u/My Card/Roms"), mounts) == "vfat"
