"""Contract tests: the exact D-Bus calls issued to UDisks2 and NetworkManager.

No system bus exists in CI, so these pin method names, signatures and the Polkit
interactive-authorisation flag against the documented UDisks2 / NM APIs.
"""

import pytest

from onion_desktop.linux import network
from onion_desktop.linux.udisks2 import I_BLOCK, I_DRIVE, I_FS, I_PTABLE, UDisks2Client, probe


class Rec:
    def __init__(self, replies=None):
        self.calls = []
        self.replies = replies or {}

    def call(self, path, interface, method, signature, body, *, interactive=False, timeout=30.0):
        self.calls.append((path, interface, method, signature, body, interactive))
        return self.replies.get(method, (True,))


def test_operations_signatures():
    t = Rec({"Mount": ("/run/media/u/ONION",), "CreatePartitionAndFormat": ("/b/sdb1",),
             "Get": (("s", "2.10.1"),), "GetManagedObjects": ({},)})
    c = UDisks2Client(t)
    assert c.mount("/b/sdb1") == "/run/media/u/ONION"
    c.unmount("/b/sdb1")
    c.check("/b/sdb1")
    c.repair("/b/sdb1")
    c.create_dos_table("/b/sdb")
    assert c.create_fat32_partition("/b/sdb", "ONION", True) == "/b/sdb1"
    c.power_off("/d/1")
    c.eject("/d/1")
    assert c.version() == (2, 10, 1)
    sig = {(m, i): (s, inter) for _p, i, m, s, _b, inter in t.calls}
    assert sig[("Mount", I_FS)] == ("a{sv}", True)
    assert sig[("Unmount", I_FS)] == ("a{sv}", True)
    assert sig[("Check", I_FS)] == ("a{sv}", True)
    assert sig[("Repair", I_FS)] == ("a{sv}", True)
    assert sig[("Format", I_BLOCK)] == ("sa{sv}", True)
    assert sig[("CreatePartitionAndFormat", I_PTABLE)] == ("ttsssa{sv}sa{sv}", True)
    assert sig[("PowerOff", I_DRIVE)] == ("a{sv}", True)
    fmt = next(c for c in t.calls if c[2] == "Format")
    assert fmt[4][0] == "dos"
    cpf = next(c for c in t.calls if c[2] == "CreatePartitionAndFormat")
    offset, size, ptype, _name, _opts, fstype, fopts = cpf[4]
    assert (offset, size, ptype, fstype) == (1024 * 1024, 0, "0x0c", "vfat")
    assert fopts["label"] == ("s", "ONION") and fopts["mkfs-args"] == ("as", ["-F", "32"])
    for call in t.calls:
        opts = call[4][-1] if call[2] not in ("Get", "CreatePartitionAndFormat") else None
        if isinstance(opts, dict):
            assert opts["auth.no_user_interaction"] == ("b", False)


def test_probe_returns_none_when_unavailable():
    from onion_desktop.core.exceptions import BackendUnavailableError

    class Down:
        def call(self, *a, **k):
            raise BackendUnavailableError("no bus")
    assert probe(lambda: UDisks2Client(Down())) is None


def test_nm_parse_and_secret_flow(monkeypatch):
    settings = {"connection": {"type": ("s", "802-11-wireless"), "id": ("s", "Home")},
                "802-11-wireless": {"ssid": ("ay", b"Caf\xc3\xa9")},
                "802-11-wireless-security": {"key-mgmt": ("s", "wpa-psk")}}
    w = network.parse_wifi_settings(settings, "/c/1")
    assert w and w.ssid == "Café" and w.has_psk
    assert network.parse_wifi_settings({"connection": {"type": ("s", "802-3-ethernet")}}, "/c/2") is None
    calls = []

    def fake_call(path, iface, method, sig, body, interactive=False):
        calls.append((method, sig, body, interactive))
        if method == "ListConnections":
            return (["/c/1"],)
        if method == "GetSettings":
            return (settings,)
        if method == "GetSecrets":
            return ({"802-11-wireless-security": {"psk": ("s", "hunter2hunter2")}},)
        raise AssertionError(method)
    monkeypatch.setattr(network, "_call", fake_call)
    nets = network.list_saved_wifi()
    assert [n.ssid for n in nets] == ["Café"]
    assert not any(c[0] == "GetSecrets" for c in calls), "listing must never read secrets"
    assert network.get_wifi_password(nets[0]) == "hunter2hunter2"
    assert calls[-1] == ("GetSecrets", "s", ("802-11-wireless-security",), True)


def test_nm_missing_secret(monkeypatch):
    from onion_desktop.core.exceptions import OdtError
    monkeypatch.setattr(network, "_call", lambda *a, **k: ({},))
    with pytest.raises(OdtError):
        network.get_wifi_password(network.SavedWifi("x", "/c/1", True))
