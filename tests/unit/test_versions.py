import pytest

from onion_desktop.onion.versions import parse_version, version_from_asset_name


@pytest.mark.parametrize("text,expected", [
    ("4.3.1", (4, 3, 1, 0, "")),
    ("v4.3.1-1", (4, 3, 1, 1, "")),
    ("Onion-v4.3.1-1.zip", (4, 3, 1, 1, "")),
    ("4.4.0-beta-20260120", (4, 4, 0, 0, "beta-20260120")),
    ("4.3.0-beta-dev-abc1234", (4, 3, 0, 0, "beta-dev-abc1234")),
    ("4.2", (4, 2, 0, 0, "")),
])
def test_parse(text, expected):
    v = parse_version(text)
    assert v is not None
    assert (v.major, v.minor, v.patch, v.revision, v.prerelease) == expected


@pytest.mark.parametrize("bad", ["", "latest", "v", "4", "4.x.1", "../4.3.1"])
def test_parse_rejects(bad):
    assert parse_version(bad) is None


def test_ordering():
    order = ["4.2.3", "4.3.0-beta-dev-1", "4.3.0", "4.3.1", "4.3.1-1", "4.4.0-beta-20260120", "4.4.0"]
    parsed = [parse_version(x) for x in order]
    assert parsed == sorted(parsed)
    assert parse_version("v4.3.1") == parse_version("4.3.1")


def test_asset_name():
    assert version_from_asset_name("Onion-v4.3.1-1.zip") == "4.3.1-1"
    assert version_from_asset_name("Onion-v4.3.1.zip.exe") is None
    assert version_from_asset_name("evil/Onion-v4.zip") is None
