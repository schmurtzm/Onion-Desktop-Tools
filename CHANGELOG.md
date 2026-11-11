# Changelog

## 0.1.0 — first Linux release candidate (2026-11-11)

Linux-native port of Onion Desktop Tools (upstream Windows v0.0.9).

* Python 3 / PySide6 application distributed as an x86_64 AppImage (glibc ≥ 2.28).
* SD card detection via UDisks2 (read-only lsblk fallback) with system-disk protection.
* FAT32 formatting through UDisks2 + Polkit with explicit device selection, typed confirmation, device
  re-validation before each step and post-format verification.
* Onion OS stable/beta discovery, verified and resumable downloads (size + GitHub SHA-256).
* Install / upgrade / repair with validated extraction and read-back verification.
* Emulators & apps manager (install, auto-install, safe uninstall), Onion configuration editor with snapshots,
  Wi-Fi pre-configuration (injection-safe), NetworkManager import.
* Backup & restore compatible with Windows ODT backups, with checksums, conflict handling and full reports.
* Light, dark, Dracula and system themes; high-DPI; keyboard shortcuts.

Known limitations: see `docs/KNOWN_ISSUES.md` (UDisks2 operations pending real-hardware validation).
