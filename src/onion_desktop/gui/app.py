"""QApplication bootstrap."""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from .. import APP_ID, APP_NAME, __version__
from ..settings import Settings
from .main_window import MainWindow, app_icon
from .state import AppState
from .themes import apply_theme


def create_app(argv: list[str] | None = None) -> QApplication:
    if os.environ.get("WAYLAND_DISPLAY") and not os.environ.get("QT_QPA_PLATFORM"):
        os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication.instance() or QApplication(argv or sys.argv)
    assert isinstance(app, QApplication)
    app.setApplicationName(APP_ID)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setDesktopFileName(APP_ID)
    app.setWindowIcon(app_icon())
    return app


def run(settings: Settings) -> int:
    app = create_app()
    apply_theme(app, settings.theme)
    state = AppState(settings)
    win = MainWindow(state)
    win.show()
    state.start()
    if settings.check_updates_on_start:
        about = win.pages["about"]
        about.check()  # type: ignore[attr-defined]
    return int(app.exec())
