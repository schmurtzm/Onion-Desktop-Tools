from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QWidget,
)

from ...core.models import human_size
from ...onion import downloader
from ...onion.installer import InstallPlan, InstallResult, execute_install, plan_install
from ...onion.releases import Channels, Release, discover, make_client
from .. import dialogs
from ..state import AppState
from ..widgets import Card, LogView, TaskPanel, status_label, subtle
from ..worker import run_task
from .base import Page, open_url


class InstallPage(Page):
    TITLE = "Install / Update Onion"
    SUBTITLE = ("Download an official Onion OS release and extract it to the selected card. Installing over an "
                "existing Onion keeps your ROMs, saves and configuration; the console completes the "
                "installation on its next boot.")

    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(state, parent)
        self.channels: Channels | None = None
        # --- releases
        rel = Card("1. Download Onion OS")
        self.stable_rb = QRadioButton("Stable — not checked yet")
        self.beta_rb = QRadioButton("Beta — not checked yet")
        self.stable_rb.setChecked(True)
        for rb in (self.stable_rb, self.beta_rb):
            rb.setEnabled(False)
            rel.body.addWidget(rb)
        row = QHBoxLayout()
        self.check_btn = QPushButton("Check for releases")
        self.notes_btn = QPushButton("Release notes")
        self.dl_btn = QPushButton("Download")
        self.dl_btn.setObjectName("primary")
        self.notes_btn.setEnabled(False)
        self.dl_btn.setEnabled(False)
        for b in (self.check_btn, self.notes_btn, self.dl_btn):
            row.addWidget(b)
        row.addStretch(1)
        rel.body.addLayout(row)
        rel.body.addWidget(subtle("Releases come from github.com/OnionUI/Onion. Downloads are checked against "
                                  "the size and SHA-256 published by GitHub."))
        self.dl_panel = TaskPanel()
        rel.body.addWidget(self.dl_panel)
        self.layout_.addWidget(rel)
        # --- local archives
        loc = Card("2. Choose the version to install")
        self.archives = QListWidget()
        self.archives.setMinimumHeight(90)
        self.archives.setMaximumHeight(170)
        self.archives.setAccessibleName("Downloaded Onion archives")
        loc.body.addWidget(self.archives)
        row2 = QHBoxLayout()
        add_btn = QPushButton("Add archive file…")
        del_btn = QPushButton("Delete selected")
        open_btn = QPushButton("Open downloads folder")
        for b in (add_btn, del_btn, open_btn):
            row2.addWidget(b)
        row2.addStretch(1)
        loc.body.addLayout(row2)
        self.layout_.addWidget(loc)
        # --- install
        ins = Card("3. Install on the selected SD card")
        self.target_lbl = status_label("")
        ins.body.addWidget(self.target_lbl)
        row3 = QHBoxLayout()
        self.install_btn = QPushButton("Install / Update / Repair")
        self.install_btn.setObjectName("primary")
        row3.addWidget(self.install_btn)
        row3.addStretch(1)
        ins.body.addLayout(row3)
        self.panel = TaskPanel()
        ins.body.addWidget(self.panel)
        self.log = LogView()
        self.log.setMaximumHeight(160)
        ins.body.addWidget(self.log)
        self.layout_.addWidget(ins)
        self.layout_.addStretch(1)

        self.extra_archives: list[Path] = []
        self.check_btn.clicked.connect(self.check_releases)
        self.notes_btn.clicked.connect(self._notes)
        self.dl_btn.clicked.connect(self._download)
        add_btn.clicked.connect(self._add_archive)
        del_btn.clicked.connect(self._delete_archive)
        open_btn.clicked.connect(lambda: self._open_downloads())
        self.install_btn.clicked.connect(self._install)
        self.archives.itemSelectionChanged.connect(self._update)
        state.card_changed.connect(self._update)
        state.target_changed.connect(self._update)
        self.reload_archives()

    # -- releases -------------------------------------------------------------------------
    def check_releases(self) -> None:
        self.check_btn.setEnabled(False)
        self.check_btn.setText("Checking…")

        def work(p, c):  # type: ignore[no-untyped-def]
            with make_client() as client:
                return discover(client)

        run_task(work, on_success=self._on_channels,
                 on_error=lambda m, h: dialogs.error(self, "Cannot list releases", m, h),
                 on_done=lambda: (self.check_btn.setEnabled(True), self.check_btn.setText("Check for releases")))

    def _rb_text(self, kind: str, r: Release | None) -> str:
        if r is None:
            return f"{kind} — none available"
        cached = " — already downloaded" if downloader.is_cached(r, self.state.settings.downloads_path) else ""
        date = r.published_at[:10]
        integrity = "" if r.asset.sha256 else " — no checksum published"
        return f"{kind} — {r.version} ({human_size(r.asset.size)}, {date}){integrity}{cached}"

    def _on_channels(self, ch: Channels) -> None:
        self.channels = ch
        self.stable_rb.setText(self._rb_text("Stable", ch.stable))
        self.beta_rb.setText(self._rb_text("Beta", ch.beta))
        self.stable_rb.setEnabled(ch.stable is not None)
        self.beta_rb.setEnabled(ch.beta is not None)
        if ch.stable is None and ch.beta is not None:
            self.beta_rb.setChecked(True)
        self.notes_btn.setEnabled(True)
        self.dl_btn.setEnabled(not self.dl_panel.busy)

    def _selected_release(self) -> Release | None:
        if not self.channels:
            return None
        return self.channels.beta if self.beta_rb.isChecked() else self.channels.stable

    def _notes(self) -> None:
        r = self._selected_release()
        if r:
            open_url(r.html_url)

    def _download(self) -> None:
        r = self._selected_release()
        if not r:
            return
        dest = self.state.settings.downloads_path
        self.dl_btn.setEnabled(False)

        def work(progress, cancel):  # type: ignore[no-untyped-def]
            with make_client(timeout=60) as client:
                return downloader.download_release(r, dest, client, progress=progress, cancel=cancel)

        def ok(arc: downloader.LocalArchive) -> None:
            self.log.log(f"Downloaded {arc.name} ({human_size(arc.size)}), SHA-256 {arc.sha256}")
            if self.channels:
                self._on_channels(self.channels)
            self.reload_archives(select=arc.path)

        task = run_task(work, on_success=ok,
                        on_error=lambda m, h: dialogs.error(self, "Download failed", m, h),
                        on_cancel=lambda: self.log.log("Download cancelled (partial file kept for resume)."),
                        on_done=lambda: self.dl_btn.setEnabled(self.channels is not None))
        self.dl_panel.attach(task)

    # -- archives -------------------------------------------------------------------------
    def reload_archives(self, select: Path | None = None) -> None:
        self.archives.clear()
        found = downloader.list_local_archives(self.state.settings.downloads_path)
        paths = {a.path for a in found}
        for a in found:
            badge = "verified (GitHub SHA-256)" if a.verified_against_github_digest else (
                "downloaded" if a.sha256 else "unknown origin")
            channel = f"{a.channel} · " if a.channel else ""
            item = QListWidgetItem(f"{a.name} — {human_size(a.size)} — {channel}{badge}")
            item.setData(Qt.ItemDataRole.UserRole, a.path)
            self.archives.addItem(item)
        for p in self.extra_archives:
            if p not in paths and p.is_file():
                item = QListWidgetItem(f"{p.name} — {human_size(p.stat().st_size)} — local file {p.parent}")
                item.setData(Qt.ItemDataRole.UserRole, p)
                self.archives.addItem(item)
        for i in range(self.archives.count()):
            if select and self.archives.item(i).data(Qt.ItemDataRole.UserRole) == select:
                self.archives.setCurrentRow(i)
        if self.archives.currentRow() < 0 and self.archives.count():
            self.archives.setCurrentRow(0)
        self._update()

    def _add_archive(self) -> None:
        fn, _ = QFileDialog.getOpenFileName(self, "Select an Onion release archive", str(Path.home()),
                                            "Onion release (Onion-v*.zip);;ZIP archives (*.zip)")
        if fn:
            self.extra_archives.append(Path(fn))
            self.reload_archives(select=Path(fn))

    def _delete_archive(self) -> None:
        item = self.archives.currentItem()
        if not item:
            return
        p: Path = item.data(Qt.ItemDataRole.UserRole)
        if p in self.extra_archives:
            self.extra_archives.remove(p)
        elif dialogs.confirm(self, "Delete download", f"Delete {p.name} from the downloads folder?"):
            p.unlink(missing_ok=True)
            p.with_name(p.name + ".json").unlink(missing_ok=True)
        self.reload_archives()

    def _open_downloads(self) -> None:
        from .base import open_path
        d = self.state.settings.downloads_path
        d.mkdir(parents=True, exist_ok=True)
        open_path(str(d))

    # -- install --------------------------------------------------------------------------
    def _update(self) -> None:
        t, c = self.state.target, self.state.card
        if t is None:
            self.target_lbl.setText("No SD card selected (choose one in the bar at the top).")
        else:
            self.target_lbl.setText(f"Target: {t.label}\nContent: {c.state.label + ' ' + (c.version or '') if c else '…'}")
        self.install_btn.setEnabled(t is not None and c is not None and self.archives.currentItem() is not None
                                    and not self.panel.busy)

    def _install(self) -> None:
        item = self.archives.currentItem()
        card = self.require_card()
        if not item or not card:
            return
        archive: Path = item.data(Qt.ItemDataRole.UserRole)
        target = card.root
        self.install_btn.setEnabled(False)
        self.log.log(f"Checking {archive.name} and the card…")
        run_task(lambda p, c: plan_install(archive, target), on_success=self._confirm_plan,
                 on_error=lambda m, h: (dialogs.error(self, "Cannot install", m, h), self._update()))

    def _confirm_plan(self, plan: InstallPlan) -> None:
        self._update()
        text = plan.confirmation
        if plan.warnings:
            text += "\n\nWarnings:\n• " + "\n• ".join(plan.warnings)
        need = f"\n\nSpace required: {human_size(plan.required_bytes)}; available: {human_size(plan.available_bytes)}"
        text += need
        if plan.available_bytes is not None and plan.required_bytes > plan.available_bytes:
            dialogs.error(self, "Not enough space", "There is not enough free space on the card." + need)
            return
        if plan.requires_strong_confirmation:
            dlg = dialogs.TypedConfirmDialog(self, "Installation confirmation", text, "INSTALL", "Install")
            if dlg.exec() != QDialog.DialogCode.Accepted:
                self.log.log("Installation cancelled by user.")
                return
        elif not dialogs.confirm(self, "Installation confirmation", text, yes_text="Install"):
            self.log.log("Installation cancelled by user.")
            return
        self.log.log(f"Extracting {plan.archive.name} to {plan.target} ({plan.mode.value})…")

        def done(res: InstallResult) -> None:
            self.state.reload_card()
            if res.ok:
                self.log.log("Extraction and verification successful.")
                dialogs.info(self, "Onion copied to the card",
                             "Extraction successful and verified.\n\nEject the card, insert it in your Miyoo and "
                             "turn it on to complete the installation.")
            else:
                for path, why in res.extract.failed:
                    self.log.log(f"FAILED {path}: {why}")
                dialogs.error(self, "Installation incomplete",
                              f"{len(res.extract.failed)} file(s) could not be written. The card is NOT ready.",
                              "Check the card (SD Cards → Check for errors) and run the installation again "
                              "to repair it.")

        task = run_task(lambda p, c: execute_install(plan, progress=p, cancel=c), on_success=done,
                        on_error=lambda m, h: (self.log.log(f"Error: {m}"),
                                               dialogs.error(self, "Installation failed", m, h)),
                        on_cancel=lambda: (self.log.log("Installation cancelled — the card may be incomplete; run it "
                                                        "again to repair."), self.state.reload_card()),
                        on_done=self._update)
        self.panel.attach(task)
        self._update()
