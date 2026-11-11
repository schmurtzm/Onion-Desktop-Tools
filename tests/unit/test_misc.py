import logging

from onion_desktop import settings
from onion_desktop.core.copier import ConflictPolicy, CopyItem, execute_copy
from onion_desktop.logging_setup import RedactingFilter, redact


def test_redaction():
    assert "hunter2" not in redact('psk="hunter2"')
    assert "s3cret" not in redact("password=s3cret and more")
    rec = logging.LogRecord("x", logging.INFO, "f", 1, "wifi psk=%s", ("abcdefgh",), None)
    RedactingFilter().filter(rec)
    assert "abcdefgh" not in rec.getMessage()


def test_settings_roundtrip(tmp_path):
    p = tmp_path / "s.json"
    s = settings.Settings(theme="dracula", backups_dir="/data/b")
    settings.save(s, p)
    assert settings.load(p).theme == "dracula"
    p.write_text('{"theme": "neon", "backups_dir": "relative/path", "check_updates_on_start": "yes"}')
    s2 = settings.load(p)
    assert s2.theme == "system" and s2.backups_dir == "" and s2.check_updates_on_start is False
    p.write_text("{broken")
    assert settings.load(p).theme == "system"


def test_copier_fat_limits_and_failures(tmp_path):
    src = tmp_path / "a.bin"
    src.write_bytes(b"x")
    items = [CopyItem(src, __import__("pathlib").PurePosixPath("ok.bin"), 1),
             CopyItem(src, __import__("pathlib").PurePosixPath("bad?.bin"), 1),
             CopyItem(tmp_path / "missing", __import__("pathlib").PurePosixPath("m.bin"), 1)]
    rep = execute_copy(items, tmp_path / "out", fat_target=True, policy=ConflictPolicy.SKIP)
    assert rep.copied == ["ok.bin"] and len(rep.failed) == 2 and not rep.ok
