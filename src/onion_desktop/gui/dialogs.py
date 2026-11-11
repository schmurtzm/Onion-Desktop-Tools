"""Standard dialogs: confirmations (incl. typed device confirmation), errors and reports."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.copier import CopyReport


def error(parent: QWidget | None, title: str, message: str, details: str = "") -> None:
    box = QMessageBox(QMessageBox.Icon.Critical, title, message, QMessageBox.StandardButton.Ok, parent)
    if details:
        if "Traceback" in details:
            box.setDetailedText(details)
        else:
            box.setInformativeText(details)
    box.exec()


def info(parent: QWidget | None, title: str, message: str) -> None:
    QMessageBox.information(parent, title, message)


def confirm(parent: QWidget | None, title: str, message: str, *, warning: bool = True,
            yes_text: str = "Continue") -> bool:
    box = QMessageBox(QMessageBox.Icon.Warning if warning else QMessageBox.Icon.Question, title, message,
                      QMessageBox.StandardButton.NoButton, parent)
    yes = box.addButton(yes_text, QMessageBox.ButtonRole.AcceptRole)
    no = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(no)  # never default to the risky choice
    box.exec()
    return box.clickedButton() is yes


class TypedConfirmDialog(QDialog):
    """Requires the user to type an exact phrase (e.g. the device path) to proceed."""

    def __init__(self, parent: QWidget | None, title: str, message: str, phrase: str,
                 button_text: str = "Erase") -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.phrase = phrase
        lay = QVBoxLayout(self)
        lbl = QLabel(message)
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
        lay.addWidget(QLabel(f"Type <b>{phrase}</b> to confirm:"))
        self.edit = QLineEdit()
        self.edit.setAccessibleName("Confirmation text")
        lay.addWidget(self.edit)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.ok = self.buttons.addButton(button_text, QDialogButtonBox.ButtonRole.AcceptRole)
        self.ok.setObjectName("danger")
        self.ok.setEnabled(False)
        self.ok.setAutoDefault(False)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        lay.addWidget(self.buttons)
        self.edit.textChanged.connect(lambda t: self.ok.setEnabled(t.strip() == phrase))
        self.resize(520, self.sizeHint().height())

    def typed(self) -> str:
        return self.edit.text().strip()


def report(parent: QWidget | None, title: str, headline: str, rep: CopyReport,
           extra_failures: list[str] | None = None) -> None:
    lines = [headline, "", rep.summary()]
    if rep.failed or extra_failures:
        lines += ["", "FAILED:"] + [f"  {p}: {why}" for p, why in rep.failed[:500]]
        lines += [f"  {p}: verification mismatch" for p in (extra_failures or [])]
    if rep.skipped:
        lines += ["", "Skipped:"] + [f"  {p}: {why}" for p, why in rep.skipped[:500]]
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    lay = QVBoxLayout(dlg)
    text = QPlainTextEdit("\n".join(lines))
    text.setReadOnly(True)
    lay.addWidget(text)
    bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    bb.rejected.connect(dlg.reject)
    bb.accepted.connect(dlg.accept)
    lay.addWidget(bb)
    dlg.resize(640, 420)
    dlg.exec()
