from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from ...onion.detection import CardInfo
from .. import dialogs
from ..state import AppState
from ..widgets import subtle, title


class Page(QWidget):
    TITLE = ""
    SUBTITLE = ""

    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = state
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        scroll.setWidget(inner)
        outer.addWidget(scroll)
        self.layout_ = QVBoxLayout(inner)
        self.layout_.setContentsMargins(24, 18, 24, 18)
        self.layout_.setSpacing(12)
        self.layout_.addWidget(title(self.TITLE))
        if self.SUBTITLE:
            self.layout_.addWidget(subtle(self.SUBTITLE))

    def require_card(self, *, onion: bool = False) -> CardInfo | None:
        card = self.state.card
        if self.state.target is None or card is None:
            dialogs.info(self, "No SD card selected",
                         "Select a mounted SD card in the bar at the top of the window first.")
            return None
        if onion and card.state.name != "ONION":
            msg = (f"This needs an SD card with Onion OS installed and started at least once.\n\n"
                   f"Selected card: {card.state.label}.")
            if card.state.name == "ONION_INSTALL_PENDING":
                msg += "\n\nInsert the card in your Miyoo and let the installation finish first."
            dialogs.info(self, "Onion OS not detected", msg)
            return None
        return card


def open_url(url: str) -> None:
    QDesktopServices.openUrl(QUrl(url))


def open_path(path: str) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))
