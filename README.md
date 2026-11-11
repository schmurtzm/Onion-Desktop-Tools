# Onion Desktop Tools — Linux

A program to install, update, back up and configure [Onion OS](https://github.com/OnionUI/Onion) SD cards for the
Miyoo Mini / Mini Plus — **Linux port** of [Onion Desktop Tools](https://github.com/schmurtzm/Onion-Desktop-Tools)
by Schmurtz (Onion Team), distributed as a single AppImage.

## Features
- Detects SD cards and card readers (UDisks2), never offers system disks
- Formats SD cards in FAT32 (explicit device choice, typed confirmation, verification)
- Checks / repairs the card's file system (fsck.vfat via UDisks2)
- Downloads the latest Onion OS (stable or beta) with checksum verification and resume
- Installs, updates or repairs Onion while keeping ROMs, saves and settings
- Backs up / restores cards (also migrates the Miyoo stock card to Onion), compatible with Windows ODT backups
- Onion configuration manager, emulators & apps manager, Wi-Fi manager
- Light, dark, Dracula and system themes; Wayland and X11; high-DPI

## Install and run
```bash
chmod +x Onion_Desktop_Tools-*-x86_64.AppImage
./Onion_Desktop_Tools-*-x86_64.AppImage
```
Run it as your normal user, **not with sudo**: disk operations ask for authorisation through your desktop (Polkit).
Requirements: x86_64 Linux with glibc ≥ 2.28 (Ubuntu 20.04+, Debian 10+, Fedora, Arch, openSUSE Leap 15.6+, RHEL/Rocky 8+),
`udisks2` and `dosfstools` for formatting (standard on GNOME/KDE desktops). See
[docs/USER_GUIDE.md](docs/USER_GUIDE.md) and [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

## Development
```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q
.venv/bin/onion-desktop-tools              # run from source
bash packaging/appimage/build.sh           # build the AppImage (docs/APPIMAGE.md)
```
Design and status: [architecture](docs/ARCHITECTURE.md) · [security model](docs/SECURITY_MODEL.md) ·
[feature parity](docs/FEATURE_PARITY.md) · [upstream audit](docs/UPSTREAM_AUDIT.md) ·
[project status](docs/PROJECT_STATUS.md) · [known issues](docs/KNOWN_ISSUES.md).

------------------------------------------------
# Original Windows version

Onion Desktop Tools is a Windows program that simplifies the preparation of a micro SD card for Onion
([download v0.0.9](https://github.com/schmurtzm/Onion-Desktop-Tools/archive/refs/tags/v0.0.9.zip)). The original
PowerShell sources are kept in this repository's root folder for reference.

A tutorial video about Onion Desktop Tool, preparing a new fresh SD card:

[![Onion Desktop Tool - Video Presentation](https://img.youtube.com/vi/moE52Dw2x64/0.jpg)](https://youtu.be/moE52Dw2x64)

An advanced tutorial video (configurator, emulators manager, Wi-Fi, backup/restore, SD card tools):

[![Onion Desktop Tool - Video Presentation](https://img.youtube.com/vi/QyzKe8Lqdi8/0.jpg)](https://youtu.be/QyzKe8Lqdi8)

## Licence
GPL-3.0 (see [LICENSE](LICENSE)); third-party components in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
