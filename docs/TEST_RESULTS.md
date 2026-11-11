# Test results

## Session 2026-11-11 (environment: Ubuntu 24.04 container, x86_64, no system D-Bus, no real SD card)

| Check | Command | Result |
|---|---|---|
| Lint | `ruff check src tests` | ✅ clean |
| Types | `mypy` (strict, all non-GUI packages, 33 files) | ✅ no issues |
| Tests as root, PySide6 6.12.0, Python 3.13 | `QT_QPA_PLATFORM=offscreen pytest -q` | ✅ 125 passed, 1 skipped (permission test needs non-root) |
| Tests as non-root user | same, user `odttest` | ✅ 126 passed |
| Tests with AppImage's PySide6 6.9.3 | separate venv | ✅ 125 passed, 1 skipped |
| Coverage | `pytest --cov` | 74 % total (before D-Bus contract tests); core/onion/backup modules 83–97 % |
| Regression proof for temp-symlink fix | test run against pre-fix code | ❌ fails before fix, ✅ passes after |
| GUI self-test (offscreen) | `python -m onion_desktop --self-test` | ✅ all 9 pages, ico plugin present |
| Visual review | offscreen screenshots of all pages in light, dark, Dracula | ✅ reviewed; fixed mnemonic `&` and dashboard alignment |
| AppImage build | `bash packaging/appimage/build.sh` | ✅ 92,858,872 bytes |
| AppImage SHA-256 | `dist/*.sha256` | `aeb6189ae07fac87bc4bdc8cbd4f5081fc355381e23605337e9ee3920f374c86` |
| glibc baseline | `work/glibc-baseline.txt` | 2.28 (libQt6Core) |
| AppImage packaging tests (non-root) | `packaging/appimage/test_appimage.sh` | ✅ version, offscreen self-test, **xcb under Xvfb**, `--list-devices`, `--inspect`, icon/desktop/licence embedded |
| No host Python required | AppImage run with every `/usr/bin/python3*` bind-mounted to `/dev/null` | ✅ version, self-test, list-devices |
| Root refusal | AppImage started as root | ✅ refuses with message |
| Missing X11 libs | run on X11 without `libxcb-cursor0` etc. | ✅ AppRun prints package names; with libs installed xcb loads |
| Real device detection | `--list-devices` on this VM | ✅ system disk `/dev/vda` reported *protected: hosts system mount point /*; read-only virtio disks protected |

### Not executed (and why)
* Any operation on a real SD card or through a real UDisks2 / Polkit / NetworkManager daemon — no system bus or
  removable media in this environment, and destructive tests require explicit authorisation (KI-1, KI-2).
* GitHub Actions runs (CI matrix, multi-distro smoke tests) — workflows written and YAML-validated, not yet run.
* Python 3.10/3.11 interpreters — not available locally; covered by the CI matrix.

## Quality scores (evidence-based, end of this session)

| Area | Score | Evidence |
|---|---|---|
| Correctness | 8 | 126 tests across unit/integration/security; install/backup/restore round-trips on simulated cards; real detection verified. Not 9+: UDisks2 paths unverified on hardware. |
| Feature completeness | 8 | 22/26 parity rows ✅/🟡, 3 ➖ by design, 1 🔶 (migration wizard), 1 ❌ (sounds). |
| Linux compatibility | 7 | AppImage glibc 2.28 baseline, xcb + offscreen verified, Wayland plugin bundled; distro matrix not yet observed green. |
| Security | 8 | Threat model T1–T14 each with tests; two review passes (found and fixed temp-symlink issue); no shell, no root. Real Polkit flow unverified. |
| Reliability | 7 | Cancel/retry/resume/verify everywhere, failure reports; FAT32 non-atomicity documented; untested on flaky real hardware. |
| Maintainability | 8 | Layered packages, strict mypy on non-GUI code, ruff clean, ADRs. GUI not type-checked strictly. |
| UI/UX | 7 | Consistent pages, themes, shortcuts, accessible names, actionable errors; no in-app migration wizard; screenshots only offscreen. |
| Test coverage | 7 | 74 % lines overall (core ≥ 83 %); GUI interaction paths and real D-Bus are the gaps. |
