from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QWidget

from ...core.models import human_size
from ...onion.detection import CardState
from ..state import AppState
from ..widgets import Card, status_label
from .base import Page


class DashboardPage(Page):
    TITLE = "Dashboard"
    SUBTITLE = "Prepare, update, configure and back up Onion OS SD cards for the Miyoo Mini / Mini Plus."

    def __init__(self, state: AppState, navigate: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__(state, parent)
        self.navigate = navigate
        self.card_box = Card("Selected SD card")
        grid = QGridLayout()
        self.fields: dict[str, QLabel] = {}
        for row, key in enumerate(["Location", "Device", "Content", "Onion version", "File system", "Free space"]):
            grid.addWidget(QLabel(f"{key}:"), row, 0)
            lbl = status_label("—")
            self.fields[key] = lbl
            grid.addWidget(lbl, row, 1)
        grid.setColumnStretch(1, 1)
        grid.setHorizontalSpacing(18)
        self.card_box.body.addLayout(grid)
        self.hint = status_label("", "warning")
        self.card_box.body.addWidget(self.hint)
        self.layout_.addWidget(self.card_box)

        self.devices_box = Card("Detected removable devices")
        self.devices_lbl = status_label("Scanning…")
        self.devices_box.body.addWidget(self.devices_lbl)
        self.layout_.addWidget(self.devices_box)

        actions = Card("Common tasks")
        row1, row2 = QHBoxLayout(), QHBoxLayout()
        for text, page, row in [("Install / update Onion", "install", row1), ("Format an SD card", "sdcards", row1),
                                ("Back up / restore", "backup", row1), ("Emulators && apps", "emulators", row2),
                                ("Onion settings", "configuration", row2), ("Wi-Fi", "wifi", row2)]:
            b = QPushButton(text)
            b.clicked.connect(lambda _=False, p=page: self.navigate(p))
            row.addWidget(b)
        actions.body.addLayout(row1)
        actions.body.addLayout(row2)
        self.layout_.addWidget(actions)
        self.layout_.addStretch(1)
        state.card_changed.connect(self.refresh)
        state.target_changed.connect(self.refresh)
        state.disks_changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        t, c = self.state.target, self.state.card
        f = self.fields
        f["Location"].setText(str(t.path) if t else "No card selected")
        f["Device"].setText(f"{t.partition.device} on {t.disk.display_name}" if t and t.disk and t.partition else "—")
        f["Content"].setText(c.state.label if c else ("Reading…" if t else "—"))
        f["Onion version"].setText(c.version_label if c and c.state in (CardState.ONION, CardState.ONION_INSTALL_PENDING)
                                   else "—")
        f["File system"].setText((c.fs_type or "unknown") if c else "—")
        f["Free space"].setText(f"{human_size(c.free_bytes)} of {human_size(c.total_bytes)}" if c else "—")
        hint = ""
        if c is not None:
            if c.fs_type and c.fs_type != "vfat":
                hint = "This card is not FAT32. Onion requires FAT32 — format it on the SD Cards page."
            elif c.state is CardState.ONION_INSTALL_PENDING:
                hint = "Onion files are on the card. Insert it in your Miyoo to run the installation."
            elif c.update_pending:
                hint = "An Onion update is waiting to be applied on the console."
            elif c.state is CardState.STOCK:
                hint = "Stock card detected. Use a new card for Onion and migrate with Backup & Restore."
        self.hint.setText(hint)
        self.hint.setVisible(bool(hint))
        removable = [d for d in self.state.disks if not d.protected_reasons]
        if self.state.poll_error:
            self.devices_lbl.setText(f"Device detection problem: {self.state.poll_error}")
        elif not removable:
            self.devices_lbl.setText("No removable storage found. Insert an SD card (or card reader).")
        else:
            self.devices_lbl.setText("\n".join(
                f"{d.device} — {d.display_name} — {human_size(d.size)} — "
                + (", ".join(f"{p.device} {p.fs_version or p.fs_type or '?'} "
                             f"{'@ ' + p.mount_point if p.mount_point else '(not mounted)'}" for p in d.partitions)
                   or "no partitions")
                for d in removable))
