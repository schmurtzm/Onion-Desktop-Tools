import httpx
import pytest

from onion_desktop.core.exceptions import ReleaseMetadataError
from onion_desktop.onion.releases import (
    discover,
    is_allowed_download_url,
    make_client,
    parse_release,
    select_channels,
)

SHA = "a" * 64


def rel(tag, pre=False, name=None, url=None, size=1000, digest=f"sha256:{SHA}", draft=False):
    name = name or f"Onion-v{tag.lstrip('v')}.zip"
    url = url or f"https://github.com/OnionUI/Onion/releases/download/{tag}/{name}"
    return {"tag_name": tag, "name": f"Onion {tag}", "prerelease": pre, "draft": draft,
            "html_url": f"https://github.com/OnionUI/Onion/releases/tag/{tag}", "body": "notes",
            "published_at": "2025-01-01T00:00:00Z",
            "assets": [{"name": "other.txt", "browser_download_url": "https://github.com/x", "size": 1},
                       {"name": name, "browser_download_url": url, "size": size, "digest": digest}]}


def test_parse_valid():
    r = parse_release(rel("v4.3.1-1"))
    assert r and r.version == "4.3.1-1" and r.asset.sha256 == SHA and r.channel == "stable"


def test_parse_skips_draft_and_assetless():
    assert parse_release(rel("v1.0.0", draft=True)) is None
    data = rel("v1.0.0")
    data["assets"] = [data["assets"][0]]
    assert parse_release(data) is None


@pytest.mark.parametrize("url", [
    "http://github.com/OnionUI/Onion/releases/download/v1/Onion-v1.0.0.zip",
    "https://evil.example/OnionUI/Onion/releases/download/v1/Onion-v1.0.0.zip",
    "https://github.com/attacker/Onion/releases/download/v1/Onion-v1.0.0.zip",
    "https://github.com/OnionUI/Onion/releases/download/v1/Other.zip",
])
def test_rejects_untrusted_urls(url):
    with pytest.raises(ReleaseMetadataError):
        parse_release(rel("v1.0.0", url=url))


def test_bad_digest_ignored_and_size_validated():
    assert parse_release(rel("v1.0.0", digest="md5:xyz")).asset.sha256 is None
    with pytest.raises(ReleaseMetadataError):
        parse_release(rel("v1.0.0", size=0))


def test_select_channels():
    rs = [parse_release(rel("v4.4.0-beta", pre=True)), parse_release(rel("v4.3.1"))]
    ch = select_channels(rs)
    assert ch.beta.version == "4.4.0-beta" and ch.stable.version == "4.3.1"


def test_allowed_hosts():
    assert is_allowed_download_url("https://objects.githubusercontent.com/abc")
    assert not is_allowed_download_url("https://objects.githubusercontent.com.evil.io/abc")
    assert not is_allowed_download_url("ftp://github.com/x")


def test_discover_with_mock_transport():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/releases/latest"):
            return httpx.Response(200, json=rel("v4.3.1"))
        return httpx.Response(200, json=[rel("v4.4.0-beta", pre=True), rel("v4.3.1"), {"bogus": 1}])
    with make_client(transport=httpx.MockTransport(handler)) as c:
        ch = discover(c)
    assert ch.stable.version == "4.3.1" and ch.beta.prerelease


def test_rate_limit_message():
    def handler(request):
        return httpx.Response(403, headers={"x-ratelimit-remaining": "0"})
    with make_client(transport=httpx.MockTransport(handler)) as c, pytest.raises(ReleaseMetadataError) as e:
        discover(c)
    assert "rate limit" in e.value.message
