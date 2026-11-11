from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.models import Disk, Partition, human_size
from ...linux.disk_manager import FormatResult
from ...onion.detection import CardState, detect_card
from .. import dialogs
from ..state import AppState
from ..widgets import Card, TaskPanel, status_label, subtle
from ..worker import run_task
from .base import Page


def _card_warning(disk: Disk) -> str:
    """Upstream Disk_Format.ps1 content-aware warning, built from mounted partitions."""
    notes = []
    for p in disk.partitions:
        if not p.mount_point:
            continue
        info = detect_card(Path(p.mount_point))
        if info.state is CardState.ONION:
            notes.append(f"Onion {info.version_label} is installed on {p.device}. Saves, ROMs and "
                         "configuration — everything will be lost!")
        elif info.state is CardState.ONION_INSTALL_PENDING:
            notes.append(f"{p.device} holds Onion installation files that were never run.")
        elif info.state is CardState.STOCK:
            notes.append(f"{p.device} looks like a Miyoo STOCK card. Installing Onion on the stock card is not "
                         "recommended (its quality is poor and may corrupt data).")
        elif info.state is CardState.OTHER:
            notes.append(f"{p.device} contains files. Everything will be lost!")
    if not disk.partitions:
        notes.append("The card has no partition recognised by Linux (unformatted or unknown type).")
    elif not any(p.mount_point for p in disk.partitions):
        notes.append("The card's partitions are not mounted, so their content could not be inspected.")
    return "\n\n".join(notes)


class FormatDialog(QDialog):
    """Step 1 of formatting: explicit device choice (no default) and summary."""

    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Format SD card as FAT32")
        self.state = state
        lay = QVBoxLayout(self)
        lay.addWidget(subtle("Creates a new MBR partition table with a single FAT32 partition labelled ONION. "
                             "ALL data on the selected device will be erased. System disks are never listed."))
        self.combo = QComboBox()
        self.combo.setAccessibleName("Device to format")
        self.combo.addItem("— Select a device —", None)
        for d in state.disks:
            if not d.protected_reasons:
                self.combo.addItem(f"{d.device} — {d.display_name} — {human_size(d.size)}"
                                   f"{' — serial ' + d.serial if d.serial else ''}", d)
        lay.addWidget(self.combo)
        self.details = status_label("")
        self.warn = status_label("", "danger")
        lay.addWidget(self.details)
        lay.addWidget(self.warn)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.next = bb.addButton("Next…", QDialogButtonBox.ButtonRole.AcceptRole)
        self.next.setEnabled(False)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.combo.currentIndexChanged.connect(self._changed)
        if not state.manager or not state.manager.can_modify:
            self.warn.setText("UDisks2 is not available: formatting is disabled (read-only mode).")
        self.resize(620, 300)

    def _changed(self) -> None:
        d: Disk | None = self.combo.currentData()
        self.next.setEnabled(bool(d) and bool(self.state.manager and self.state.manager.can_modify))
        if not d:
            self.details.setText("")
            self.warn.setText("")
            return
        parts = "\n".join(f"  {p.device}: {p.fs_version or p.fs_type or 'unknown'} {p.label} "
                          f"{human_size(p.size)} {('mounted at ' + p.mount_point) if p.mount_point else ''}"
                          for p in d.partitions) or "  (no partitions)"
        self.details.setText(f"Device: {d.device}\nModel: {d.display_name}\nSize: {human_size(d.size)} "
                             f"({d.size:,} bytes)\nBus: {d.bus or 'unknown'}\nPartitions:\n{parts}")
        self.warn.setText(_card_warning(d))

    def selected(self) -> Disk | None:
        data: Disk | None = self.combo.currentData()
        return data


