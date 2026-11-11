# Project status — 2026-11-11

**Overall:** Phases 0–3 complete (with documented limitations), Phase 4 in progress, Phase 5 artifacts produced
locally. The application is functional end-to-end on simulated cards; the remaining release blocker is
validation of UDisks2 operations on real hardware (KI-1).

## Completed this session
* Full audit of the upstream PowerShell tool and of Onion OS's on-card layout (`docs/UPSTREAM_AUDIT.md`).
* Architecture, threat model, parity matrix, roadmap, decision record.
* Python package `onion_desktop` (≈ 4.5 k lines): Qt-free core (safe paths, validated ZIP extraction, copy engine),
  Onion logic (versions, detection, releases, downloader, installer, flags, packages, Wi-Fi), backup/restore,
  Linux layer (sysfs system-disk probe, lsblk, UDisks2 via jeepney, guarded DiskManager, NetworkManager).
* PySide6 GUI with 9 pages, threaded workers, device polling, 4 themes.
* 126 automated tests (unit, integration, security, GUI, D-Bus contracts).
* Reproducible AppImage build (pinned + checksummed inputs), packaging test script, CI workflows.

## Current implementation status
See `FEATURE_PARITY.md`. Summary: 22 features ✅/🟡, 3 intentionally different, migration wizard partial,
sounds not implemented.

## Remaining tasks
See `NEXT_STEPS.md` — real-hardware validation first, then CI observation, migration wizard.

## Security concerns
None open at critical/high severity in code review. KI-1 is rated High only because the privileged path has not yet
been observed on a real system; it fails closed by design.
