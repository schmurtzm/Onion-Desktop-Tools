from __future__ import annotations

from importlib import resources
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...onion.emulators import (
    Package,
    PackageOpReport,
    PackageStatus,
    install_package,
    scan_packages,
    uninstall_package,
)
from .. import dialogs
from ..state import AppState
from ..widgets import TaskPanel, status_label
from ..worker import run_task
from .base import Page, open_path

COLORS = {PackageStatus.INSTALLED: QColor(48, 164, 108, 90), PackageStatus.ROMS_PRESENT: QColor(230, 140, 40, 100)}


class EmulatorsPage(Page):
    TITLE = "Emulators & Apps"
    SUBTITLE = ("Onion's package manager from your desktop. Green: installed. Orange: not installed but ROMs "
                "for it are on the card. Removing an emulator never deletes your ROMs or files you added.")

    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(state, parent)
        top = QHBoxLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["All", "Emu", "RApp", "App"])
        self.type_combo.setAccessibleName("Package type")
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter…")
        self.filter.setAccessibleName("Filter packages")
        self.status_filter = QComboBox()
        self.status_filter.addItems(["Any status", "Installed", "ROMs present", "Not installed"])
        top.addWidget(self.type_combo)
        top.addWidget(self.status_filter)
        top.addWidget(self.filter, 1)
        self.layout_.addLayout(top)
        self.counts = status_label("")
        self.layout_.addWidget(self.counts)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Package", "Type", "Folder", "ROM folder", "Status"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.setMinimumHeight(380)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.cellDoubleClicked.connect(self._open)
        self.layout_.addWidget(self.table)
        row = QHBoxLayout()
        self.btns = {k: QPushButton(t) for k, t in [("refresh", "Refresh"), ("install", "Install selected"),
                                                     ("auto", "Auto-install (orange)"), ("remove", "Uninstall selected"),
                                                     ("help", "Help")]}
        self.btns["install"].setToolTip("Install the selected rows (Ctrl/Shift for multiple selection).")
        self.btns["auto"].setToolTip("Install every emulator whose ROMs are already on the card (orange rows).")
        for k in ("refresh", "install", "auto", "remove"):
            row.addWidget(self.btns[k])
        row.addStretch(1)
        row.addWidget(self.btns["help"])
        self.layout_.addLayout(row)
        self.panel = TaskPanel()
        self.layout_.addWidget(self.panel)
        self.packages: list[Package] = []
        self.btns["refresh"].clicked.connect(self.reload)
        self.btns["install"].clicked.connect(lambda: self._install(self._selected()))
        self.btns["auto"].clicked.connect(
            lambda: self._install([p for p in self.packages if p.status is PackageStatus.ROMS_PRESENT]))
        self.btns["remove"].clicked.connect(self._uninstall)
        self.btns["help"].clicked.connect(self._help)
        self.type_combo.currentIndexChanged.connect(self._apply_filter)
        self.status_filter.currentIndexChanged.connect(self._apply_filter)
        self.filter.textChanged.connect(self._apply_filter)
        state.card_changed.connect(self.reload)

    def reload(self) -> None:
        card = self.state.card
        self.table.setRowCount(0)
        self.packages = []
        if card is None or card.state.name != "ONION":
            self.counts.setText("Select an SD card with Onion OS installed.")
            return
        root = card.root
        run_task(lambda p, c: scan_packages(root), on_success=self._fill,
                 on_error=lambda m, h: dialogs.error(self, "Cannot read packages", m, h))

    def _fill(self, pkgs: list[Package]) -> None:
        self.packages = pkgs
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(pkgs))
        label = {PackageStatus.INSTALLED: "Installed", PackageStatus.ROMS_PRESENT: "ROMs present",
                 PackageStatus.NOT_INSTALLED: "Not installed"}
        for r, p in enumerate(pkgs):
            vals = [p.name, p.pack_type, p.folder, p.rom_folder,
                    label[p.status] + (" (device script)" if p.has_device_script else "")]
            for col, v in enumerate(vals):
                it = QTableWidgetItem(v)
                it.setData(Qt.ItemDataRole.UserRole, r)
                if p.status in COLORS:
                    it.setBackground(QBrush(COLORS[p.status]))
                self.table.setItem(r, col, it)
        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()
        if not pkgs:
            self.counts.setText("No package data found on this card (App/PackageManager/data).")
        else:
            n = {s: sum(1 for p in pkgs if p.status is s) for s in PackageStatus}
            self.counts.setText(f"Not installed: {n[PackageStatus.NOT_INSTALLED]} · Installed: "
                                f"{n[PackageStatus.INSTALLED]} · Not installed but ROMs present: "
                                f"{n[PackageStatus.ROMS_PRESENT]}")
        self._apply_filter()

    def _apply_filter(self) -> None:
        text = self.filter.text().strip().lower()
        typ = self.type_combo.currentText()
        st = self.status_filter.currentIndex()
        want = {1: PackageStatus.INSTALLED, 2: PackageStatus.ROMS_PRESENT, 3: PackageStatus.NOT_INSTALLED}.get(st)
        for r in range(self.table.rowCount()):
            p = self._pkg_at(r)
            hay = " ".join([p.name, p.pack_type, p.folder, p.rom_folder]).lower()
            visible = ((not text or text in hay) and (typ == "All" or p.pack_type == typ)
                       and (want is None or p.status is want))
            self.table.setRowHidden(r, not visible)

    def _pkg_at(self, row: int) -> Package:
        return self.packages[self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)]

    def _selected(self) -> list[Package]:
        rows = sorted({i.row() for i in self.table.selectedItems()})
        return [self._pkg_at(r) for r in rows if not self.table.isRowHidden(r)]

    def _open(self, row: int, col: int) -> None:
        card = self.state.card
        if not card:
            return
        p = self._pkg_at(row)
        path = card.root / ("Roms/" + p.rom_folder if col == 3 and p.rom_folder else f"{p.pack_type}/{p.folder}")
        if path.is_dir():
            open_path(str(path))
        else:
            dialogs.info(self, "Folder not found", f"{path} does not exist (package not installed?).")

    def _install(self, pkgs: list[Package]) -> None:
        card = self.require_card(onion=True)
        if not card:
            return
        pkgs = [p for p in pkgs if p.status is not PackageStatus.INSTALLED]
        if not pkgs:
            dialogs.info(self, "Nothing to install", "Select one or more packages that are not installed yet.")
            return
        msg = "Install these packages?\n\n" + "\n".join(f"• {p.name}" for p in pkgs[:40])
        if len(pkgs) > 40:
            msg += f"\n… and {len(pkgs) - 40} more"
        if any(p.has_device_script for p in pkgs):
            msg += ("\n\nSome packages include a setup script that only the console can run; open the Package "
                    "Manager on the Miyoo afterwards if they do not work.")
        if not dialogs.confirm(self, "Install packages", msg, warning=False, yes_text="Install"):
            return
        root = card.root

        def work(progress, cancel):  # type: ignore[no-untyped-def]
            return [install_package(root, p, progress=progress, cancel=cancel) for p in pkgs]
        self._run(work, "Installation")

    def _uninstall(self) -> None:
        card = self.require_card(onion=True)
        if not card:
            return
        pkgs = [p for p in self._selected() if p.status is PackageStatus.INSTALLED]
        if not pkgs:
            dialogs.info(self, "Nothing to uninstall", "Select one or more installed (green) packages.")
            return
        msg = ("Uninstall these packages?\n\n" + "\n".join(f"• {p.name}" for p in pkgs[:40]) +
               "\n\nOnly the files that came with each package are removed. Your ROMs, saves and any files "
               "you added are kept.")
        if not dialogs.confirm(self, "Uninstall packages", msg, yes_text="Uninstall"):
            return
        root = card.root
        self._run(lambda pr, c: [uninstall_package(root, p) for p in pkgs], "Uninstall")

    def _run(self, fn, what: str) -> None:  # type: ignore[no-untyped-def]
        def done(reports: list[PackageOpReport]) -> None:
            bad = [r for r in reports if not r.ok]
            kept = [k for r in reports for k in r.kept]
            if bad:
                lines = [f"{r.package}: {p}: {why}" for r in bad for p, why in (r.failed + r.copy.failed)][:50]
                dialogs.error(self, f"{what} incomplete", f"{len(bad)} package(s) had errors.", "\n".join(lines))
            else:
                extra = f"\n\nFolders kept because they contain your own files: {', '.join(kept)}" if kept else ""
                dialogs.info(self, what, f"{what} finished for {len(reports)} package(s).{extra}")
            self.reload()
        self.panel.attach(run_task(fn, on_success=done,
                                   on_error=lambda m, h: dialogs.error(self, f"{what} failed", m, h)))

    def _help(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Emulators & Apps — help")
        lay = QVBoxLayout(dlg)
        area = QScrollArea()
        img = QLabel()
        with resources.as_file(resources.files("onion_desktop.resources").joinpath("Onion_Emulators_Manager_help.png")) as f:
            img.setPixmap(QPixmap(str(Path(f))))
        area.setWidget(img)
        lay.addWidget(area)
        dlg.resize(900, 640)
        dlg.exec()
