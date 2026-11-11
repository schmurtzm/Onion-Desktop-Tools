# Security model and threat analysis

## Assets
User data on SD cards (ROMs, saves, configs), data on the host's **other** disks (above all the
system disk), local backups, Wi-Fi credentials, integrity of the Onion OS image written to cards.

## Trust boundaries
1. **User ↔ GUI** — the only source of authorisation for destructive operations.
2. **GUI process (unprivileged) ↔ UDisks2 (root daemon)** — privileged actions are requested over
   D-Bus and authorised by Polkit. The app never runs as root (it refuses to start as root).
3. **Network ↔ app** — GitHub API metadata and release downloads are untrusted until validated.
4. **SD card contents ↔ app** — file names, symlinks, sizes and package folders on a card are
   untrusted input (cards can be crafted).
5. **App ↔ Miyoo device** — anything written into scripts executed on the device must not be
   able to inject commands.

## Threats and controls

| # | Threat | Control | Test |
|---|---|---|---|
| T1 | Formatting the wrong disk (system disk, wrong USB stick) | No auto-selection; candidates exclude disks hosting `/`, `/boot`, `/boot/efi`, `/home`, `/usr`, `/var`, swap or any mounted system path (resolved through dm/LVM/LUKS `slaves`); non-removable/non-hotplug, read-only and >2 TiB disks are refused; typed confirmation of the device name | `tests/unit/test_disk_classification.py`, `tests/security/test_disk_safety.py` |
| T2 | TOCTOU: card swapped between confirmation and format | Format takes a `DiskIdentity` (device, serial, size, model, drive object); it re-enumerates and re-classifies immediately before each privileged call and aborts on any mismatch | `tests/security/test_disk_safety.py` |
| T3 | Privilege escalation / command injection | No `shell=True`, no `sudo`/`pkexec`; subprocess only for `lsblk` with fixed argv; privileged work delegated to UDisks2 | `tests/security/test_no_shell.py` (static scan) |
| T4 | Zip slip / absolute paths / symlinks / device files in archives | All members validated before writing: no absolute, drive-letter, `..`, backslash, NUL, symlink or special-file entries; final path must stay under target; declared vs. written size enforced | `tests/security/test_archive_safety.py` |
| T5 | Zip bomb / disk exhaustion | Total declared size checked against free space; streaming writes stop if an entry exceeds its declared size; compression-ratio cap | same |
| T6 | Tampered/corrupt download | HTTPS only, host allowlist on every redirect, asset name/URL pattern check, size check, SHA-256 check when GitHub provides `digest`, archive structure check before install; partial downloads never replace good files | `tests/unit/test_releases.py`, `tests/integration/test_downloader.py` |
| T7 | Symlinks on card / in backups redirecting writes or reads outside the tree | Walks never follow symlinks (reported as skipped); `safe_join` rejects symlinked components | `tests/security/test_symlinks.py` |
| T8 | Overwriting existing backups | Backup folders created with `exist_ok=False`, unique suffix on collision | `tests/integration/test_backup_restore.py` |
| T9 | Silent overwrite of ROMs/saves on restore or package install | Restore plans conflicts first; default policy *skip*; overwrite only after explicit choice; package install never overwrites files under `Roms/` | same, `test_emulators.py` |
| T10 | Shell injection on device via Wi-Fi SSID/password | Credentials never enter shell code: written to a data file in wpa_supplicant syntax (hex SSID when needed, validated passphrase), static script `cat`s it | `tests/security/test_wifi_injection.py` |
| T11 | Credential leakage | Wi-Fi secrets fetched from NetworkManager only on explicit click (Polkit-gated by NM), never logged; logging filter redacts `psk=`, `password=`; nothing written to temp files | `tests/unit/test_logging.py` |
| T12 | Partial failure reported as success | Every operation returns a report with copied/skipped/failed lists; GUI shows failures; non-empty `failed` ⇒ operation status *failed* | integration tests |
| T13 | Self-update executing remote code | Update *check* only; user is sent to the release page; no auto-replacement | n/a |
| T14 | Unexpected device removal mid-operation | I/O errors captured per file; temp files cleaned; report marks the operation failed; FAT32 non-atomicity documented | `test_copier.py` (simulated errors) |

## Residual risks
* FAT32 has no journaling: an interrupted install/restore can leave a partially updated card.
  Mitigation: re-running install (repair) is idempotent; backups before upgrades are offered.
* GitHub does not always provide asset digests; then integrity relies on TLS + size + archive
  structure checks.
* Polkit policy is controlled by the distribution; on some systems formatting removable
  media requires no password.
