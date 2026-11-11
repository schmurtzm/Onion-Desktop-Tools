# Feature parity matrix

Status legend: ✅ implemented and tested · 🟡 implemented, partially verified (see notes) · 🔶 partial ·
➖ intentionally different (documented) · ❌ not implemented.

"Tests" lists automated tests; **no test touches a real block device** (real-device testing needs explicit
human authorisation and is tracked in NEXT_STEPS.md).

| # | Upstream feature | Upstream implementation | Linux replacement | Dependencies | Status | Tests |
|---|---|---|---|---|---|---|
| 1 | Launcher / admin elevation | `.bat` + `RunAs` (whole app elevated) | App runs unprivileged and **refuses root**; per-operation Polkit via UDisks2 | polkit, udisks2 | ➖ by design | `test_appimage.sh` (root refusal manual), `main.py` |
| 2 | Self-update | `ODT_update.ps1` downloads zipball & overwrites itself | Update **check** only (About page / optional at start); opens release page | httpx | ➖ (no self-replacement, security) | — |
| 3 | Main window, tabs | WinForms TabControl | PySide6 sidebar + pages, global target selector, themes, high-DPI, shortcuts (F5, Ctrl+1…9) | PySide6 | ✅ | `test_gui.py`, `--self-test` |
| 4 | Drive selector | `RMPARTUSB LIST` regex, auto-selects single drive | UDisks2 (lsblk fallback) enumeration, live polling (3 s, off GUI thread), protected-disk classification; auto-select only for non-destructive use | udisks2 / util-linux | ✅ | `test_disk_classification.py`, `test_gui.py` |
| 5 | Format FAT32 | `RMPARTUSB-old … WINPE FAT32 NOACT VOLUME=Onion`, LockHunter kill | UDisks2 `Block.Format(dos)` + `CreatePartitionAndFormat(0x0c, vfat, ONION)`; explicit device choice + typed device confirmation; TOCTOU identity re-check before every step; post-format FAT32 verification; no process killing | udisks2, dosfstools | 🟡 logic fully tested with fake backend; **not yet run against a real UDisks2 daemon** | `test_disk_safety.py`, `test_dbus_contracts.py` |
| 6 | Content-aware format warning | Onion/stock/other/empty text | Same rules from mounted partitions | — | ✅ | `test_gui.py` |
| 7 | Check disk (`chkdsk /F /X`) | console window | UDisks2 `Filesystem.Check` / `Repair` (fsck.vfat), auto-unmount | udisks2, dosfstools | 🟡 (contract-tested) | `test_dbus_contracts.py` |
| 8 | Eject | `RemoveDrive.exe` | unmount all + `Drive.PowerOff` (fallback `Eject`) | udisks2 | 🟡 | `test_dbus_contracts.py` |
| 9 | Stable/beta discovery | GitHub API `releases/latest` + first prerelease | Same semantics; strict asset-name and URL validation; rate-limit message | httpx | ✅ | `test_releases.py` |
| 10 | Download with progress | `wget.exe` + size polling | Streaming httpx, cancel, retries with backoff, HTTP Range resume, redirect host allowlist, size + SHA-256 (GitHub `digest`) + archive structure checks, sidecar metadata | httpx | ✅ | `test_downloader.py` |
| 11 | Card state detection | 5 duplicated copies, `strings.exe` | `onion/detection.py` (same rules; version.txt first, then binary scan; update-pending flag) | — | ✅ | `test_detection.py` |
| 12 | Install / upgrade / repair | `7z x -aoa` to root, per-state confirmation | Validated in-process extraction, temp+rename, per-state confirmation text, downgrade/reinstall modes, typed confirmation for stock/other/non-FAT, net space check, post-extract CRC verification from medium, card-changed guard | — | ✅ | `test_installer.py`, `test_archive_safety.py` |
| 13 | Format + install | chained in menu | After a successful format the user is offered to continue to install with the new card selected | — | ✅ | manual |
| 14 | Migrate stock → Onion | backup → format → install → restore chain | Same steps available (Backup page → SD Cards format → Install → Restore); no single wizard yet | — | 🔶 | `test_backup_restore.py` (stock rules) |
| 15 | Backup categories | robocopy with filters | Copy engine with identical filters (Imgs exclusion, png, stock BIOS excludes, cfg depth 1, dot flags), profiles, description, per-file SHA-256 manifest, failure report, never overwrites backups | — | ✅ | `test_backup_restore.py` |
| 16 | Stock BIOS cheats | `7z x cheat.7z` → `BIOS/fbneo/cheats` | bundled `fbneo_cheat.zip` (same `cheat.dat`), stock backups only | — | ✅ (➖ only for stock) | `test_stock_backup_adds_cheats` |
| 17 | Restore | robocopy, silent overwrite | Plan → conflict detection → user choice (keep / overwrite) → copy → checksum verification against manifest; Windows ODT backups (no manifest) supported | — | ✅ | `test_backup_restore.py` |
| 18 | Onion configuration flags | rename `flag`↔`flag_` per click | Same on-card semantics; staged changes + Apply; automatic snapshot; restore last snapshot; unknown flags preserved & listed | — | ✅ | `test_config_emulators_wifi.py` |
| 19 | Emulators & apps manager | DataGridView, copy/remove | Table with colours, type/status/text filters, install, auto-install (orange), uninstall, open folder, help image | — | ✅ | `test_config_emulators_wifi.py` |
| 20 | Package uninstall semantics | `Remove-Item -Recurse` of whole folder | Onion pacman semantics: only package files, then empty dirs; user files and ROMs kept | — | ➖ (safer) | same |
| 21 | Wi-Fi configuration | runtime.sh hook with interpolated credentials | Validated SSID/PSK, wpa_supplicant encoding (hex SSID), static hook + data file; multiple networks queued; cancel pending | — | ✅ (➖ injection fixed; refuses non-installed Onion instead of overwriting `updater`) | `test_wifi_injection.py` |
| 22 | Wi-Fi from PC | `netsh wlan export key=clear` (keys left on disk) | NetworkManager: list SSIDs; password read only on explicit click via `GetSecrets` (Polkit), never stored/logged | NetworkManager | 🟡 (contract-tested, not run against real NM) | `test_dbus_contracts.py` |
| 23 | About / sponsors / docs links | PictureBoxes | About page with links, licence, update check | — | ✅ | `--self-test` |
| 24 | Sounds on success/failure | `SoundPlayer` | not implemented (setting reserved) | — | ❌ (low priority) | — |
| 25 | High-DPI switch | `SetProcessDPIAware` flag | Qt 6 automatic high-DPI scaling | Qt | ✅ | — |
| 26 | Distribution | zip of scripts + exes | AppImage (glibc ≥ 2.28), pinned & checksummed build, CI multi-distro smoke tests | — | ✅ | `test_appimage.sh`, `appimage.yml` |
