# Upstream audit — Onion Desktop Tools (Windows, PowerShell)

Audited revision: `099551c` ("Update README.md"), which carries `Menu.ps1` header
`# Onion-Desktop-Tools-v0.0.9`. Upstream: <https://github.com/schmurtzm/Onion-Desktop-Tools>.
This fork (`SpikeTheDragon40k/Onion-Desktop-Tools`) contained the upstream tree unmodified
at the start of the port.

Onion OS itself was also inspected (`OnionUI/Onion`, shallow clone at `07505ea`) to confirm
the on-card layout the tool depends on (version files, package manager, release naming).

## 1. Scripts and responsibilities

| File | Responsibility | Called from |
|---|---|---|
| `_Onion Desktop Tools - Launcher*.bat` | Self-elevate to Administrator (`FSUTIL DIRTY` probe + `Start-Process -Verb RunAs`), create `backups/` and `downloads/ODT_updates/`, copy `ODT_update.ps1` to a temp copy and run it | user |
| `ODT_update.ps1` | Self-update: query `api.github.com/repos/Schmurtzm/Onion-Desktop-Tools/releases/latest`, compare `tag_name` with the first line of `Menu.ps1` (string comparison `-gt`), download `zipball_url`, extract with `7z.exe`, `Move-Item -Force` over the install dir, then dot-source `Menu.ps1` | launcher |
| `Menu.ps1` | Main window (WinForms TabControl): *Install or Update Onion*, *Onion configuration*, *Backup or Restore Onion*, *SD card tools*, *About*. OK button dispatches to scripts. Eject icon calls `RemoveDrive.exe`. Optional `-HighDPI` calls `SetProcessDPIAware` via P/Invoke | `ODT_update.ps1` |
| `Disk_selector.ps1` | Drive picker dialog. Runs `tools\RMPARTUSB.exe LIST`, regex-parses `DRIVE n - size desc Fw= Sno= X:`. **Auto-checks the radio button when exactly one drive is listed** (also for formatting) | Menu & most scripts |
| `Disk_Format.ps1` | FAT32 format: resolve letter (`RMPARTUSB drive=N GETDRV`), classify content (empty / Onion / fresh Onion / stock / other / no partition) to build a warning, Yes/No confirm, `LockHunter32.exe /unlock /kill /silent`, then `RMPARTUSB-old.exe drive=N WINPE FAT32 NOACT VOLUME=Onion` (old build avoids hidden boot partition) | Menu |
| `Onion_Install_Download.ps1` | Downloader dialog: latest prerelease from `/repos/OnionUI/Onion/releases` (first with `prerelease`), latest stable from `/releases/latest`; asset filter `*Onion-v*`; shows version + size; "i" opens release page; downloads with `tools\wget.exe` in a console window into `downloads\`, progress by polling file size; success = size equals API `size`. Already-downloaded (size match) entries are disabled | Menu |
| `Onion_Install_Extract.ps1` | Choose a `downloads\*.zip`, classify target card, free-space check against `7z l` total, per-state confirmation text, extract with `7z x -y -aoa` (overwrite all) to drive root, success/fail sound | Menu |
| `Onion_Save_Backup.ps1` | Backup selected categories to `backups\<yyyy-MM-dd HH.mm.ss>_<state>_<version>\` with robocopy (progress by parsing robocopy logs). Writes `Backupinfo_<date>.txt` (date, source state/version, free text description) | Menu |
| `Onion_Save_Restore.ps1` | List backup folders (newest first), show `Backupinfo_*.txt`, enable only categories present in backup, robocopy each category back to the card (overwrites changed files). Contains a dead copy of the extract function | Menu |
| `Onion_Config_00_settings.ps1` | Onion "flag file" editor driven by `config.json`. Toggling renames `<flag>` ↔ `<flag>_` in `<card>\.tmp_update\config` | Menu (Onion configuration tab, auto-discovered by `Onion_Config_*.ps1` glob, label = first comment line) |
| `Onion_Config_01_Emulators.ps1` | Emulators/apps manager: scans `App\PackageManager\data\{Emu,RApp,App}\<Pack>\<Type>\<folder>`; status green (installed: `<card>\<Type>\<folder>` exists), orange (ROMs present in `Roms\<sys>`), none. Install = `Copy-Item <pack>\* <card>\ -Recurse -Force`; Auto-install = all orange; Uninstall = `Remove-Item <card>\<Type>\<folder> -Recurse -Force`; filter box; double-click opens folders | Menu |
| `Onion_Config_02_wifi.ps1` | Wi-Fi: SSID + password text boxes; "Get Wifi info from this PC" runs `PC_WifiInfo.ps1`. Writes a one-shot `runtime.sh` (original renamed `runtime_ori.sh`) that appends a `network={ssid="..." psk="..."}` block to `/appconfigs/wpa_supplicant.conf` on the device, then restores and runs the original. If `runtime.sh` is missing it **overwrites `.tmp_update/updater`** instead | Menu |
| `PC_WifiInfo.ps1` | `netsh wlan export profile key=clear` into `$HOME\GetWifiPassword_<guid>\` (**cleanup commented out — clear-text keys left on disk**), parse XML, show one button per profile | Wi-Fi script |
| `config.json` | Flag definitions for the configuration editor (see §5) | settings script |

## 2. Windows Forms interfaces

Main menu (tabs + OK button + eject icon), drive selector, format confirmation `MessageBox`,
downloader, extractor (file list + read-only log text box), backup (checkboxes, description
dialog, progress bar), restore (backup list, category checkboxes, info pane), configuration
(tabbed checkboxes with tooltips), emulator manager (`DataGridView` with colours, filter,
type combo, Install/Auto-Install/Uninstall/Help), Wi-Fi dialog, PC Wi-Fi picker, self-update
prompt. All long operations run on the UI thread (robocopy loops call `DoEvents`).

## 3. Windows-specific dependencies

| Dependency | Use | Notes |
|---|---|---|
| `RMPARTUSB.exe` / `RMPARTUSB-old.exe` | list USB drives, map drive number → letter, partition+format FAT32 | closed-source freeware (RMPrepUSB) |
| `fat32format.exe` | (shipped, unused in scripts) | |
| `LockHunter*.exe` + `USRFindHandle*.sys` | kill processes holding the drive before format | kernel driver |
| `RemoveDrive.exe` | safe eject | Uwe Sieber freeware |
| `7z.exe`, `7z.dll`, `7-zip.dll` | zip extraction, size listing, cheat.7z extraction | LGPL/BSD (7-Zip) |
| `wget.exe`, `curl.exe` | downloads | GPL / MIT |
| `strings.exe` | read version from `installUI` binary | Sysinternals licence |
| `robocopy.exe`, `chkdsk`, `netsh wlan`, `Get-Volume`, `Get-PSDrive` | copy, check disk, Wi-Fi export, FS type, free space | Windows built-ins |
| `user32.dll SetProcessDPIAware`, `System.Media.SoundPlayer`, `Microsoft.VisualBasic.Interaction` | DPI, sounds, message boxes | .NET |
| UAC elevation | whole app runs as Administrator | |

## 4. Module dependency graph

```
Launcher.bat → ODT_update.ps1 → Menu.ps1
Menu.ps1 → Disk_selector.ps1 (Get_Drive)
         → Disk_Format.ps1 → RMPARTUSB-old, LockHunter
         → Onion_Install_Download.ps1 → GitHub API, wget
         → Onion_Install_Extract.ps1 → 7z, strings
         → Onion_Save_Backup.ps1 → robocopy, strings, 7z (cheat.7z)
         → Onion_Save_Restore.ps1 → robocopy, strings
         → Onion_Config_*.ps1 (glob) → config.json, PC_WifiInfo.ps1 → netsh
         → RemoveDrive.exe, chkdsk
