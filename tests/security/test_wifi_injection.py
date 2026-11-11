import pytest

from onion_desktop.core.exceptions import ValidationError
from onion_desktop.onion import wifi


@pytest.mark.parametrize("ssid", ['My"Net', "$(reboot)", "`id`", "a\\b", "café"])
def test_special_ssids_are_hex_encoded_or_safe(ssid):
    block = wifi.network_block(ssid, "password123")
    line = next(x for x in block.splitlines() if "ssid=" in x).strip()
    if any(c in ssid for c in '"\\') or not ssid.isascii():
        assert line == f"ssid={ssid.encode().hex()}"
    else:
        assert line == f'ssid="{ssid}"'


def test_password_validation():
    for bad in ["short", "x" * 64, "pässwörd123", "abc\ndefgh"]:
        with pytest.raises(ValidationError):
            wifi.validate_password(bad)
    assert wifi.validate_password("") == ""
    assert wifi.validate_password("f" * 64) == "f" * 64
    with pytest.raises(ValidationError):
        wifi.validate_ssid("x" * 33)
    with pytest.raises(ValidationError):
        wifi.validate_ssid("a\nb")


def test_hook_script_never_contains_credentials(onion_card):
    secret_ssid, secret_pw = '"; rm -rf /mnt/SDCARD; "', "pa$$`w0rd`\"x"
    wifi.add_network(onion_card, secret_ssid, secret_pw)
    hook = (onion_card / wifi.RUNTIME).read_text()
    assert hook == wifi.HOOK_SCRIPT
    assert "rm -rf" not in hook and "pa$$" not in hook
    data = (onion_card / wifi.PENDING_FILE).read_text()
    assert f"ssid={secret_ssid.encode().hex()}" in data
    assert 'psk="pa$$`w0rd`"x"' in data
