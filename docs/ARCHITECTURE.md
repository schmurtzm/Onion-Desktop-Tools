# Architecture

## Goals

* Linux-native port of Onion Desktop Tools: Python 3.10+, PySide6/Qt 6, distributed as an AppImage.
* Strict separation: **pure Onion logic** (no Qt, no D-Bus) ↔ **Linux integration** ↔ **GUI**.
* Every destructive/privileged action goes through one narrow, testable path.

## Layers

```
src/onion_desktop/
├── main.py                 CLI entry: arg parsing, root refusal, logging, Qt app bootstrap
├── paths.py                XDG directories (config/data/cache/state)
├── settings.py             JSON settings (XDG config), typed dataclass
├── logging_setup.py        rotating file log + secret-redaction filter
├── updates.py              ODT self-update *check* (no self-replacement)
├── core/                   OS-independent primitives
│   ├── exceptions.py       OdtError hierarchy with user-facing messages
│   ├── progress.py         CancelToken, Progress, callback type
│   ├── models.py           Disk, Partition, DiskIdentity (frozen dataclasses)
│   ├── safe_fs.py          safe_join, symlink-free walks, filesystem type lookup
│   ├── archive.py          validated zip extraction (traversal/symlink/bomb checks, verify)
│   └── copier.py           planned copy engine (progress, cancel, conflicts, reports, hashes)
├── onion/                  Onion OS semantics (pure Python, tested with temp dirs)
│   ├── versions.py         version parsing/ordering compatible with Onion
│   ├── detection.py        card state + version detection (upstream rules)
│   ├── releases.py         GitHub release discovery + asset/URL validation
│   ├── downloader.py       resumable download, size + SHA-256 verification, sidecar metadata
│   ├── installer.py        install planning (modes, warnings, space) + execution + verification
│   ├── configuration.py    flag schema (config.json) + flag store + config snapshot/restore
│   ├── emulators.py        package manager scan/install/uninstall (Onion pacman semantics)
│   └── wifi.py             validation, wpa_supplicant block encoding, one-shot runtime hook
├── backup/
│   ├── profiles.py         categories, availability per card state
│   ├── backup_manager.py   backup planning/execution, Backupinfo + JSON manifest
│   └── restore_manager.py  backup listing, restore planning (conflicts), execution
├── linux/
│   ├── sysprobe.py         which block devices back /, /boot, /home, swap… (sysfs/procfs)
│   ├── lsblk_backend.py    read-only detection via `lsblk -J` (fallback, no D-Bus)
│   ├── udisks2.py          UDisks2 D-Bus client (jeepney): enumerate, mount, unmount,
│   │                       format, check/repair, power-off; Polkit interactive auth
│   ├── disk_manager.py     backend selection, classification/protection, TOCTOU
│   │                       identity re-validation, guarded destructive operations
│   └── network.py          NetworkManager: saved Wi-Fi SSIDs, explicit secret fetch
└── gui/
    ├── app.py              QApplication setup, theme, high-DPI, icon
    ├── main_window.py      sidebar navigation + stacked pages + global target selector
    ├── worker.py           TaskRunner: runs core callables in QThread, signals progress
    ├── themes.py           system / light / dark / Dracula palettes
    ├── widgets.py          reusable widgets (progress panel, info card, log view)
    ├── dialogs.py          confirmation dialogs (typed device confirmation)
    └── pages/              dashboard, sdcards, install, emulators, configuration,
                            wifi, backup, settings, about
```

## Key decisions (see DECISIONS.md)

* **UDisks2 via jeepney** (pure-Python D-Bus, MIT) rather than QtDBus: QtDBus's PySide6
  marshalling of nested `a{oa{sa{sv}}}` is unreliable, and jeepney keeps `linux/` Qt-free and
  unit-testable. Polkit authorisation is requested by UDisks itself (interactive flag set);
  the GUI never runs as root and never calls `sudo`/`pkexec`.
* **lsblk fallback** for read-only listing when the system bus or UDisks is absent; destructive
  operations require UDisks2 and fail closed otherwise.
* **Zip extraction in-process** (stdlib `zipfile`), no 7-Zip. Members are validated *before*
  any write; files are written to temp names then `os.replace`d; CRC is checked by zipfile and
  the result is re-read and re-verified from disk after `fsync` + `POSIX_FADV_DONTNEED`.
* **Copy engine** instead of rsync: per-file progress/cancel/conflict decisions and precise
  failure reports are needed by the GUI; rsync would add a host dependency and output parsing.
* **Workers**: each long operation is a plain function `(…, progress, cancel) -> Report` run
  in a `QThread`; the GUI only receives signals. Device polling also happens off the GUI thread.

## Data locations (XDG)

| Purpose | Path |
|---|---|
| Settings | `$XDG_CONFIG_HOME/onion-desktop-tools/settings.json` |
| Downloads (Onion zips + `.json` sidecars) | `$XDG_DATA_HOME/onion-desktop-tools/downloads/` |
| Backups | `$XDG_DATA_HOME/onion-desktop-tools/backups/` (configurable) |
| Config snapshots | `$XDG_DATA_HOME/onion-desktop-tools/config-snapshots/` |
| Logs | `$XDG_STATE_HOME/onion-desktop-tools/logs/odt.log` |

Nothing user-specific is written inside the AppImage.

## Destructive operation pipeline

```
GUI explicit selection (no default) → typed confirmation (device name) →
DiskManager.format_fat32(identity):
    re-enumerate → find by identity → compare serial/size/model/drive object →
    re-run protection classification → unmount children (UDisks, Polkit) →
    Block.Format("dos") → PartitionTable.CreatePartitionAndFormat(0x0c, vfat, label ONION) →
    verify IdType == vfat && IdVersion == FAT32 → mount (optional)
```
