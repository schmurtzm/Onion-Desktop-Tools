# Troubleshooting

| Symptom | Cause / fix |
|---|---|
| "must not be run as root" | Start the AppImage as your normal user. Privileged actions ask for authorisation through Polkit. |
| Window does not open on X11; terminal mentions `xcb` or `libxcb-cursor` | Install the X11 helper libraries. Debian/Ubuntu: `sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libxcb-icccm4 libxcb-keysyms1`; Fedora: `sudo dnf install xcb-util-cursor libxkbcommon-x11 xcb-util-wm xcb-util-keysyms`; Arch: `sudo pacman -S xcb-util-cursor libxkbcommon-x11 xcb-util-wm xcb-util-keysyms`. |
| `dlopen(): error loading libfuse.so.2` / AppImage won't mount | Run with `--appimage-extract-and-run`, or install FUSE (`fuse3`). |
| SD Cards page says "lsblk (read-only)" | UDisks2 is not running/installed: `sudo apt install udisks2` (or your distro's equivalent) and `systemctl start udisks2`. |
| Formatting says "Authorisation was denied" | Your Polkit agent refused or was cancelled; retry and enter your password. On headless sessions no agent is available. |
| Format finished but "not FAT32" | Very small cards (<512 MB) may get FAT16; use a larger card. The operation is reported as failed. |
| Format or Repair fails with "device is busy" | Close file managers/terminals using the card, then retry. ODT never kills processes. |
| My card is listed as "Protected" | It hosts a system mount, is internal eMMC, read-only (check the lock switch), non-removable or > 2 TB. Protected devices can never be modified. |
| Install says "not enough space" | Free space on the card or use a bigger card; the check includes room for safe file replacement. |
| Install "incomplete" | Some files could not be written (bad card, removed card). Run **Check for errors**, then install again to repair. |
| Restore shows skipped files | Those files already existed on the card with different content and you chose to keep them. Restore again with *Overwrite* if wanted. |
| Wi-Fi import button fails | Requires NetworkManager. Enter SSID and password manually instead. |
| GitHub rate limit | Wait a few minutes; anonymous GitHub API access is limited per IP. |
| Where are my files? | Downloads and backups: `~/.local/share/onion-desktop-tools/`; settings: `~/.config/onion-desktop-tools/`; logs: `~/.local/state/onion-desktop-tools/logs/`. |
