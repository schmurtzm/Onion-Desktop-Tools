"""Discovery of official Onion OS releases on GitHub (OnionUI/Onion).

Only assets named ``Onion-v<version>.zip`` attached to releases of the official repository
are accepted, and their download URL must point at that repository's release downloads.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from .. import __version__
from ..core.exceptions import ReleaseMetadataError
from .versions import OnionVersion, parse_version, version_from_asset_name

GITHUB_API = "https://api.github.com"
ONION_REPO = "OnionUI/Onion"
USER_AGENT = f"onion-desktop-tools-linux/{__version__}"
ASSET_RE = re.compile(r"^Onion-v[0-9][0-9A-Za-z.\-]*\.zip$")
SHA256_RE = re.compile(r"^sha256:([0-9a-f]{64})$")
# Hosts allowed for the initial URL and every redirect of a release download.
ALLOWED_DOWNLOAD_HOSTS = {
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
    "github-releases.githubusercontent.com",
}


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    url: str
    size: int
    sha256: str | None  # from GitHub's asset "digest" when provided


@dataclass(frozen=True)
class Release:
    tag: str
    title: str
    version: str
    prerelease: bool
    html_url: str
    published_at: str
    notes: str
    asset: ReleaseAsset

    @property
    def channel(self) -> str:
        return "beta" if self.prerelease else "stable"

    @property
    def parsed_version(self) -> OnionVersion | None:
        return parse_version(self.version)


def is_allowed_download_url(url: str) -> bool:
    try:
        u = urlparse(url)
    except ValueError:
        return False
    return u.scheme == "https" and (u.hostname or "") in ALLOWED_DOWNLOAD_HOSTS


def _validate_asset_url(url: str, repo: str) -> None:
    u = urlparse(url)
    if u.scheme != "https" or u.hostname != "github.com":
        raise ReleaseMetadataError(f"Unexpected download host in release metadata: {url}")
    if not u.path.lower().startswith(f"/{repo.lower()}/releases/download/"):
        raise ReleaseMetadataError(f"Download URL is not an official release of {repo}: {url}")


def _validate_html_url(url: str, repo: str) -> str:
    u = urlparse(url)
    if u.scheme == "https" and u.hostname == "github.com" and u.path.lower().startswith(
        f"/{repo.lower()}/"
    ):
        return url
    return f"https://github.com/{repo}/releases"


def parse_release(data: dict[str, Any], repo: str = ONION_REPO) -> Release | None:
    """Convert one GitHub API release object; None if it has no usable Onion asset."""
    if not isinstance(data, dict) or data.get("draft"):
        return None
    assets = data.get("assets") or []
    chosen: dict[str, Any] | None = None
    for a in assets:
        if isinstance(a, dict) and isinstance(a.get("name"), str) and ASSET_RE.match(a["name"]):
            chosen = a
            break
    if chosen is None:
        return None
    url = chosen.get("browser_download_url")
    size = chosen.get("size")
    if not isinstance(url, str) or not isinstance(size, int) or size <= 0:
        raise ReleaseMetadataError(f"Release asset {chosen['name']} has invalid metadata.")
    _validate_asset_url(url, repo)
    if url.rsplit("/", 1)[-1] != chosen["name"]:
        raise ReleaseMetadataError("Asset name does not match its download URL.")
    digest = chosen.get("digest")
    sha256 = None
    if isinstance(digest, str):
        m = SHA256_RE.match(digest.strip().lower())
        if m:
            sha256 = m.group(1)
    version = version_from_asset_name(chosen["name"]) or str(data.get("tag_name", "")).lstrip("v")
    return Release(
        tag=str(data.get("tag_name", "")),
        title=str(data.get("name") or data.get("tag_name") or chosen["name"]),
        version=version,
        prerelease=bool(data.get("prerelease")),
        html_url=_validate_html_url(str(data.get("html_url", "")), repo),
        published_at=str(data.get("published_at") or ""),
        notes=str(data.get("body") or ""),
        asset=ReleaseAsset(chosen["name"], url, size, sha256),
    )


def make_client(timeout: float = 20.0, transport: httpx.BaseTransport | None = None) -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
        timeout=httpx.Timeout(timeout, connect=15.0),
        follow_redirects=False,
        transport=transport,
    )


def _get_json(client: httpx.Client, url: str) -> Any:
    try:
        r = client.get(url)
    except httpx.HTTPError as exc:
        raise ReleaseMetadataError(f"Cannot reach GitHub: {exc}") from exc
    if r.status_code == 403 and r.headers.get("x-ratelimit-remaining") == "0":
        raise ReleaseMetadataError(
            "GitHub API rate limit reached.", hint="Wait a few minutes and try again."
        )
    if r.status_code != 200:
        raise ReleaseMetadataError(f"GitHub API returned HTTP {r.status_code} for {url}.")
    try:
        return r.json()
    except ValueError as exc:
        raise ReleaseMetadataError("GitHub returned invalid JSON.") from exc


def fetch_releases(client: httpx.Client, repo: str = ONION_REPO, per_page: int = 30) -> list[Release]:
    data = _get_json(client, f"{GITHUB_API}/repos/{repo}/releases?per_page={per_page}")
    if not isinstance(data, list):
        raise ReleaseMetadataError("Unexpected GitHub API response.")
    releases: list[Release] = []
    for item in data:
        try:
            rel = parse_release(item, repo)
        except ReleaseMetadataError:
            continue  # skip a malformed release rather than failing the whole list
        if rel:
            releases.append(rel)
    return releases


def fetch_latest_stable(client: httpx.Client, repo: str = ONION_REPO) -> Release | None:
    data = _get_json(client, f"{GITHUB_API}/repos/{repo}/releases/latest")
    rel = parse_release(data, repo)
    return rel if rel and not rel.prerelease else None


@dataclass(frozen=True)
class Channels:
    stable: Release | None
    beta: Release | None
    all: list[Release]


def select_channels(releases: list[Release], latest_stable: Release | None = None) -> Channels:
    """Upstream semantics: stable = GitHub 'latest' release; beta = newest pre-release."""
    stable = latest_stable or next((r for r in releases if not r.prerelease), None)
    beta = next((r for r in releases if r.prerelease), None)
    return Channels(stable, beta, releases)


def discover(client: httpx.Client, repo: str = ONION_REPO) -> Channels:
    releases = fetch_releases(client, repo)
    try:
        latest = fetch_latest_stable(client, repo)
    except ReleaseMetadataError:
        latest = None
    return select_channels(releases, latest)
