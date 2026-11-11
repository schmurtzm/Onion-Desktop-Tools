"""Run blocking core operations in a QThread and relay progress as Qt signals."""

from __future__ import annotations

import logging
import traceback
from collections.abc import Callable
from typing import Any, ClassVar

from PySide6.QtCore import QObject, QThread, Signal

from ..core.exceptions import OdtError, OperationCancelled
from ..core.progress import CancelToken, Progress

log = logging.getLogger(__name__)
TaskFn = Callable[[Callable[[Progress], None], CancelToken], Any]


class _Thread(QThread):
    progressed = Signal(str, int, int)
    succeeded = Signal(object)
    failed = Signal(str, str)  # message, hint/details
    cancelled = Signal()

    def __init__(self, fn: TaskFn, token: CancelToken) -> None:
        super().__init__()
        self.fn = fn
        self.token = token

    def run(self) -> None:  # executed in the worker thread
        def report(p: Progress) -> None:
            # Normalised to per-mille so multi-GB byte counts fit Qt's int32 progress values.
            frac = p.fraction
            self.progressed.emit(p.message, int(frac * 1000) if frac is not None else 0,
                                 1000 if frac is not None else 0)
        try:
            result = self.fn(report, self.token)
        except OperationCancelled:
            self.cancelled.emit()
        except OdtError as exc:
            log.warning("Operation failed: %s", exc.message)
            self.failed.emit(exc.message, exc.hint or "")
        except Exception as exc:
            log.exception("Unexpected error in background task")
            self.failed.emit(f"Unexpected error: {exc}", traceback.format_exc(limit=5))
        else:
            self.succeeded.emit(result)


class Task(QObject):
    """Handle for one background operation. Keep a reference until it finishes."""

    progressed = Signal(str, int, int)
    succeeded = Signal(object)
    failed = Signal(str, str)
    cancelled = Signal()
    done = Signal()

    _running: ClassVar[set[Task]] = set()

    def __init__(self, fn: TaskFn, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.token = CancelToken()
        self._thread = _Thread(fn, self.token)
        self._thread.progressed.connect(self._relay_progress)
        self._thread.succeeded.connect(self.succeeded)
        self._thread.failed.connect(self.failed)
        self._thread.cancelled.connect(self.cancelled)
        self._thread.finished.connect(self._on_finished)

    def _relay_progress(self, msg: str, done: int, total: int) -> None:
        self.progressed.emit(msg, done, total)

    def start(self) -> Task:
        Task._running.add(self)
        self._thread.start()
        return self

    def cancel(self) -> None:
        self.token.cancel()

    def is_running(self) -> bool:
        return self._thread.isRunning()

    def _on_finished(self) -> None:
        Task._running.discard(self)
        self.done.emit()


def run_task(fn: TaskFn, *, on_success: Callable[[Any], None] | None = None,
             on_error: Callable[[str, str], None] | None = None,
             on_progress: Callable[[str, int, int], None] | None = None,
             on_cancel: Callable[[], None] | None = None,
             on_done: Callable[[], None] | None = None) -> Task:
    t = Task(fn)
    if on_success:
        t.succeeded.connect(on_success)
    if on_error:
        t.failed.connect(on_error)
    if on_progress:
        t.progressed.connect(on_progress)
    if on_cancel:
        t.cancelled.connect(on_cancel)
    if on_done:
        t.done.connect(on_done)
    return t.start()
