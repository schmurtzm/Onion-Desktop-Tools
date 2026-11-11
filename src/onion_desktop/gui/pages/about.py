from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from ... import __version__
from ...updates import check_for_update
from .. import dialogs
from ..state import AppState
from ..worker import run_task
from .base import Page, open_url


class AboutPage(Page):
    TITLE = "About"

    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(state, parent)
        lbl = QLabel(
            f"<p><b>Onion Desktop Tools for Linux</b> {__version__}</p>"
            "<p>Linux port of <a href='https://github.com/schmurtzm/Onion-Desktop-Tools'>Onion Desktop Tools</a> "
            "by Schmurtz (Onion Team).</p>"
            "<p>Onion OS: <a href='https://github.com/OnionUI/Onion'>github.com/OnionUI/Onion</a> · "
            "<a href='https://github.com/OnionUI/Onion/wiki'>Onion documentation</a></p>"
            "<p>Support the original authors: "
            "<a href='https://www.patreon.com/schmurtz'>Schmurtz on Patreon</a> · "
            "<a href='https://www.buymeacoffee.com/schmurtz'>Buy me a coffee</a> · "
            "<a href='https://github.com/sponsors/Aemiii91'>Onion team (GitHub Sponsors)</a> · "
            "<a href='https://ko-fi.com/Aemiii91'>Ko-fi</a></p>"
            "<p>Licensed under the GNU General Public License v3.0. This program comes with ABSOLUTELY NO "
            "WARRANTY. FBNeo cheat.dat from the FBNeo-cheats project. Qt for Python (PySide6) is LGPL-3.0.</p>")
        lbl.setOpenExternalLinks(True)
        lbl.setWordWrap(True)
        self.layout_.addWidget(lbl)
        row = QHBoxLayout()
        b = QPushButton("Check for updates")
        b.clicked.connect(self.check)
        row.addWidget(b)
        row.addStretch(1)
        self.layout_.addLayout(row)
        self.layout_.addStretch(1)

    def check(self) -> None:
        def done(info):  # type: ignore[no-untyped-def]
            if info is None:
                dialogs.info(self, "Updates", "Could not check for updates (no release published or no network).")
            elif info.newer:
                if dialogs.confirm(self, "Update available", f"Version {info.latest} is available (you have "
                                   f"{info.current}). Open the download page?", warning=False, yes_text="Open"):
                    open_url(info.url)
            else:
                dialogs.info(self, "Updates", f"You are running the latest version ({info.current}).")
        run_task(lambda p, c: check_for_update(), on_success=done)
