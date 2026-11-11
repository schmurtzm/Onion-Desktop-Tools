# Known issues and limitations

| ID | Severity | Issue | Mitigation / plan |
|---|---|---|---|
| KI-1 | **High (until validated)** | UDisks2 operations (mount, unmount, format, check/repair, power-off) have only been exercised against fake backends and D-Bus contract tests; the development container has no system bus. | Real-hardware validation with an explicitly authorised throw-away SD card (NEXT_STEPS #1). Formatting logic fails closed on any unexpected state. |
| KI-2 | Medium | NetworkManager import (saved SSIDs / password) untested against a live NM. | Same validation session; feature is optional. |
| KI-3 | Medium | No single "migrate stock card" wizard; the user performs Backup → Format → Install → Restore manually (each step is implemented and tested). | Implement a guided wizard (NEXT_STEPS #3). |
| KI-4 | Low | FAT32 has no journaling: an interrupted install/restore may leave a partially written card. | Re-run install (idempotent repair); temp-file+rename per file; failures are reported, never shown as success. |
| KI-5 | Low | Qt's X11 plugin needs host libs `libxcb-cursor0`, `libxkbcommon-x11-0`, `libxcb-icccm4`, `libxcb-keysyms1` (missing on some minimal installs). Wayland sessions are unaffected. | AppRun prints the exact package names per distro; TROUBLESHOOTING.md. |
| KI-6 | Low | Success/failure sounds from upstream not implemented. | Optional; setting reserved. |
| KI-7 | Low | Package `install.sh` scripts (device-side) are not run when installing packages from the desktop (same as upstream ODT). | UI warns; open the on-device Package Manager if a package needs it. |
| KI-8 | Info | The Wi-Fi password sits in plain text on the card until the console applies it (the console's own `wpa_supplicant.conf` is also plain text). | Documented on the Wi-Fi page; file removed by the device hook after use. |
| KI-9 | Info | `appimagetool` packs with mksquashfs timestamps; byte-for-byte reproducibility of the AppImage is not guaranteed (inputs are pinned). | Inputs pinned by SHA-256; checksum published per build. |
| KI-10 | Info | x86_64 only. | aarch64 build would need PBS aarch64 + PySide6 aarch64 wheels (available) — future work. |

Security concerns resolved during development: zip-slip/symlink/device entries (archive pre-validation),
planted temp-file symlinks on crafted cards (fixed in e2e67c3, regression test), Wi-Fi shell injection,
clear-text Wi-Fi export to disk (upstream), silent restore overwrite.
