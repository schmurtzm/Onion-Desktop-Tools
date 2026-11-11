"""NetworkManager integration (replacement for upstream ``netsh wlan export key=clear``).

Listing saved Wi-Fi networks reads only names. A password is fetched only for one network,
only when the user explicitly asks, through NetworkManager's ``GetSecrets`` (which is itself
Polkit-protected). Secrets are returned to the caller and never logged or written to disk.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..core.exceptions import BackendUnavailableError, OdtError

NM = "org.freedesktop.NetworkManager"
SETTINGS = "/org/freedesktop/NetworkManager/Settings"


@dataclass(frozen=True)
class SavedWifi:
    ssid: str
    connection_path: str
    has_psk: bool


def _call(path: str, iface: str, method: str, sig: str | None, body: tuple[Any, ...],
          interactive: bool = False) -> tuple[Any, ...]:
    try:
        from jeepney import DBusAddress, MessageFlag, new_method_call
        from jeepney.io.blocking import open_dbus_connection
        from jeepney.wrappers import DBusErrorResponse, unwrap_msg
    except ImportError as exc:  # pragma: no cover
        raise BackendUnavailableError("The 'jeepney' D-Bus library is not available.") from exc
    msg = new_method_call(DBusAddress(path, bus_name=NM, interface=iface), method, sig, body)
    if interactive:
        msg.header.flags |= MessageFlag.allow_interactive_authorization
    try:
        conn = open_dbus_connection(bus="SYSTEM")
    except (OSError, ConnectionError, KeyError, ValueError) as exc:
        raise BackendUnavailableError(f"Cannot connect to the D-Bus system bus: {exc}") from exc
    try:
        result: tuple[Any, ...] = unwrap_msg(conn.send_and_get_reply(msg, timeout=60))
        return result
    except DBusErrorResponse as exc:
        if getattr(exc, "name", "") == "org.freedesktop.DBus.Error.ServiceUnknown":
            raise BackendUnavailableError("NetworkManager is not running.") from exc
        raise OdtError(f"NetworkManager error: {exc.data[0] if exc.data else exc}") from exc
    finally:
        conn.close()


def _v(x: Any) -> Any:
    return x[1] if isinstance(x, tuple) and len(x) == 2 and isinstance(x[0], str) else x


def decode_ssid(raw: Any) -> str:
    data = bytes(raw) if isinstance(raw, (bytes, bytearray, list)) else str(raw).encode()
    return data.decode("utf-8", "replace")


def parse_wifi_settings(settings: dict[str, dict[str, Any]], path: str) -> SavedWifi | None:
    conn = {k: _v(v) for k, v in settings.get("connection", {}).items()}
    if conn.get("type") != "802-11-wireless":
        return None
    wifi = {k: _v(v) for k, v in settings.get("802-11-wireless", {}).items()}
    ssid = decode_ssid(wifi.get("ssid", b""))
    sec = {k: _v(v) for k, v in settings.get("802-11-wireless-security", {}).items()}
    has_psk = sec.get("key-mgmt") in ("wpa-psk", "sae")
    return SavedWifi(ssid, path, has_psk) if ssid else None


def list_saved_wifi() -> list[SavedWifi]:
    (paths,) = _call(SETTINGS, f"{NM}.Settings", "ListConnections", None, ())
    out = []
    for p in paths:
        (settings,) = _call(str(p), f"{NM}.Settings.Connection", "GetSettings", None, ())
        w = parse_wifi_settings(settings, str(p))
        if w:
            out.append(w)
    return sorted(out, key=lambda w: w.ssid.lower())


def get_wifi_password(net: SavedWifi) -> str:
    """Explicit, user-initiated secret retrieval (may trigger a Polkit prompt)."""
    (secrets,) = _call(net.connection_path, f"{NM}.Settings.Connection", "GetSecrets", "s",
                       ("802-11-wireless-security",), interactive=True)
    sec = {k: _v(v) for k, v in secrets.get("802-11-wireless-security", {}).items()}
    psk = sec.get("psk")
    if not isinstance(psk, str):
        raise OdtError("No password is stored for this network (or access was denied).")
    return psk
