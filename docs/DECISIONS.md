# Architecture decision record

| ID | Decision | Rationale | Alternatives rejected |
|---|---|---|---|
| D1 | Python 3.10+ / PySide6, Qt-free core packages (`core`, `onion`, `backup`, `linux`) | Testable without a display; GUI is a thin layer | Logic inside widgets (upstream style) |
| D2 | UDisks2 over D-Bus via **jeepney** | Pure Python (MIT), no compiled deps, keeps `linux/` Qt-free; QtDBus marshalling of `a{oa{sa{sv}}}` is unreliable in PySide6 | QtDBus, dbus-python (C ext, needs system build), shelling out to `udisksctl` (text parsing) |
| D3 | Polkit through UDisks2 only; app refuses to run as root | Least privilege; desktop agents prompt per action | pkexec helper, sudo, running GUI as root |
| D4 | `lsblk -J` read-only fallback; destructive ops fail closed without UDisks2 | Detection still works in minimal environments; no unsafe formatting path | parted/mkfs.vfat directly (needs root) |
| D5 | Format = MBR (`dos`) + one `0x0c` FAT32 partition at 1 MiB, label `ONION` (UDisks upper-cases FAT labels; upstream used `Onion`) | Matches upstream layout (no active flag, no hidden partition) | GPT, superfloppy |
| D6 | `mkfs-args ["-F","32"]` passed only when UDisks ≥ 2.10; FAT32 is always **verified** after formatting | Older UDisks ignores/lacks the option; verification makes the result certain | trusting mkfs auto-selection |
| D7 | In-process ZIP extraction with pre-validation, temp+rename, CRC re-read from medium | Removes 7-Zip dependency; enables traversal/symlink defences and real verification | 7z/unzip subprocess |
| D8 | Own copy engine instead of rsync/robocopy port | Needs per-file conflict policy, cancel, precise reports, hashes; avoids host dep | rsync with output parsing |
| D9 | Restore conflicts default to **keep the card's files**; overwrite only by explicit choice | Avoid silently replacing newer saves (requirement 7.15) | upstream silent overwrite |
| D10 | Package uninstall follows Onion's on-device package manager (delete only package files) | Never deletes user-added files; ROMs untouched | upstream `Remove-Item -Recurse` |
| D11 | Wi-Fi: credentials go to a data file; the device hook is static | Fixes upstream shell injection; supports any SSID via hex encoding | escaping inside shell script |
| D12 | Wi-Fi config refused when Onion is not installed (no `runtime.sh`) | Upstream fallback overwrote `.tmp_update/updater`, breaking pending installs | upstream behaviour |
| D13 | Config flags staged + snapshot before Apply | Gives configuration backup/reset (requirement 5.6) while keeping on-card semantics | immediate per-click rename |
| D14 | No self-replacing updater; update check only | AppImage integrity; no remote code execution path | upstream zipball overwrite |
| D15 | AppImage base = python-build-standalone CPython 3.12 (glibc 2.17) + PySide6 **6.9.3** pinned | 6.9.x is the newest PySide6 with manylinux_2_28 wheels → glibc 2.28 baseline (RHEL 8, Debian 10+, Ubuntu 20.04+). 6.12 would require glibc 2.34 | python-appimage (needs GitHub API at build time; fine for CI but not reproducible offline), linuxdeploy-plugin-python |
| D16 | All build downloads pinned by URL + SHA-256; Python launched with `-I` | Reproducibility, supply-chain hygiene, ignore user `PYTHONPATH` | floating "continuous" tools |
| D17 | Devices polled every 3 s in a worker thread | Simple, robust across backends; no GUI blocking | UDisks signal subscription (future improvement) |
| D18 | Data in XDG dirs (`~/.local/share/onion-desktop-tools/{downloads,backups}`) | Nothing written inside the AppImage | upstream app-relative folders |
| D19 | `cheat.dat` shipped as ZIP (repacked from upstream `cheat.7z`, identical content) | stdlib-only extraction | py7zr runtime dependency |
| D20 | Empty-card check ignores desktop-OS litter (`System Volume Information`, `.Trashes`, …) | A card freshly formatted on Windows/macOS is still "empty" | upstream count of all entries |
