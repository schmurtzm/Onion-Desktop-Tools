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
