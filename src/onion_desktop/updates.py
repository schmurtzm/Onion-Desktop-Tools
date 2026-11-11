"""Self-update *check* (upstream ODT_update.ps1 replaced itself; the AppImage does not)."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from . import __version__
from .onion.releases import GITHUB_API, make_client
from .onion.versions import parse_version

UPDATE_REPO = "SpikeTheDragon40k/Onion-Desktop-Tools"


@dataclass(frozen=True)
class UpdateInfo:
    current: str
    latest: str
    url: str

    @property
    def newer(self) -> bool:
        a, b = parse_version(self.latest), parse_version(self.current)
        return bool(a and b and a > b)


def check_for_update(client: httpx.Client | None = None) -> UpdateInfo | None:
    own = client is None
    client = client or make_client()
    try:
        r = client.get(f"{GITHUB_API}/repos/{UPDATE_REPO}/releases/latest")
        if r.status_code != 200:
            return None
        data = r.json()
        tag = str(data.get("tag_name", "")).lstrip("v")
        return UpdateInfo(__version__, tag, f"https://github.com/{UPDATE_REPO}/releases")
    except (httpx.HTTPError, ValueError):
        return None
    finally:
        if own:
            client.close()
