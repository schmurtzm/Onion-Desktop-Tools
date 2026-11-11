# Development roadmap

| Phase | Scope | State (2026-11-11) |
|---|---|---|
| 0 — Audit & planning | Upstream audit, parity matrix, architecture, threat model, roadmap, skeleton | **Done** |
| 1 — Linux foundation | Entry point, main window, navigation, themes, settings, logging, read-only detection, tests, build pipeline | **Done** |
| 2 — Onion installation | Release discovery, verified downloads, install/upgrade/repair, verification | **Done** (simulated cards) |
| 3 — Feature parity | Format, emulators, configuration, Wi-Fi, backup, restore, repair | **Done except**: single-step migration wizard (🔶), sounds (❌); UDisks2/NM paths need real-system validation |
| 4 — Hardening | Full security review, extended errors, perf, UX, multi-distro | **In progress** — two security review passes done; multi-distro smoke tests written for CI, not yet observed green on GitHub |
| 5 — Release | AppImage, CI, docs, release notes, checksums | **Mostly done** — AppImage builds and passes packaging tests locally; first tagged release pending CI run and real-device validation |

## Exit-criteria tracking
* Phase 1 exit (launches; inspects removable storage read-only) — met: `--self-test` (offscreen + xcb), `--list-devices`.
* Phase 2 exit (install/update pass integration tests with simulated cards) — met: `tests/integration/test_installer.py`.
* Phase 3 exit (every feature implemented or documented limitation) — met, see FEATURE_PARITY.md.
* Phase 4 exit (no known critical/high issues; workflows pass required tests) — **not yet**: KI-1 (real UDisks2
  validation) is rated High until executed on hardware.
* Phase 5 exit (AppImage generated, checksum recorded, release validations passed) — AppImage + checksum produced
  locally (TEST_RESULTS.md); CI release validations pending.
