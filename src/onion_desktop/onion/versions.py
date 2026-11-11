"""Onion OS version parsing and ordering.

Onion versions look like ``4.3.1``, ``4.3.1-1`` (package revision), ``4.4.0-beta-20260120``
or pre-release builds ``4.3.0-beta-dev-abc1234``. ``version.txt`` on the card stores them
with a ``v`` prefix. Final releases sort above pre-releases of the same x.y.z.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import total_ordering

_VERSION_RE = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)(?:\.(?P<patch>\d+))?"
    r"(?:-(?P<rev>\d+)(?=$|-))?"
    r"(?:-(?P<pre>[0-9A-Za-z][0-9A-Za-z.\-]*))?$"
)


@total_ordering
@dataclass(frozen=True)
class OnionVersion:
    major: int
    minor: int
    patch: int
    revision: int
    prerelease: str  # "" for final releases
    raw: str

    @property
    def is_prerelease(self) -> bool:
        return bool(self.prerelease)

    def _key(self) -> tuple[int, int, int, int, int, str]:
        return (self.major, self.minor, self.patch, 0 if self.prerelease else 1,
                self.revision, self.prerelease)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, OnionVersion):
            return NotImplemented
        return self._key() < other._key()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OnionVersion):
            return NotImplemented
        return self._key() == other._key()

    def __hash__(self) -> int:
        return hash(self._key())

    def __str__(self) -> str:
        return self.raw


def normalize_version_text(text: str) -> str:
    t = text.strip().strip("\x00").strip()
    for prefix in ("Onion-v", "Onion v", "onion-v"):
        if t.startswith(prefix):
            t = t[len(prefix):]
    if t[:1] in ("v", "V") and t[1:2].isdigit():
        t = t[1:]
    if t.endswith(".zip"):
        t = t[:-4]
    return t


def parse_version(text: str) -> OnionVersion | None:
    """Parse an Onion version string; return None if it is not recognisable."""
    t = normalize_version_text(text)
    m = _VERSION_RE.match(t)
    if not m:
        return None
    return OnionVersion(
        major=int(m["major"]),
        minor=int(m["minor"]),
        patch=int(m["patch"] or 0),
        revision=int(m["rev"] or 0),
        prerelease=m["pre"] or "",
        raw=t,
    )


def version_from_asset_name(name: str) -> str | None:
    m = re.fullmatch(r"Onion-v([0-9][0-9A-Za-z.\-]*)\.zip", name)
    return m.group(1) if m else None
