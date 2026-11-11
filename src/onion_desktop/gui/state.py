"""Shared application state: settings, device list (polled off the GUI thread), current target card."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from .. import settings as settings_mod
from ..core.models import Disk, Partition, human_size
from ..linux.disk_manager import DiskManager, create_default_manager
from ..onion.detection import CardInfo, detect_card
from .worker import Task, run_task

log = logging.getLogger(__name__)
POLL_MS = 3000


@dataclass(frozen=True)
class Target:
    """A mounted card root the user selected (or a manually chosen folder)."""

    path: Path
    disk: Disk | None
    partition: Partition | None

    @property
    def label(self) -> str:
        if self.disk and self.partition:
            return (f"{self.partition.label or self.partition.device} — {self.disk.display_name} "
                    f"({human_size(self.disk.size)}) — {self.path}")
        return f"Folder: {self.path}"


class AppState(QObject):
    disks_changed = Signal()
    target_changed = Signal()
    card_changed = Signal()
    backend_ready = Signal(str)

    def __init__(self, settings: settings_mod.Settings, manager: DiskManager | None = None) -> None:
        super().__init__()
        self.settings = settings
        self.manager = manager
        self.disks: list[Disk] = []
        self.target: Target | None = None
        self.card: CardInfo | None = None
        self.poll_error: str = ""
        self._signature: tuple[object, ...] = ()
        self._poll_task: Task | None = None
        self._card_task: Task | None = None
        self._user_cleared = False
        self.timer = QTimer(self)
        self.timer.setInterval(POLL_MS)
        self.timer.timeout.connect(self.refresh)

    def start(self) -> None:
        self.refresh()
        self.timer.start()

    # -- device polling -------------------------------------------------------------------
    def refresh(self) -> None:
        if self._poll_task is not None:
            return

        def work(progress, cancel):  # type: ignore[no-untyped-def]
            mgr = self.manager or create_default_manager()
            return mgr, mgr.list_disks()

        self._poll_task = run_task(work, on_success=self._on_disks, on_error=self._on_poll_error,
                                   on_done=self._poll_done)

    def _poll_done(self) -> None:
        self._poll_task = None

    def _on_poll_error(self, msg: str, _details: str) -> None:
        if msg != self.poll_error:
            self.poll_error = msg
            log.warning("Device enumeration failed: %s", msg)
            self.disks_changed.emit()

    def _on_disks(self, result: tuple[DiskManager, list[Disk]]) -> None:
        mgr, disks = result
        if self.manager is None:
            self.manager = mgr
            self.backend_ready.emit(getattr(mgr.backend, "name", "?"))
        self.poll_error = ""
        sig = tuple((d.device, d.size, d.serial, d.protected_reasons,
                     tuple((p.device, p.fs_type, p.mount_points) for p in d.partitions)) for d in disks)
        if sig == self._signature:
            return
        self._signature = sig
        self.disks = disks
        self._reconcile_target()
        self.disks_changed.emit()

    def candidate_targets(self) -> list[Target]:
        out = []
        for d in self.disks:
            if d.protected_reasons:
                continue
            for p in d.partitions:
                if p.mount_point:
                    out.append(Target(Path(p.mount_point), d, p))
        return out

    def _reconcile_target(self) -> None:
        cands = self.candidate_targets()
        if self.target and self.target.disk is not None:
            match = next((c for c in cands if c.partition and self.target.partition
                          and c.partition.device == self.target.partition.device
                          and c.disk and c.disk.serial == self.target.disk.serial), None)
            if match is None:
                self.set_target(None)
            elif match != self.target:
                self.target = match
        if self.target is None and len(cands) == 1 and not self._user_cleared:
            # Selecting a *mounted folder* is non-destructive; formatting never uses this.
            self.set_target(cands[0])

    # -- target ---------------------------------------------------------------------------
    def set_target(self, target: Target | None, *, user: bool = False) -> None:
        if user:
            self._user_cleared = target is None
        if target == self.target:
            return
        self.target = target
        self.card = None
        self.target_changed.emit()
        self.reload_card()

    def reload_card(self) -> None:
        if self.target is None:
            self.card = None
            self.card_changed.emit()
            return
        path = self.target.path
        self._card_task = run_task(lambda p, c: detect_card(path), on_success=self._on_card)

    def _on_card(self, card: CardInfo) -> None:
        if self.target and card.root == self.target.path:
            self.card = card
            self.card_changed.emit()

    def save_settings(self) -> None:
        settings_mod.save(self.settings)
