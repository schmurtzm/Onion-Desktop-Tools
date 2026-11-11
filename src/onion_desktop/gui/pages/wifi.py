from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QPushButton,
    QWidget,
)

from ...core.exceptions import ValidationError
from ...linux.network import SavedWifi, get_wifi_password, list_saved_wifi
from ...onion import wifi
from .. import dialogs
from ..state import AppState
from ..widgets import Card, status_label, subtle
from ..worker import run_task
from .base import Page


class WifiPage(Page):
    TITLE = "Wi-Fi"
    SUBTITLE = ("Pre-configure Wi-Fi for a Miyoo Mini Plus. The network is added the next time the console "
                "starts from this card.")

    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(state, parent)
        box = Card("Network")
        form = QFormLayout()
        self.ssid = QLineEdit()
        self.ssid.setMaxLength(32)
        self.ssid.setAccessibleName("Network name (SSID)")
        self.pw = QLineEdit()
        self.pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw.setMaxLength(64)
        self.pw.setAccessibleName("Password")
        self.show_pw = QCheckBox("Show password")
        self.show_pw.toggled.connect(lambda on: self.pw.setEchoMode(
            QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password))
        form.addRow("Network name (SSID):", self.ssid)
        form.addRow("Password:", self.pw)
        form.addRow("", self.show_pw)
        box.body.addLayout(form)
        box.body.addWidget(subtle("Leave the password empty for an open network. WPA passwords are 8–63 "
                                  "characters, or 64 hexadecimal digits."))
        self.err = status_label("", "danger")
        box.body.addWidget(self.err)
        row = QHBoxLayout()
        self.add_btn = QPushButton("Add to SD card")
        self.add_btn.setObjectName("primary")
        self.import_btn = QPushButton("Use a network saved on this computer…")
        row.addWidget(self.add_btn)
        row.addWidget(self.import_btn)
        row.addStretch(1)
        box.body.addLayout(row)
        self.layout_.addWidget(box)
        pend = Card("Pending changes on the card")
        self.pending_lbl = status_label("")
        pend.body.addWidget(self.pending_lbl)
        self.cancel_btn = QPushButton("Cancel pending Wi-Fi changes")
        pend.body.addWidget(self.cancel_btn)
        self.layout_.addWidget(pend)
        note = Card("Privacy")
        note.body.addWidget(subtle("Until the console applies it, the password is stored in plain text on the SD "
                                   "card (.tmp_update/odt_wifi_networks.conf), as it is in the console's own "
                                   "wpa_supplicant.conf. Passwords are never written to this application's logs."))
        self.layout_.addWidget(note)
        self.layout_.addStretch(1)
        self.add_btn.clicked.connect(self._add)
        self.import_btn.clicked.connect(self._import)
        self.cancel_btn.clicked.connect(self._cancel)
        self.ssid.textChanged.connect(self._validate)
        self.pw.textChanged.connect(self._validate)
        state.card_changed.connect(self._refresh)
        self._refresh()
        self._validate()

    def _validate(self) -> bool:
        try:
            if self.ssid.text():
                wifi.validate_ssid(self.ssid.text())
            if self.pw.text():
                wifi.validate_password(self.pw.text())
            self.err.setText("")
            ok = bool(self.ssid.text())
        except ValidationError as exc:
            self.err.setText(exc.message)
            ok = False
        self.add_btn.setEnabled(ok)
        return ok

    def _refresh(self) -> None:
        c = self.state.card
        if c is None or c.state.name != "ONION":
            self.pending_lbl.setText("Select an SD card with Onion OS installed.")
            self.cancel_btn.setEnabled(False)
            return
        n = wifi.pending_ssid_count(c.root)
        pending = wifi.has_pending(c.root)
        self.pending_lbl.setText(f"{n} network(s) waiting to be added on next boot." if pending else
                                 "No pending Wi-Fi changes.")
        self.cancel_btn.setEnabled(pending)

    def _add(self) -> None:
        card = self.require_card(onion=True)
        if not card or not self._validate():
            return
        try:
            wifi.add_network(card.root, self.ssid.text(), self.pw.text())
        except Exception as exc:
            dialogs.error(self, "Cannot configure Wi-Fi", getattr(exc, "message", str(exc)), getattr(exc, "hint", "") or "")
            return
        self.pw.clear()
        dialogs.info(self, "Wi-Fi added", f"'{self.ssid.text()}' will be added when the console next starts "
                                          "from this card.")
        self._refresh()

    def _cancel(self) -> None:
        c = self.state.card
        if c and dialogs.confirm(self, "Cancel Wi-Fi changes", "Remove the pending Wi-Fi networks from the card?"):
            wifi.cancel_pending(c.root)
            self._refresh()

    def _import(self) -> None:
        self.import_btn.setEnabled(False)
        run_task(lambda p, c: list_saved_wifi(), on_success=self._choose,
                 on_error=lambda m, h: dialogs.error(self, "Cannot read saved networks", m,
                                                     h or "NetworkManager is required for this feature."),
                 on_done=lambda: self.import_btn.setEnabled(True))

    def _choose(self, nets: list[SavedWifi]) -> None:
        if not nets:
            dialogs.info(self, "No saved networks", "NetworkManager has no saved Wi-Fi networks.")
            return
        names = [n.ssid for n in nets]
        name, ok = QInputDialog.getItem(self, "Saved networks", "Network:", names, 0, False)
        if not ok:
            return
        net = nets[names.index(name)]
        self.ssid.setText(net.ssid)
        self.pw.clear()
        if net.has_psk and dialogs.confirm(
                self, "Read stored password",
                f"Also read the password stored for '{net.ssid}'?\n\nYour system may ask you to authenticate. "
                "The password is only placed in the field below; it is not saved by this application.",
                warning=False, yes_text="Read password"):
            run_task(lambda p, c: get_wifi_password(net), on_success=self.pw.setText,
                     on_error=lambda m, h: dialogs.error(self, "Password not available", m, h))
