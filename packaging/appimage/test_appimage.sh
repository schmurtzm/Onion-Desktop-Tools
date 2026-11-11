#!/usr/bin/env bash
# Packaging tests for a built AppImage. Must run as a NON-root user.
# Usage: test_appimage.sh path/to/Onion_Desktop_Tools-*.AppImage
set -euo pipefail
APPIMAGE="$(readlink -f "$1")"
export APPIMAGE_EXTRACT_AND_RUN=1 TMPDIR="${TMPDIR:-$(mktemp -d)}"
fail() { echo "FAIL: $*" >&2; exit 1; }

echo "== launches and reports version (bundled Python, isolated env)"
env -i HOME="$HOME" PATH=/usr/bin:/bin TMPDIR="$TMPDIR" APPIMAGE_EXTRACT_AND_RUN=1 "$APPIMAGE" --version | grep -q "Onion Desktop Tools" \
  || fail "version"

echo "== all pages render off-screen, Qt image plugins present"
out=$(env -i HOME="$HOME" PATH=/usr/bin:/bin TMPDIR="$TMPDIR" APPIMAGE_EXTRACT_AND_RUN=1 QT_QPA_PLATFORM=offscreen "$APPIMAGE" --self-test 2>/dev/null)
echo "$out"
echo "$out" | grep -q '"ico_plugin": true' || fail "self-test"

if command -v xvfb-run >/dev/null; then
  echo "== xcb platform plugin loads under Xvfb"
  QT_QPA_PLATFORM=xcb xvfb-run -a "$APPIMAGE" --self-test 2>/dev/null | grep -q '"platform": "xcb"' || fail "xcb"
fi

echo "== read-only device listing works"
"$APPIMAGE" --list-devices >/dev/null 2>&1 || fail "list-devices"

echo "== card inspection works on a folder"
d=$(mktemp -d); mkdir -p "$d/.tmp_update/onionVersion"; printf 'v4.3.1' > "$d/.tmp_update/onionVersion/version.txt"
"$APPIMAGE" --inspect "$d" | grep -q '"version": "4.3.1"' || fail "inspect"

echo "== icon and desktop entry embedded"
x=$(mktemp -d); (cd "$x" && "$APPIMAGE" --appimage-extract >/dev/null)
test -s "$x/squashfs-root/onion-desktop-tools.png" || fail "icon"
grep -q '^Exec=onion-desktop-tools' "$x/squashfs-root/onion-desktop-tools.desktop" || fail "desktop entry"
test -s "$x/squashfs-root/usr/share/licenses/onion-desktop-tools/LICENSE" || fail "license"
echo "ALL APPIMAGE TESTS PASSED"
