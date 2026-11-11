# User guide

## Getting started
1. Download `Onion_Desktop_Tools-<version>-x86_64.AppImage` and its `.sha256` file; verify with
   `sha256sum -c Onion_Desktop_Tools-*.AppImage.sha256`.
2. `chmod +x Onion_Desktop_Tools-*.AppImage` and double-click it (or run it from a terminal). **Do not use sudo.**
3. Insert the SD card. Most desktops mount it automatically; otherwise use **SD Cards → Mount**.
4. Pick the card in the **SD card** selector at the top of the window. If only one removable card is mounted it is
   selected automatically (this never applies to formatting).

## Preparing a new card (recommended for Onion)
1. **SD Cards → Format FAT32…** → choose the device (nothing is pre-selected) → read the summary →
   type the device path (e.g. `/dev/sdb`) to confirm. Your desktop may ask for your password.
2. After formatting you are offered to continue to **Install / Update**.
3. **Check for releases** → choose Stable or Beta → **Download** (progress, cancel and resume supported; the
   file is verified against GitHub's SHA-256).
4. Select the downloaded version → **Install / Update / Repair** → confirm. Files are written and then read back
   from the card for verification.
5. Eject (**SD Cards → Eject**), insert the card in the Miyoo and switch it on: the console finishes the install.

## Updating or repairing Onion
Same as steps 3–5 with the existing Onion card selected. ROMs, saves and settings are kept. Choosing the version
already installed performs a repair (all Onion files are rewritten).

## Migrating from the Miyoo stock card
1. Select the **stock** card → **Backup & Restore → Backup** (ROMs, images and BIOS; FBNeo cheats are converted).
2. Insert the **new** card → format it and install Onion as above; boot it once on the console.
3. Select the new card → **Restore** → pick the stock backup → restore.

## Backups
* Stored in `~/.local/share/onion-desktop-tools/backups/` (configurable in Settings), one folder per backup,
  compatible with Windows ODT backups. Existing backups are never overwritten.
* Each backup records a checksum for every file; restores are verified against it.
* If files on the card differ from the backup (e.g. newer saves) you choose to keep them or overwrite them.
* The final report lists every skipped or failed file.

## Emulators & Apps
Green rows are installed, orange rows have ROMs on the card but the emulator is not installed (**Auto-install**
installs all of those). Uninstalling only removes files that came with the package — your ROMs and your own files
stay. Double-click a row to open its emulator or ROM folder.

## Configuration
Toggle Onion options and click **Apply to card**. A snapshot of the previous settings is saved first and can be
restored with **Restore last snapshot**. Unknown flags on the card are listed and left untouched.

## Wi-Fi (Miyoo Mini Plus)
Enter the network name and password (or import a network saved on this computer — reading its password requires
your explicit confirmation) and click **Add to SD card**. The console adds the network at its next start.
**Cancel pending Wi-Fi changes** undoes it before then.

## Command line
```
onion-desktop-tools --version | --list-devices | --inspect /path/to/card | --self-test | --debug
```
Logs: `~/.local/state/onion-desktop-tools/logs/odt.log` (passwords are never logged).