```
Scripts share state through dot-sourcing and global variables (`$selectedTag`, `$script:SdCardState`).

## 5. Configuration and data formats

* `config.json`: `{"Onion_Configuration": {"<Section>": [{"filename": ".flag", "short_description", "description", "sub_option": 0|1}]}}`.
  Sections: System, Time, User interface, Network. `sub_option: 1` = indented child option.
* Onion flags: presence of an (often empty) file in `<card>/.tmp_update/config/`. Disabled flags are
  renamed with a trailing underscore by ODT (Onion itself just deletes/creates them; a `.flag_`
  file is simply "absent" to Onion).
* Backup folder: `<yyyy-MM-dd HH.mm.ss>_<State>_<Version>/` with sub-trees mirroring the card
  (`Roms`, `Saves`, `BIOS`, `RetroArch/.retroarch`, `.tmp_update/config`) and
  `Backupinfo_<yyyy-MM-dd_HH.mm.ss>.txt` (`Date: …\r\nSource: <state> <version>\r\nDescription:\r\n<text>`).
* Wi-Fi: wpa_supplicant `network={ ssid="…" psk="…" }` appended to `/appconfigs/wpa_supplicant.conf` on device.

## 6. Onion install / update behaviour

* Card state detection (repeated in five scripts):
  1. no entries → `empty`
  2. `.tmp_update/bin/installUI` exists → `Onion`; version = `strings installUI` regex `--version\s+(.*?)\s`, fallback `.tmp_update/onionVersion/version.txt`
  3. `.tmp_update` and `miyoo/app/.tmp_update/onion.pak` exist → `Onion_InstallPending` (zip extracted, device not booted yet)
  4. `RApp/` exists → `Stock`
  5. else `Other`
* Install = extract release zip to card root with overwrite-all. The device performs the real
  install on next boot (`miyoo/app/.tmp_update/install.sh` unpacks `onion.pak` and
  `RetroArch/retroarch.pak`). ROMs/saves are preserved because the zip does not contain them.
* Confirmation text depends on state; stock and "other" cards get strong warnings.
* Free-space check compares 7-Zip's uncompressed total with `Get-PSDrive` free space.
* Confirmed in Onion source: `version.txt` holds `v<VERSION>`; release asset `Onion-v<VERSION>.zip`
  (tagged) or `Onion-v<VERSION>-<sha>.zip` (pre-release); Onion compares versions by stripping
  letters and splitting on `.`/`-`.

## 7. Backup and restore behaviour

| Category | Onion source | Stock source | Filter |
|---|---|---|---|
| Roms | `Roms/` | `Roms/` | exclude directories named `Imgs` |
| Imgs | `Roms/**/*.png` | `Imgs/<sys>/**/*.png` → `Roms/<sys>/Imgs/` | `*.png` |
| Saves | `Saves/` (only if `version.txt` exists) | disabled | |
| BIOS | `BIOS/` | `RetroArch/.retroarch/system/` | stock excludes dirs `cheats`, `cheats备用版`, `GLupeN64`, `Mupen64plus`, `scummvm`, `pscnbios`, files `scph39*`; then extracts `tools/cheat.7z` (FBNeo `cheat.dat`) into `BIOS/fbneo/cheats` |
| Retroarch config | `RetroArch/.retroarch/*.cfg` (depth 1) | disabled | |
| Onion config flags | `.tmp_update/config/.*` | disabled | |

"Other" cards: every category disabled. Restore copies each selected category back (robocopy
overwrites changed files, no conflict prompt) and plays a sound. No verification, failures
are not reported (robocopy exit codes ignored).

## 8. SD card formatting and validation

* Detection relies on RMPARTUSB listing USB drives only; internal SD readers may not appear.
* Format: MBR, single FAT32 partition, label `Onion`, no active flag. No post-format verification.
* "Check for errors" opens `chkdsk X: /F /X` in a console.
* No system-disk protection beyond RMPARTUSB's USB-only listing. Single-drive auto-selection.

## 9. Emulator / application installation

See §1. Onion's own on-device package manager (`src/packageManager`) additionally runs
`install.sh`/`uninstall.sh` inside the package and its uninstall removes **only files that
exist in the package data** (then empty dirs) — less destructive than ODT's recursive delete.

## 10. Wi-Fi configuration

See §1. SSID and password are interpolated unescaped into a shell script executed as root on
the device (`echo -e "...ssid=\"$ssid\"..."`) → **shell injection / broken config** for SSIDs or
passwords containing `"`, `$`, `` ` ``, `\`. The fallback that overwrites `.tmp_update/updater`
destroys a pending Onion installation.

## 11. Licensing

* Upstream: GPL-3.0 (`LICENSE`). This port remains GPL-3.0-or-later compatible and keeps
  attribution to Schmurtz / Onion Team.
* Bundled Windows binaries (`tools/`) are third-party freeware/OSS under their own licences;
  the Linux port uses **none** of them and does not ship them in the AppImage.
* `tools/cheat.7z` contains FBNeo `cheat.dat` (FBNeo-cheats project). The port ships it
  re-packed as `cheat.zip` (identical `cheat.dat`, verified SHA-256 in tests) to avoid a 7z
  runtime dependency; attribution in `THIRD_PARTY_NOTICES.md`.
* Images/icons/sounds in `tools/res` are part of the upstream repository (GPL-3.0).
* Python dependencies of the port: PySide6 (LGPL-3.0), httpx (BSD-3), httpcore (BSD-3),
  h11 (MIT), anyio (MIT), idna (BSD-3), certifi (MPL-2.0), sniffio (MIT/Apache-2.0),
  jeepney (MIT).
