from __future__ import annotations

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)

from ... import paths
from ...settings import THEMES
from ..state import AppState
from ..themes import apply_theme
from .base import Page, open_path


class SettingsPage(Page):
    TITLE = "Settings"

    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(state, parent)
        s = state.settings
        form = QFormLayout()
        self.theme = QComboBox()
        self.theme.addItems([t.capitalize() if t != "dracula" else "Dracula (dark)" for t in THEMES])
        self.theme.setCurrentIndex(THEMES.index(s.theme))
        form.addRow("Theme:", self.theme)
        self.dl = self._dir_row(form, "Downloads folder:", str(s.downloads_path))
        self.bk = self._dir_row(form, "Backups folder:", str(s.backups_path))
        self.updates = QCheckBox("Check for Onion Desktop Tools updates at startup (contacts GitHub)")
        self.updates.setChecked(s.check_updates_on_start)
        form.addRow("", self.updates)
        self.layout_.addLayout(form)
        row = QHBoxLayout()
        logs = QPushButton("Open log folder")
        logs.clicked.connect(lambda: (paths.log_dir().mkdir(parents=True, exist_ok=True), open_path(str(paths.log_dir()))))
        row.addWidget(logs)
        row.addStretch(1)
        self.layout_.addLayout(row)
        self.layout_.addStretch(1)
        self.theme.currentIndexChanged.connect(self._save)
        self.updates.toggled.connect(self._save)

    def _dir_row(self, form: QFormLayout, label: str, value: str) -> QLineEdit:
        row = QHBoxLayout()
        edit = QLineEdit(value)
        edit.setReadOnly(True)
        btn = QPushButton("Change…")
        row.addWidget(edit, 1)
        row.addWidget(btn)
        form.addRow(label, row)

        def pick() -> None:
            d = QFileDialog.getExistingDirectory(self, label, edit.text())
            if d:
                edit.setText(d)
                self._save()
        btn.clicked.connect(pick)
        return edit

    def _save(self) -> None:
        s = self.state.settings
        s.theme = THEMES[self.theme.currentIndex()]
        s.downloads_dir = self.dl.text()
        s.backups_dir = self.bk.text()
        s.check_updates_on_start = self.updates.isChecked()
        self.state.save_settings()
        app = QApplication.instance()
        if isinstance(app, QApplication):
            apply_theme(app, s.theme)