class SdCardsPage(Page):
    TITLE = "SD Card Manager"
    SUBTITLE = ("Removable devices detected on this computer. Protected devices (system disks, internal "
                "storage) are shown for information only and can never be modified.")

    def __init__(self, state: AppState, navigate: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__(state, parent)
        self.navigate = navigate
        self.backend_lbl = subtle("")
        self.layout_.addWidget(self.backend_lbl)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Device", "Model / label", "Size", "File system", "Mounted at", "Free", "Status"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setMinimumHeight(260)
        self.layout_.addWidget(self.tree)
        row = QHBoxLayout()
        self.buttons: dict[str, QPushButton] = {}
        for key, text in [("refresh", "Refresh"), ("mount", "Mount"), ("unmount", "Unmount"),
                          ("eject", "Eject"), ("check", "Check for errors"), ("repair", "Repair"),
                          ("use", "Use as target")]:
            b = QPushButton(text)
            self.buttons[key] = b
            row.addWidget(b)
        row.addStretch(1)
        fmt = QPushButton("Format FAT32…")
        fmt.setObjectName("danger")
        self.buttons["format"] = fmt
        row.addWidget(fmt)
        self.layout_.addLayout(row)
        self.panel = TaskPanel()
        self.layout_.addWidget(self.panel)
        box = Card("Notes")
        box.body.addWidget(QLabel(
            "• Mounting, ejecting, checking and formatting are performed by the system's UDisks2 service; "
            "your desktop may ask for your password (Polkit).\n"
            "• 'Check for errors' runs fsck.vfat read-only; 'Repair' fixes errors (equivalent of chkdsk /F).\n"
            "• Onion requires FAT32. Cards larger than 32 GB are fine on Linux."))
        self.layout_.addWidget(box)
        self.layout_.addStretch(1)
        b = self.buttons
        b["refresh"].clicked.connect(state.refresh)
        b["mount"].clicked.connect(lambda: self._part_op("mount"))
        b["unmount"].clicked.connect(lambda: self._part_op("unmount"))
        b["check"].clicked.connect(lambda: self._part_op("check"))
        b["repair"].clicked.connect(lambda: self._part_op("repair"))
        b["eject"].clicked.connect(self._eject)
        b["use"].clicked.connect(self._use)
        b["format"].clicked.connect(self._format)
        self.tree.itemSelectionChanged.connect(self._update_buttons)
        state.disks_changed.connect(self.populate)
        state.backend_ready.connect(lambda _n: self.populate())
        self.populate()

    def populate(self) -> None:
        mgr = self.state.manager
        if mgr is None:
            self.backend_lbl.setText("Detecting devices…")
        elif mgr.can_modify:
            self.backend_lbl.setText("Backend: UDisks2 (full functionality).")
        else:
            self.backend_lbl.setText("Backend: lsblk (read-only). Install/start udisks2 to mount, eject or format.")
        if self.state.poll_error:
            self.backend_lbl.setText(self.backend_lbl.text() + f"  Problem: {self.state.poll_error}")
        self.tree.clear()
        for d in self.state.disks:
            status = "Protected: " + "; ".join(d.protected_reasons) if d.protected_reasons else "Removable"
            top = QTreeWidgetItem([d.device, d.display_name, human_size(d.size),
                                   d.partition_table or d.fs_type or "", "", "", status])
            top.setData(0, Qt.ItemDataRole.UserRole, ("disk", d))
            if d.protected_reasons:
                for col in range(7):
                    top.setForeground(col, self.palette().placeholderText())
            for p in d.partitions:
                child = QTreeWidgetItem([p.device, p.label, human_size(p.size),
                                         f"{p.fs_type} {p.fs_version}".strip(), ", ".join(p.mount_points),
                                         human_size(p.free_bytes) if p.free_bytes is not None else "", ""])
                child.setData(0, Qt.ItemDataRole.UserRole, ("part", d, p))
                top.addChild(child)
            self.tree.addTopLevelItem(top)
            top.setExpanded(True)
        for i in range(6):
            self.tree.resizeColumnToContents(i)
        self._update_buttons()

    def _selection(self) -> tuple[Disk | None, Partition | None]:
        items = self.tree.selectedItems()
        if not items:
            return None, None
        data = items[0].data(0, Qt.ItemDataRole.UserRole)
        if data[0] == "disk":
            return data[1], None
        return data[1], data[2]

    def _update_buttons(self) -> None:
        d, p = self._selection()
        can = bool(self.state.manager and self.state.manager.can_modify) and not self.panel.busy
        ok_disk = d is not None and not d.protected_reasons
        b = self.buttons
        b["mount"].setEnabled(can and ok_disk and p is not None and not p.mounted and bool(p.fs_type))
        b["unmount"].setEnabled(can and ok_disk and p is not None and p.mounted)
        b["check"].setEnabled(can and ok_disk and p is not None and p.fs_type == "vfat")
        b["repair"].setEnabled(can and ok_disk and p is not None and p.fs_type == "vfat")
        b["eject"].setEnabled(can and ok_disk)
        b["use"].setEnabled(ok_disk and p is not None and p.mounted)
        b["format"].setEnabled(can)

    def _run(self, fn, done_msg: str | None = None, on_success=None) -> None:  # type: ignore[no-untyped-def]
        def ok(result):  # type: ignore[no-untyped-def]
            if on_success:
                on_success(result)
            elif done_msg:
                dialogs.info(self, "Done", done_msg)
            self.state.refresh()

        task = run_task(fn, on_success=ok,
                        on_error=lambda m, h: dialogs.error(self, "Operation failed", m, h),
                        on_done=self._update_buttons)
        self.panel.attach(task)
        self._update_buttons()

    def _part_op(self, op: str) -> None:
        d, p = self._selection()
        mgr = self.state.manager
        if not d or not p or not mgr:
            return
        if op == "repair" and not dialogs.confirm(
                self, "Repair file system", f"Run a file system repair on {p.device}? It will be unmounted first."):
            return
        if op == "mount":
            self._run(lambda pr, c: mgr.mount(p), on_success=lambda mp: dialogs.info(self, "Mounted", f"Mounted at {mp}"))
        elif op == "unmount":
            self._run(lambda pr, c: mgr.unmount(p))
        else:
            repair = op == "repair"
            self._run(lambda pr, c: mgr.check_filesystem(p, repair=repair),
                      on_success=lambda ok: (dialogs.info(self, "File system check",
                                                          f"{p.device}: no errors found." if ok else
                                                          f"{p.device}: errors were found"
                                                          + (" and could not all be repaired." if repair else
                                                             ". Use 'Repair' to fix them."))))

    def _eject(self) -> None:
        d, _ = self._selection()
        mgr = self.state.manager
        if d and mgr:
            ident = d.identity
            self._run(lambda pr, c: mgr.eject(ident), "The device can now be removed safely.")

    def _use(self) -> None:
        from ..state import Target
        d, p = self._selection()
        if d and p and p.mount_point:
            self.state.set_target(Target(Path(p.mount_point), d, p), user=True)
            self.navigate("dashboard")

    def _format(self) -> None:
        mgr = self.state.manager
        if not mgr:
            return
        dlg = FormatDialog(self.state, self)
        if dlg.exec() != QDialog.DialogCode.Accepted or not (disk := dlg.selected()):
            return
        confirm = dialogs.TypedConfirmDialog(
            self, "Confirm erase",
            f"You are about to ERASE {disk.device} ({disk.display_name}, {human_size(disk.size)}).\n"
            "All partitions and data on this device will be permanently destroyed.",
            disk.device)
        if confirm.exec() != QDialog.DialogCode.Accepted:
            return
        ident, typed = disk.identity, confirm.typed()

        def work(progress, cancel):  # type: ignore[no-untyped-def]
            return mgr.format_fat32(ident, confirmed_device_text=typed, progress=progress)

        def done(res: FormatResult) -> None:
            from ..state import Target
            msg = f"{res.partition.device} is now FAT32 (label {res.partition.label or 'ONION'})."
            if res.mount_point:
                self.state.set_target(Target(Path(res.mount_point), res.disk, res.partition), user=True)
                if dialogs.confirm(self, "Format complete", msg + "\n\nInstall Onion OS on it now?",
                                   warning=False, yes_text="Install Onion"):
                    self.navigate("install")
                return
            dialogs.info(self, "Format complete", msg)

        self._run(work, on_success=done)
