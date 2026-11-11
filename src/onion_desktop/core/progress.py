"""Progress reporting and cooperative cancellation shared by all long operations."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass

from .exceptions import OperationCancelled


@dataclass(frozen=True)
class Progress:
    message: str
    done: int = 0
    total: int = 0  # 0 = indeterminate

    @property
    def fraction(self) -> float | None:
        if self.total <= 0:
            return None
        return max(0.0, min(1.0, self.done / self.total))


ProgressCallback = Callable[[Progress], None]


def null_progress(_: Progress) -> None:
    """Progress sink that discards updates."""


class CancelToken:
    """Thread-safe cancellation flag checked by workers between units of work."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self._event.is_set():
            raise OperationCancelled()
