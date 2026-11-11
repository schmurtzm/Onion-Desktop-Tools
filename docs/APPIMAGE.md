# AppImage build

## Tooling choice
* **Base interpreter:** [python-build-standalone](https://github.com/astral-sh/python-build-standalone)
  `cpython-3.12.8+20250106-x86_64-unknown-linux-gnu-install_only` — relocatable, built for glibc 2.17,
  SHA-256 checked against the pinned hash (identical to upstream `SHA256SUMS`).
* **Dependencies:** wheels only (`--only-binary=:all:`) with `packaging/appimage/constraints.txt`.
  PySide6 is pinned to **6.9.3**, the newest series published as `manylinux_2_28`; PySide6 ≥ 6.10 wheels
  require glibc 2.34.
* **Packer:** `appimagetool` 1.9.0 + `type2-runtime` 20251108 (static runtime, no FUSE2 dependency on the
  host's libfuse2; FUSE3 or `--appimage-extract-and-run` works), both pinned by SHA-256 and run from an
  extracted copy so no FUSE is needed at build time.
* Considered: `python-appimage` (resolves base images through the GitHub API at build time), `linuxdeploy`
  + `linuxdeploy-plugin-conda` (larger, conda licensing), PyInstaller/Nuitka (more fragile Qt plugin handling).

## Build
```bash
bash packaging/appimage/build.sh            # → dist/Onion_Desktop_Tools-<ver>-x86_64.AppImage (+ .sha256)
bash packaging/appimage/test_appimage.sh dist/Onion_Desktop_Tools-*-x86_64.AppImage   # as a non-root user
```
Host requirements for building: bash, curl, tar, sha256sum, `desktop-file-validate` (desktop-file-utils),
and Qt runtime libs for the icon conversion step (`libegl1 libgl1 libxkbcommon0 libfontconfig1`).

## Layout
`AppRun` (refuses root, explains missing X11 libs, runs `usr/python/bin/python3 -I -m onion_desktop`),
`onion-desktop-tools.desktop`, 256 px icon + `.DirIcon`, AppStream metainfo, `usr/share/licenses/…`.
Unused Qt modules (Quick/QML, PDF, SQL, Multimedia, Designer tools…) and Python test/Tk modules are removed.
`work/glibc-baseline.txt` records the highest `GLIBC_2.x` symbol needed by any bundled ELF.

## Host runtime requirements
* glibc ≥ 2.28, x86_64.
* For disk operations: `udisks2` (+ `dosfstools` for FAT32 formatting/checks) and a Polkit agent — standard on
  GNOME, KDE Plasma, Xfce, Cinnamon. Without UDisks2 the app runs in read-only mode.
* X11 sessions: `libxcb-cursor0 libxkbcommon-x11-0 libxcb-icccm4 libxcb-keysyms1` (usually present).
* Optional: NetworkManager for importing saved Wi-Fi networks.
