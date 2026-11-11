from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...backup.backup_manager import BackupPlan, BackupResult, plan_backup, run_backup
from ...backup.profiles import ALL, PROFILES, Category, available_categories
from ...backup.restore_manager import BackupInfo, RestorePlan, RestoreResult, list_backups, plan_restore, run_restore
from ...core.copier import ConflictPolicy
from ...core.models import human_size
from .. import dialogs
from ..state import AppState
from ..widgets import TaskPanel, status_label, subtle
from ..worker import run_task
from .base import Page, open_path


class BackupPage(Page):
    TITLE = "Backup & Restore"
    SUBTITLE = ("Back up an Onion or Miyoo stock card to this computer, and restore backups onto an Onion card "
                "(this is also how you migrate from the stock card to Onion).")

    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(state, parent)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._backup_tab(), "Backup")
        self.tabs.addTab(self._restore_tab(), "Restore")
        self.layout_.addWidget(self.tabs)
        self.panel = TaskPanel()
        self.layout_.addWidget(self.panel)
        self.layout_.addStretch(1)
        state.card_changed.connect(self._card_changed)
        self._card_changed()
        self.reload_backups()

    # ---------------------------------------------------------------- backup tab
    def _backup_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.src_lbl = status_label("")
        lay.addWidget(self.src_lbl)
        prof_row = QHBoxLayout()
        self.profile = QComboBox()
        self.profile.addItems(list(PROFILES))
        self.profile.setAccessibleName("Backup profile")
        prof_row.addWidget(self.profile)
        prof_row.addStretch(1)
        lay.addLayout(prof_row)
        self.b_checks: dict[Category, QCheckBox] = {}
        for cat in ALL:
            cb = QCheckBox(cat.label)
            self.b_checks[cat] = cb
            lay.addWidget(cb)
        self.dest_lbl = subtle("")
        lay.addWidget(self.dest_lbl)
        row = QHBoxLayout()
        self.backup_btn = QPushButton("Start backup")
        self.backup_btn.setObjectName("primary")
        open_btn = QPushButton("Open backups folder")
        row.addWidget(self.backup_btn)
        row.addWidget(open_btn)
        row.addStretch(1)
        lay.addLayout(row)
        self.profile.currentTextChanged.connect(self._apply_profile)
        self.backup_btn.clicked.connect(self._backup)
        open_btn.clicked.connect(self._open_backups)
        return w

    def _card_changed(self) -> None:
        c = self.state.card
        allowed = set(available_categories(c.state)) if c else set()
        if c is None:
            self.src_lbl.setText("Select the SD card to back up in the bar at the top.")
        else:
            extra = ""
            if c.state.name == "STOCK":
                extra = ("\nStock card: saves, RetroArch configuration and Onion flags cannot be migrated "
                         "automatically. BIOS files are taken from RetroArch/.retroarch/system.")
            elif not allowed:
                extra = "\nThis card holds neither Onion nor the stock OS: nothing can be backed up."
            self.src_lbl.setText(f"Source: {c.root} — {c.state.label} {c.version or ''}{extra}")
        for cat, cb in self.b_checks.items():
            cb.setEnabled(cat in allowed)
            cb.setChecked(cat in allowed)
        self._apply_profile(self.profile.currentText())
        self.dest_lbl.setText(f"Backups are stored in {self.state.settings.backups_path}")
        self._update_restore_target()

    def _apply_profile(self, name: str) -> None:
        cats = PROFILES.get(name, ALL)
        for cat, cb in self.b_checks.items():
            cb.setChecked(cb.isEnabled() and cat in cats)

    def _open_backups(self) -> None:
        p = self.state.settings.backups_path
        p.mkdir(parents=True, exist_ok=True)
        open_path(str(p))

    def _backup(self) -> None:
        card = self.require_card()
        if not card:
            return
        cats = [c for c, cb in self.b_checks.items() if cb.isChecked() and cb.isEnabled()]
        if not cats:
            dialogs.info(self, "Nothing selected", "Select at least one category to back up.")
            return
        run_task(lambda p, c: plan_backup(card, cats), on_success=self._confirm_backup,
                 on_error=lambda m, h: dialogs.error(self, "Cannot back up", m, h))

    def _confirm_backup(self, plan: BackupPlan) -> None:
        desc, ok = QInputDialog.getMultiLineText(
            self, "Backup description",
            f"{len(plan.items)} files, {human_size(plan.total_bytes)} will be copied.\n"
            "Optional description for this backup:", "")
        if not ok:
            return
        dest = self.state.settings.backups_path

        def done(res: BackupResult) -> None:
            self.reload_backups()
            title = "Backup complete" if res.ok else "Backup INCOMPLETE"
            dialogs.report(self, title, f"Backup folder: {res.folder}", res.report)

        self.panel.attach(run_task(lambda p, c: run_backup(plan, dest, desc, progress=p, cancel=c), on_success=done,
                                   on_error=lambda m, h: dialogs.error(self, "Backup failed", m, h)))

    # ---------------------------------------------------------------- restore tab
    def _restore_tab(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        left = QVBoxLayout()
        self.backups = QListWidget()
        self.backups.setAccessibleName("Available backups")
        left.addWidget(self.backups)
        refresh = QPushButton("Refresh list")
        left.addWidget(refresh)
        lay.addLayout(left, 2)
        mid = QVBoxLayout()
        self.r_checks: dict[Category, QCheckBox] = {}
        for cat in ALL:
            cb = QCheckBox(cat.label)
            cb.setEnabled(False)
            self.r_checks[cat] = cb
            mid.addWidget(cb)
        self.verify_cb = QCheckBox("Verify restored files against the backup checksums")
        self.verify_cb.setChecked(True)
        mid.addWidget(self.verify_cb)
        self.restore_target_lbl = status_label("")
        mid.addWidget(self.restore_target_lbl)
        self.restore_btn = QPushButton("Restore to selected card")
        self.restore_btn.setObjectName("primary")
        self.restore_btn.setEnabled(False)
        mid.addWidget(self.restore_btn)
        mid.addStretch(1)
        lay.addLayout(mid, 2)
        self.info = QPlainTextEdit()
        self.info.setReadOnly(True)
        self.info.setAccessibleName("Backup information")
        lay.addWidget(self.info, 3)
        refresh.clicked.connect(self.reload_backups)
        self.backups.currentItemChanged.connect(self._show_backup)
        self.restore_btn.clicked.connect(self._restore)
        return w

    def reload_backups(self) -> None:
        self.backups.clear()
        for b in list_backups(self.state.settings.backups_path):
            item = QListWidgetItem(b.name + ("  ⚠ incomplete" if b.complete is False else ""))
            item.setData(Qt.ItemDataRole.UserRole, b)
            self.backups.addItem(item)
        self._show_backup()

    def _selected_backup(self) -> BackupInfo | None:
        item = self.backups.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _show_backup(self) -> None:
        b = self._selected_backup()
        for cat, cb in self.r_checks.items():
            present = bool(b and cat in b.categories)
            cb.setEnabled(present)
            cb.setChecked(present)
        self.info.setPlainText(b.info_text if b else "Select a backup.")
        self._update_restore_target()

    def _update_restore_target(self) -> None:
        if not hasattr(self, "restore_target_lbl"):
            return
        c = self.state.card
        self.restore_target_lbl.setText(f"Target: {c.root} ({c.state.label})" if c else "Target: no card selected")
        self.restore_btn.setEnabled(bool(c and self._selected_backup()))

    def _restore(self) -> None:
        b, card = self._selected_backup(), self.require_card()
        if not b or not card:
            return
        cats = [c for c, cb in self.r_checks.items() if cb.isChecked() and cb.isEnabled()]
        run_task(lambda p, c: plan_restore(b, card, cats), on_success=self._confirm_restore,
                 on_error=lambda m, h: dialogs.error(self, "Cannot restore", m, h))

    def _confirm_restore(self, plan: RestorePlan) -> None:
        text = (f"Selected backup:\n{plan.backup.name}\nTarget: {plan.target}\n\n{len(plan.items)} files, "
                f"{human_size(plan.total_bytes)}.")
        if plan.warnings:
            text += "\n\nWarnings:\n• " + "\n• ".join(plan.warnings)
        policy = ConflictPolicy.SKIP
        if plan.conflicts:
            box = QMessageBox(QMessageBox.Icon.Warning, "Files already exist",
                              text + f"\n\n{len(plan.conflicts)} file(s) already exist on the card with different "
                              "content (for example newer saves). What should happen to them?", parent=self)
            box.setDetailedText("\n".join(str(c.dst_rel) for c in plan.conflicts[:2000]))
            keep = box.addButton("Keep card's files", QMessageBox.ButtonRole.AcceptRole)
            over = box.addButton("Overwrite with backup", QMessageBox.ButtonRole.DestructiveRole)
            cancel = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            box.setDefaultButton(keep)
            box.exec()
            clicked = box.clickedButton()
            if clicked is cancel or clicked is None:
                return
            policy = ConflictPolicy.OVERWRITE if clicked is over else ConflictPolicy.SKIP
        elif not dialogs.confirm(self, "Restore backup", text + "\n\nRestore this backup?", yes_text="Restore"):
            return
        verify = self.verify_cb.isChecked()

        def done(res: RestoreResult) -> None:
            self.state.reload_card()
            title = "Restore complete" if res.ok else "Restore INCOMPLETE"
            dialogs.report(self, title, f"Backup {plan.backup.name} → {plan.target}", res.report, res.verify_failures)

        self.panel.attach(run_task(lambda p, c: run_restore(plan, policy, verify=verify, progress=p, cancel=c),
                                   on_success=done, on_error=lambda m, h: dialogs.error(self, "Restore failed", m, h)))
