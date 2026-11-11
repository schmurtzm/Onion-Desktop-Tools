"""Reusable widgets."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .worker import Task


def title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("pageTitle")
    lbl.setAccessibleName(text)
    return lbl


def subtle(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("subtle")
    lbl.setWordWrap(True)
    return lbl


def status_label(text: str = "", kind: str = "") -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    if kind:
        lbl.setObjectName(kind)
    return lbl


class Card(QFrame):
    def __init__(self, heading: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(14, 12, 14, 12)
        if heading:
            h = QLabel(f"<b>{heading}</b>")
            self.body.addWidget(h)


class TaskPanel(QWidget):
    """Progress bar + message + cancel button bound to a running Task."""

    finished = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        self.bar = QProgressBar()
        self.bar.setTextVisible(True)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setAccessibleName("Cancel operation")
        row.addWidget(self.bar, 1)
        row.addWidget(self.cancel_btn)
        lay.addLayout(row)
        self.msg = QLabel()
        self.msg.setObjectName("subtle")
        self.msg.setWordWrap(False)
        self.msg.setTextFormat(Qt.TextFormat.PlainText)
        lay.addWidget(self.msg)
        self.task: Task | None = None
        self.cancel_btn.clicked.connect(self._cancel)
        self.setVisible(False)

    def attach(self, task: Task) -> None:
        self.task = task
        self.bar.setRange(0, 0)
        self.msg.setText("Starting…")
        self.cancel_btn.setEnabled(True)
        self.setVisible(True)
        task.progressed.connect(self._on_progress)
        task.done.connect(self._on_done)

    def _on_progress(self, msg: str, done: int, total: int) -> None:
        metrics = self.msg.fontMetrics()
        self.msg.setText(metrics.elidedText(msg, Qt.TextElideMode.ElideMiddle, max(200, self.msg.width())))
        if total > 0:
            self.bar.setRange(0, total)
            self.bar.setValue(done)
        else:
            self.bar.setRange(0, 0)

    def _cancel(self) -> None:
        if self.task:
            self.task.cancel()
            self.cancel_btn.setEnabled(False)
            self.msg.setText("Cancelling…")

    def _on_done(self) -> None:
        self.task = None
        self.setVisible(False)
        self.finished.emit()

    @property
    def busy(self) -> bool:
        return self.task is not None


class LogView(QPlainTextEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(5000)
        self.setAccessibleName("Operation log")

    def log(self, text: str) -> None:
        self.appendPlainText(text)
