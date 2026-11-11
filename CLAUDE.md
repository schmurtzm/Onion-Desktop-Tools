# CLAUDE.md — Onion Desktop Tools (Linux port)

Linux/PySide6 port of the Windows PowerShell tool whose original scripts (`*.ps1`, `tools/`) remain in the repo
root as reference — do not modify or delete them.

## Before working
Read `docs/PROJECT_STATUS.md`, `docs/NEXT_STEPS.md`, `docs/KNOWN_ISSUES.md`, `docs/DECISIONS.md`.
Update those files plus `docs/TEST_RESULTS.md` at the end of each session.

## Setup
```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
# Ubuntu: sudo apt install libegl1 libgl1 libxkbcommon0 libfontconfig1   (Qt offscreen runtime)
```

## Checks (all must pass before committing)
```bash
.venv/bin/ruff check src tests
.venv/bin/mypy
QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m onion_desktop --self-test
bash packaging/appimage/build.sh && bash packaging/appimage/test_appimage.sh dist/*.AppImage   # as non-root
```

## Architecture boundaries
* `core/`, `onion/`, `backup/`, `linux/` must not import Qt. GUI (`gui/`) only calls them via `gui/worker.py`.
* Every long operation takes `progress` and `cancel` and returns a report; never report success if anything failed.
* Only `linux/disk_manager.py` may modify devices, only via UDisks2, only after `find(identity)` +
  eligibility re-check. Never add a code path that formats without typed confirmation.
* No `shell=True`, `os.system`, `sudo`/`pkexec`; subprocess only in `linux/lsblk_backend.py`
  (enforced by `tests/security/test_no_shell.py`).
* Untrusted paths (archives, card contents) go through `safe_join` / `walk_files`; new files via `open_new_file`.
* Never log Wi-Fi passwords or other secrets.

## Testing rules
* Tests use temp dirs and fake backends. Tests touching real block devices must be marked `realdevice`
  (excluded by default) and require explicit human authorisation.
* Do not mark a feature done in `docs/FEATURE_PARITY.md` without a test.
