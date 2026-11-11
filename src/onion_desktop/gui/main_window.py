from __future__ import annotations

from importlib import resources
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME
from .pages.about import AboutPage
from .pages.backup import BackupPage
from .pages.configuration import ConfigurationPage
from .pages.dashboard import DashboardPage
from .pages.emulators import EmulatorsPage
from .pages.install import InstallPage
from .pages.sdcards import SdCardsPage
from .pages.settings_page import SettingsPage
from .pages.wifi import WifiPage
from .state import AppState, Target

PAGES = [
    ("dashboard", "Dashboard"),
    ("sdcards", "SD Cards"),
    ("install", "Install / Update"),
    ("emulators", "Emulators & Apps"),
    ("configuration", "Configuration"),
    ("wifi", "Wi-Fi"),
    ("backup", "Backup & Restore"),
    ("settings", "Settings"),
    ("about", "About"),
]


def app_icon(name: str = "onion.ico") -> QIcon:
    with resources.as_file(resources.files("onion_desktop.resources").joinpath(name)) as p:
        return QIcon(str(Path(p)))


class MainWindow(QMainWindow):
    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.resize(1100, 760)
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(210)
        self.sidebar.setIconSize(QSize(18, 18))
        self.sidebar.setAccessibleName("Navigation")
        root.addWidget(self.sidebar)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        root.addLayout(right, 1)
        bar = QWidget()
        bar_l = QHBoxLayout(bar)
        bar_l.setContentsMargins(16, 10, 16, 6)
        bar_l.addWidget(QLabel("SD card:"))
        self.target_combo = QComboBox()
        self.target_combo.setAccessibleName("Selected SD card")
        self.target_combo.setMinimumWidth(420)
        bar_l.addWidget(self.target_combo, 1)
        folder_btn = QPushButton("Folder…")
        folder_btn.setToolTip("Use a folder (e.g. a card mounted elsewhere) as the target")
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setToolTip("Rescan devices (F5)")
        bar_l.addWidget(folder_btn)
        bar_l.addWidget(refresh_btn)
        right.addWidget(bar)

        self.stack = QStackedWidget()
        right.addWidget(self.stack, 1)
        self.pages: dict[str, QWidget] = {}
        factories = {
            "dashboard": lambda: DashboardPage(state, self.navigate),
            "sdcards": lambda: SdCardsPage(state, self.navigate),
            "install": lambda: InstallPage(state),
            "emulators": lambda: EmulatorsPage(state),
            "configuration": lambda: ConfigurationPage(state),
            "wifi": lambda: WifiPage(state),
            "backup": lambda: BackupPage(state),
            "settings": lambda: SettingsPage(state),
            "about": lambda: AboutPage(state),
        }
        for key, label in PAGES:
            page = factories[key]()
            self.pages[key] = page
            self.stack.addWidget(page)
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.sidebar.addItem(item)
        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

        self._extra_folder: Target | None = None
        self._updating_combo = False
        self.target_combo.currentIndexChanged.connect(self._combo_changed)
        folder_btn.clicked.connect(self._choose_folder)
        refresh_btn.clicked.connect(self._refresh)
        QShortcut(QKeySequence.StandardKey.Refresh, self, activated=self._refresh)
        for i in range(min(9, len(PAGES))):
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self, activated=lambda i=i: self.sidebar.setCurrentRow(i))
        state.disks_changed.connect(self._fill_combo)
        state.target_changed.connect(self._fill_combo)
        self._fill_combo()

    def navigate(self, key: str) -> None:
        for i, (k, _label) in enumerate(PAGES):
            if k == key:
                self.sidebar.setCurrentRow(i)

    def _refresh(self) -> None:
        self.state.refresh()
        self.state.reload_card()

    def _fill_combo(self) -> None:
        self._updating_combo = True
        self.target_combo.clear()
        self.target_combo.addItem("— No SD card selected —", None)
        targets = self.state.candidate_targets()
        if self._extra_folder:
            targets.append(self._extra_folder)
        for t in targets:
            self.target_combo.addItem(t.label, t)
        cur = self.state.target
        idx = 0
        for i in range(1, self.target_combo.count()):
            t = self.target_combo.itemData(i)
            if cur is not None and t.path == cur.path:
                idx = i
        self.target_combo.setCurrentIndex(idx)
        self._updating_combo = False

    def _combo_changed(self, idx: int) -> None:
        if self._updating_combo:
            return
        self.state.set_target(self.target_combo.itemData(idx), user=True)

    def _choose_folder(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select the root folder of the SD card")
        if d:
            self._extra_folder = Target(Path(d), None, None)
            self.state.set_target(self._extra_folder, user=True)
            self._fill_combo()
