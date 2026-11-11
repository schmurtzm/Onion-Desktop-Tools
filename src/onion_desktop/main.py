"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import APP_NAME, __version__


def _list_devices() -> int:
    from .core.models import human_size
    from .linux.disk_manager import create_default_manager

    mgr = create_default_manager()
    out = []
    for d in mgr.list_disks():
        out.append({
            "device": d.device, "model": d.display_name, "size": d.size, "size_h": human_size(d.size),
            "bus": d.bus, "backend": d.backend, "protected": list(d.protected_reasons),
            "partitions": [{"device": p.device, "fs": p.fs_type, "fs_version": p.fs_version, "label": p.label,
                            "mount_points": list(p.mount_points)} for p in d.partitions],
        })
    print(json.dumps({"backend": mgr.backend.name, "can_modify": mgr.can_modify, "disks": out}, indent=2))
    return 0


def _inspect(path: str) -> int:
    from pathlib import Path

    from .onion.detection import detect_card
    c = detect_card(Path(path))
    print(json.dumps({"root": str(c.root), "state": c.state.value, "version": c.version,
                      "update_pending": c.update_pending, "fs_type": c.fs_type, "free_bytes": c.free_bytes}, indent=2))
    return 0


def _self_test() -> int:
    """Render every page off-screen (used by packaging tests)."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QTimer

    from .gui.app import create_app
    from .gui.main_window import PAGES, MainWindow
    from .gui.state import AppState
    from .settings import Settings

    app = create_app([sys.argv[0]])

    class _NoDisks:
        name, can_modify = "selftest", False

        def list_disks(self):  # type: ignore[no-untyped-def]
            return []
    from .linux.disk_manager import DiskManager
    win = MainWindow(AppState(Settings(), DiskManager(_NoDisks(), system_probe=dict)))
    win.show()
    for i, (key, _label) in enumerate(PAGES):
        win.sidebar.setCurrentRow(i)
        app.processEvents()
        if win.stack.currentWidget() is not win.pages[key]:
            print(f"page {key} failed to show", file=sys.stderr)
            return 1
    QTimer.singleShot(0, app.quit)
    app.exec()
    from PySide6.QtGui import QImageReader
    fmts = {bytes(f.data()).decode() for f in QImageReader.supportedImageFormats()}
    print(json.dumps({"pages": [k for k, _ in PAGES], "platform": app.platformName(), "ico_plugin": "ico" in fmts,
                      "qt": __import__("PySide6").__version__}))
    return 0 if "ico" in fmts else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="onion-desktop-tools", description=f"{APP_NAME} {__version__} (Linux)")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    parser.add_argument("--debug", action="store_true", help="verbose logging")
    parser.add_argument("--list-devices", action="store_true", help="print detected block devices as JSON and exit")
    parser.add_argument("--inspect", metavar="PATH", help="print the Onion state of a mounted card folder and exit")
    parser.add_argument("--self-test", action="store_true", help="render all pages off-screen and exit")
    args = parser.parse_args(argv)

    from . import logging_setup, paths
    logging_setup.configure(paths.log_dir() if not args.self_test else None, args.debug)

    if args.list_devices:
        return _list_devices()
    if args.inspect:
        return _inspect(args.inspect)
    if args.self_test:
        return _self_test()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        print(f"{APP_NAME} must not be run as root. Start it as your normal user; privileged disk operations "
              "are authorised through Polkit when needed.", file=sys.stderr)
        return 1
    from . import settings
    try:
        from .gui.app import run
    except ImportError as exc:
        print(f"Cannot start the graphical interface: {exc}\nA Qt platform library may be missing on this system "
              "(for X11: libxcb-cursor0; see TROUBLESHOOTING.md).", file=sys.stderr)
        return 1
    return run(settings.load())


if __name__ == "__main__":
    sys.exit(main())
