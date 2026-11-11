"""Resumable, verified download of Onion release archives."""

from __future__ import annotations

import hashlib
import json
import os
import time
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

from ..core.exceptions import DownloadError, IntegrityError, OperationCancelled
from ..core.progress import CancelToken, Progress, ProgressCallback, null_progress
from .releases import ASSET_RE, Release, is_allowed_download_url

CHUNK = 256 * 1024
MAX_REDIRECTS = 5


@dataclass(frozen=True)
class LocalArchive:
    path: Path
    size: int
    sha256: str | None
    version: str | None
    channel: str | None
    verified_against_github_digest: bool

    @property
    def name(self) -> str:
        return self.path.name


def _sidecar(path: Path) -> Path:
    return path.with_name(path.name + ".json")


def sha256_of(path: Path, cancel: CancelToken | None = None) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            if cancel:
                cancel.raise_if_cancelled()
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def list_local_archives(directory: Path) -> list[LocalArchive]:
    out: list[LocalArchive] = []
    if not directory.is_dir():
        return out
    for p in sorted(directory.glob("*.zip"), key=lambda q: q.name, reverse=True):
        if p.is_symlink() or not p.is_file():
            continue
        meta: dict[str, Any] = {}
        try:
            meta = json.loads(_sidecar(p).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = {}
        out.append(
            LocalArchive(
                path=p,
                size=p.stat().st_size,
                sha256=meta.get("sha256") if isinstance(meta.get("sha256"), str) else None,
                version=meta.get("version") if isinstance(meta.get("version"), str) else None,
                channel=meta.get("channel") if isinstance(meta.get("channel"), str) else None,
                verified_against_github_digest=bool(meta.get("github_digest_verified")),
            )
        )
    return out


def is_cached(release: Release, directory: Path) -> bool:
    p = directory / release.asset.name
    if not p.is_file() or p.stat().st_size != release.asset.size:
        return False
    if release.asset.sha256:
        try:
            meta = json.loads(_sidecar(p).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        return bool(meta.get("sha256") == release.asset.sha256)
    return True


def _open_stream(client: httpx.Client, url: str, headers: dict[str, str]) -> httpx.Response:
    """GET with manual redirect handling so every hop is checked against the allowlist."""
    for _ in range(MAX_REDIRECTS + 1):
        if not is_allowed_download_url(url):
            raise DownloadError(f"Refusing to download from untrusted location: {url}")
        req = client.build_request("GET", url, headers=headers)
        resp = client.send(req, stream=True)
        if resp.status_code in (301, 302, 303, 307, 308):
            loc = resp.headers.get("location")
            resp.close()
            if not loc:
                raise DownloadError("Redirect without location.")
            url = urljoin(url, loc)
            continue
        return resp
    raise DownloadError("Too many redirects.")


def download_release(
    release: Release,
    directory: Path,
    client: httpx.Client,
    *,
    progress: ProgressCallback = null_progress,
    cancel: CancelToken | None = None,
    retries: int = 3,
    backoff: float = 2.0,
) -> LocalArchive:
    """Download *release*'s asset into *directory* and verify it.

    The file is written as ``<name>.part`` (resumed with HTTP Range when possible) and only
    renamed to its final name after size, SHA-256 (if GitHub publishes it) and ZIP structure
    checks pass.
    """
    cancel = cancel or CancelToken()
    cancel.raise_if_cancelled()
    asset = release.asset
    if not ASSET_RE.match(asset.name):
        raise DownloadError(f"Unexpected asset name: {asset.name}")
    directory.mkdir(parents=True, exist_ok=True)
    final = directory / asset.name
    part = directory / (asset.name + ".part")
    if is_cached(release, directory):
        progress(Progress("Already downloaded and verified", asset.size, asset.size))
        return _local(final, release)

    attempt = 0
    while True:
        attempt += 1
        try:
            _download_attempt(asset.url, part, asset.size, client, progress, cancel)
            break
        except OperationCancelled:
            raise
        except (httpx.HTTPError, DownloadError, OSError) as exc:
            if attempt > retries:
                raise DownloadError(f"Download failed after {attempt} attempts: {exc}") from exc
            progress(Progress(f"Network error, retrying ({attempt}/{retries})…", 0, 0))
            for _ in range(int(backoff * attempt * 10)):
                cancel.raise_if_cancelled()
                time.sleep(0.1)

    size = part.stat().st_size
    if size != asset.size:
        part.unlink(missing_ok=True)
        raise IntegrityError(f"Downloaded size {size} does not match expected {asset.size}.")
    progress(Progress("Verifying checksum…", 0, 0))
    digest = sha256_of(part, cancel)
    if asset.sha256 and digest != asset.sha256:
        part.unlink(missing_ok=True)
        raise IntegrityError(
            "SHA-256 checksum mismatch: the download is corrupt or was tampered with."
        )
    try:
        with zipfile.ZipFile(part) as zf:
            names = zf.namelist()
    except zipfile.BadZipFile as exc:
        part.unlink(missing_ok=True)
        raise IntegrityError("The downloaded file is not a valid ZIP archive.") from exc
    if not any(n.rstrip("/") == "miyoo/app/.tmp_update/onion.pak" for n in names):
        part.unlink(missing_ok=True)
        raise IntegrityError("The downloaded archive does not look like an Onion OS release.")
    os.replace(part, final)
    meta = {
        "name": asset.name,
        "version": release.version,
        "channel": release.channel,
        "tag": release.tag,
        "size": asset.size,
        "sha256": digest,
        "github_digest_verified": bool(asset.sha256),
        "source_url": asset.url,
        "release_page": release.html_url,
        "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    _sidecar(final).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    progress(Progress("Download complete", asset.size, asset.size))
    return _local(final, release, digest)


def _local(path: Path, release: Release, digest: str | None = None) -> LocalArchive:
    return LocalArchive(path, path.stat().st_size, digest or release.asset.sha256, release.version,
                        release.channel, bool(release.asset.sha256))


def _download_attempt(
    url: str, part: Path, expected: int, client: httpx.Client,
    progress: ProgressCallback, cancel: CancelToken,
) -> None:
    have = part.stat().st_size if part.exists() else 0
    if have > expected:
        part.unlink()
        have = 0
    if have == expected:
        return
    headers = {"Accept": "application/octet-stream"}
    if have:
        headers["Range"] = f"bytes={have}-"
    resp = _open_stream(client, url, headers)
    try:
        if resp.status_code == 206 and have:
            mode = "ab"
        elif resp.status_code == 200:
            mode, have = "wb", 0
        elif resp.status_code == 416:
            part.unlink(missing_ok=True)
            raise DownloadError("Server rejected resume request; restarting.")
        else:
            raise DownloadError(f"Server returned HTTP {resp.status_code}.")
        done = have
        with open(part, mode) as out:
            for chunk in resp.iter_bytes(CHUNK):
                cancel.raise_if_cancelled()
                out.write(chunk)
                done += len(chunk)
                if done > expected:
                    raise DownloadError("Server sent more data than expected.")
                progress(Progress(f"Downloading {part.name[:-5]}", done, expected))
        if done < expected:
            raise DownloadError(f"Connection closed early ({done} of {expected} bytes); resuming.")
    finally:
        resp.close()


def describe(archive: LocalArchive) -> dict[str, Any]:
    d = asdict(archive)
    d["path"] = str(archive.path)
    return d
