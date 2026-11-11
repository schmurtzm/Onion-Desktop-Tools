# Next steps (prioritised)

1. **Real-hardware validation (needs explicit human authorisation).** On a desktop with UDisks2 + Polkit
   (GNOME and KDE), with a disposable SD card in a USB reader *and* in a built-in `mmcblk` reader:
   mount/unmount, format FAT32 (check `IdVersion=FAT32`, label, partition type 0x0c at 1 MiB), check/repair,
   eject/power-off, install a real Onion release and boot it on a Miyoo Mini Plus, Wi-Fi hook on device.
   Record results in TEST_RESULTS.md and downgrade KI-1/KI-2.
2. Push and watch the GitHub Actions runs (`ci.yml`, `appimage.yml`), fix any distro-specific failure in the
   smoke matrix (Rocky 8 = glibc 2.28 floor).
3. Guided "Migrate stock card" wizard chaining Backup (stock) → Format (new card) → Install → Restore.
4. Replace polling with UDisks2 `InterfacesAdded/Removed` signals (keep polling as fallback).
5. Show per-category sizes in the backup page before starting; optional ZIP backup export.
6. Optional sounds; aarch64 AppImage; AppImageUpdate zsync metadata.
