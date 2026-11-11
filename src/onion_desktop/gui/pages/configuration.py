from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QPushButton, QTabWidget, QVBoxLayout, QWidget

from ... import paths
from ...onion.configuration import FlagDefinition, FlagStore, backup_config, load_default_schema, restore_config
from .. import dialogs
from ..state import AppState
from ..widgets import status_label
from .base import Page, open_path


class ConfigurationPage(Page):
    TITLE = "Onion Configuration"
    SUBTITLE = ("Onion settings stored as flag files in .tmp_update/config. Changes are applied to the card when "
                "you click Apply; a snapshot of the previous settings is saved first.")

    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(state, parent)
        self.schema = load_default_schema()
        self.status = status_label("")
        self.layout_.addWidget(self.status)
        self.tabs = QTabWidget()
        self.boxes: dict[str, QCheckBox] = {}
        for section, defs in self.schema.items():
            w = QWidget()
            lay = QVBoxLayout(w)
            for d in defs:
                cb = QCheckBox(d.short_description)
                cb.setToolTip(d.description)
                cb.setAccessibleDescription(d.description)
                if d.sub_option:
                    cb.setContentsMargins(24, 0, 0, 0)
                    cb.setStyleSheet("margin-left: 24px;")
                cb.toggled.connect(self._dirty)
                self.boxes[d.filename] = cb
                lay.addWidget(cb)
            lay.addStretch(1)
            self.tabs.addTab(w, section)
        self.layout_.addWidget(self.tabs)
        self.unknown = status_label("")
        self.layout_.addWidget(self.unknown)
        row = QHBoxLayout()
        self.apply_btn = QPushButton("Apply to card")
        self.apply_btn.setObjectName("primary")
        self.revert_btn = QPushButton("Discard changes")
        self.restore_btn = QPushButton("Restore last snapshot")
        self.snap_btn = QPushButton("Open snapshots folder")
        for b in (self.apply_btn, self.revert_btn, self.restore_btn, self.snap_btn):
            row.addWidget(b)
        row.addStretch(1)
        self.layout_.addLayout(row)
        self.layout_.addStretch(1)
        self.apply_btn.clicked.connect(self._apply)
        self.revert_btn.clicked.connect(self.load)
        self.restore_btn.clicked.connect(self._restore)
        self.snap_btn.clicked.connect(lambda: (paths.config_snapshots_dir().mkdir(parents=True, exist_ok=True),
                                               open_path(str(paths.config_snapshots_dir()))))
        state.card_changed.connect(self.load)
        self.load()

    def _defs(self) -> list[FlagDefinition]:
        return [d for defs in self.schema.values() for d in defs]

    def _store(self) -> FlagStore | None:
        c = self.state.card
        if c is None or c.state.name != "ONION":
            return None
        s = FlagStore(c.root)
        return s if s.exists() else None

    def load(self) -> None:
        store = self._store()
        self._loading = True
        for d in self._defs():
            cb = self.boxes[d.filename]
            cb.setEnabled(store is not None)
            cb.setChecked(bool(store and store.is_enabled(d.filename)))
        self._loading = False
        self.status.setText("" if store else "Select an SD card with Onion OS installed (and started once) "
                                             "to edit its configuration.")
        other = store.unknown_flags(self.schema) if store else []
        self.unknown.setText(("Other flags present on the card (kept untouched): " + ", ".join(other)) if other else "")
        for b in (self.apply_btn, self.revert_btn):
            b.setEnabled(False)
        self.restore_btn.setEnabled(store is not None)

    def _dirty(self) -> None:
        if not getattr(self, "_loading", False):
            self.apply_btn.setEnabled(True)
            self.revert_btn.setEnabled(True)

    def _apply(self) -> None:
        store = self._store()
        if not store:
            return
        try:
            snap = backup_config(store.card_root, paths.config_snapshots_dir())
            changed = 0
            for d in self._defs():
                want = self.boxes[d.filename].isChecked()
                if want != store.is_enabled(d.filename):
                    store.set_enabled(d.filename, want)
                    changed += 1
        except OSError as exc:
            dialogs.error(self, "Cannot write configuration", str(exc))
            return
        except Exception as exc:  # OdtError
            dialogs.error(self, "Cannot write configuration", getattr(exc, "message", str(exc)))
            return
        dialogs.info(self, "Configuration saved", f"{changed} setting(s) changed. Previous settings saved to:\n{snap}")
        self.load()

    def _restore(self) -> None:
        store = self._store()
        snaps = sorted(p for p in paths.config_snapshots_dir().glob("*") if p.is_dir()) if store else []
        if not store or not snaps:
            dialogs.info(self, "No snapshot", "No configuration snapshot has been saved yet.")
            return
        latest = snaps[-1]
        if dialogs.confirm(self, "Restore configuration", f"Restore the settings saved on {latest.name}?"):
            try:
                restore_config(latest, store.card_root, self.schema)
            except Exception as exc:
                dialogs.error(self, "Restore failed", getattr(exc, "message", str(exc)))
            self.load()
