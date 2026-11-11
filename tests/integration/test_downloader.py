import hashlib
import io
import json

import httpx
import pytest

from conftest import make_release_zip
from onion_desktop.core.exceptions import DownloadError, IntegrityError, OperationCancelled
from onion_desktop.core.progress import CancelToken
from onion_desktop.onion.downloader import download_release, is_cached, list_local_archives
from onion_desktop.onion.releases import Release, ReleaseAsset, make_client

URL = "https://github.com/OnionUI/Onion/releases/download/v4.3.1/Onion-v4.3.1.zip"
CDN = "https://release-assets.githubusercontent.com/abc"


@pytest.fixture
def payload(tmp_path):
    return make_release_zip(tmp_path / "src.zip").read_bytes()


def release(data, sha=True):
    return Release("v4.3.1", "Onion", "4.3.1", False, "https://github.com/OnionUI/Onion/releases", "", "",
                   ReleaseAsset("Onion-v4.3.1.zip", URL, len(data),
                                hashlib.sha256(data).hexdigest() if sha else None))


def server(data, *, redirect_to=CDN, fail_first=0, honour_range=True, corrupt=False):
    state = {"n": 0}

    def handler(req: httpx.Request):
        if str(req.url) == URL:
            return httpx.Response(302, headers={"location": redirect_to})
        state["n"] += 1
        body = bytearray(data)
        if corrupt:
            body[-10] ^= 0xFF
        if state["n"] <= fail_first:
            return httpx.Response(200, content=bytes(body[: len(body) // 2]))  # truncated
        rng = req.headers.get("range")
        if rng and honour_range:
            start = int(rng.split("=")[1].rstrip("-"))
            return httpx.Response(206, content=bytes(body[start:]))
        return httpx.Response(200, content=bytes(body))
    return httpx.MockTransport(handler), state


def test_download_ok_and_cached(tmp_path, payload):
    t, _ = server(payload)
    rel = release(payload)
    with make_client(transport=t) as c:
        arc = download_release(rel, tmp_path / "dl", c)
    assert arc.path.read_bytes() == payload and arc.verified_against_github_digest
    meta = json.loads((tmp_path / "dl/Onion-v4.3.1.zip.json").read_text())
    assert meta["sha256"] == hashlib.sha256(payload).hexdigest()
    assert is_cached(rel, tmp_path / "dl")
    assert list_local_archives(tmp_path / "dl")[0].version == "4.3.1"


def test_resume_after_truncation(tmp_path, payload):
    t, state = server(payload, fail_first=1)
    with make_client(transport=t) as c:
        arc = download_release(release(payload), tmp_path / "dl", c, backoff=0)
    assert arc.path.read_bytes() == payload and state["n"] == 2


def test_checksum_mismatch_rejected(tmp_path, payload):
    t, _ = server(payload, corrupt=True)
    with make_client(transport=t) as c, pytest.raises(IntegrityError):
        download_release(release(payload), tmp_path / "dl", c)
    assert not (tmp_path / "dl/Onion-v4.3.1.zip").exists()
    assert not (tmp_path / "dl/Onion-v4.3.1.zip.part").exists()


def test_untrusted_redirect_rejected(tmp_path, payload):
    t, _ = server(payload, redirect_to="https://evil.example/x")
    with make_client(transport=t) as c, pytest.raises(DownloadError):
        download_release(release(payload), tmp_path / "dl", c, retries=0)


def test_not_an_onion_archive(tmp_path):
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("x.txt", "x")
    data = buf.getvalue()
    t, _ = server(data)
    with make_client(transport=t) as c, pytest.raises(IntegrityError):
        download_release(release(data, sha=False), tmp_path / "dl", c)


def test_cancel(tmp_path, payload):
    t, _ = server(payload)
    tok = CancelToken()
    tok.cancel()
    with make_client(transport=t) as c, pytest.raises(OperationCancelled):
        download_release(release(payload), tmp_path / "dl", c, cancel=tok)
