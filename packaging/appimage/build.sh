#!/usr/bin/env bash
# Reproducible AppImage build for Onion Desktop Tools (Linux).
#
# Base: python-build-standalone CPython (relocatable, built against glibc 2.17).
# The effective glibc baseline is set by the PySide6 wheels (manylinux_2_28 → glibc ≥ 2.28).
# All downloaded tools are pinned by URL *and* SHA-256.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
WORK="${WORK:-$HERE/work}"
CACHE="$WORK/cache"
APPDIR="$WORK/AppDir"
OUT="${OUT:-$ROOT/dist}"
ARCH=x86_64

PY_URL="https://github.com/astral-sh/python-build-standalone/releases/download/20250106/cpython-3.12.8+20250106-x86_64-unknown-linux-gnu-install_only.tar.gz"
PY_SHA="c8032747c8e44ce0164236fa70a6b767a43ef778dc51b99bd18f25984f8cba3b"
TOOL_URL="https://github.com/AppImage/appimagetool/releases/download/1.9.0/appimagetool-x86_64.AppImage"
TOOL_SHA="46fdd785094c7f6e545b61afcfb0f3d98d8eab243f644b4b17698c01d06083d1"
RUNTIME_URL="https://github.com/AppImage/type2-runtime/releases/download/20251108/runtime-x86_64"
RUNTIME_SHA="2fca8b443c92510f1483a883f60061ad09b46b978b2631c807cd873a47ec260d"

fetch() {  # url sha dest
    local url="$1" sha="$2" dest="$3"
    if [ ! -f "$dest" ] || ! echo "$sha  $dest" | sha256sum -c --status; then
        echo ">> downloading $url"
        curl --fail --location --proto '=https' --tlsv1.2 --retry 3 -o "$dest.part" "$url"
        mv "$dest.part" "$dest"
    fi
    echo "$sha  $dest" | sha256sum -c --quiet || { echo "checksum mismatch for $dest" >&2; exit 1; }
}

mkdir -p "$CACHE" "$OUT"
fetch "$PY_URL" "$PY_SHA" "$CACHE/python.tar.gz"
fetch "$TOOL_URL" "$TOOL_SHA" "$CACHE/appimagetool.AppImage"
fetch "$RUNTIME_URL" "$RUNTIME_SHA" "$CACHE/runtime-$ARCH"
chmod +x "$CACHE/appimagetool.AppImage"

VERSION="$(grep -Po '^version = "\K[^"]+' "$ROOT/pyproject.toml")"
echo ">> building Onion Desktop Tools $VERSION"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/256x256/apps" \
         "$APPDIR/usr/share/metainfo" "$APPDIR/usr/share/licenses/onion-desktop-tools"
tar -xzf "$CACHE/python.tar.gz" -C "$APPDIR/usr"          # → usr/python
PY="$APPDIR/usr/python/bin/python3"

export PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1 SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-$(git -C "$ROOT" log -1 --format=%ct 2>/dev/null || date +%s)}"
"$PY" -I -m pip install --no-compile --only-binary=:all: -c "$HERE/constraints.txt" \
      PySide6-Essentials httpx jeepney
"$PY" -I -m pip install --no-compile --no-deps --no-build-isolation "$ROOT" 2>/dev/null \
  || "$PY" -I -m pip install --no-compile --no-deps "$ROOT"

# ---- trim: tools and Qt parts the application never loads -----------------------------------
SP="$APPDIR/usr/python/lib/python3.12/site-packages"
"$PY" -I -m pip uninstall -y pip setuptools wheel >/dev/null 2>&1 || true
rm -rf "$APPDIR/usr/python/lib/python3.12/test" "$APPDIR/usr/python/lib/python3.12/idlelib" \
       "$APPDIR/usr/python/lib/python3.12/tkinter" "$APPDIR/usr/python/lib/python3.12/ensurepip" \
       "$APPDIR/usr/python/lib/python3.12/lib2to3" "$APPDIR/usr/python/lib/tcl"* "$APPDIR/usr/python/lib/tk"* \
       "$APPDIR/usr/python/lib/itcl"* "$APPDIR/usr/python/lib/thread"* "$APPDIR/usr/python/include" \
       "$APPDIR/usr/python/share"
rm -f "$APPDIR/usr/python/lib/python3.12/lib-dynload/_tkinter"*
rm -rf "$SP/PySide6/Qt/qml" "$SP/PySide6/include" "$SP/PySide6/typesystems" "$SP/PySide6/glue" \
       "$SP/PySide6/scripts" "$SP/PySide6/examples"
for tool in assistant designer linguist lrelease lupdate qmlformat qmllint qmlls qmlcachegen qmltyperegistrar \
            qmlimportscanner balsam balsamui svgtoqml uic rcc androiddeployqt androiddeployqt6 qsb; do
    rm -f "$SP/PySide6/$tool" "$SP/PySide6/Qt/libexec/$tool"
done
find "$SP/PySide6" -maxdepth 1 \( -name 'QtQuick*' -o -name 'QtQml*' -o -name 'Qt3D*' -o -name 'QtDesigner*' \
      -o -name 'QtPdf*' -o -name 'QtCharts*' -o -name 'QtDataVis*' -o -name 'QtGraphs*' -o -name 'QtTest*' \
      -o -name 'QtHelp*' -o -name 'QtUiTools*' -o -name 'QtSql*' -o -name 'QtXml*' -o -name 'QtConcurrent*' \
      -o -name 'QtOpenGLWidgets*' -o -name 'QtSpatialAudio*' -o -name 'QtMultimedia*' \) -exec rm -rf {} +
find "$SP/PySide6/Qt/lib" \( -name 'libQt6Quick*' -o -name 'libQt6Qml*' -o -name 'libQt6Pdf*' -o -name 'libQt6Designer*' \
      -o -name 'libQt6Test*' -o -name 'libQt6Help*' -o -name 'libQt6UiTools*' -o -name 'libQt6Sql*' \
      -o -name 'libQt6ShaderTools*' -o -name 'libQt6Multimedia*' -o -name 'libQt6SpatialAudio*' -o -name 'libQt6Xml*' \
      -o -name 'libQt6Concurrent*' -o -name 'libQt6OpenGLWidgets*' -o -name 'libQt6Charts*' -o -name 'libQt6Graphs*' \
      -o -name 'libQt6DataVisualization*' -o -name 'libQt63D*' \) -delete
rm -rf "$SP/PySide6/Qt/plugins/"{qmltooling,sqldrivers,designer,multimedia,scenegraph,qmllint,assetimporters,sceneparsers,renderers,geometryloaders,renderplugins} 2>/dev/null || true
find "$APPDIR/usr/python" -name '__pycache__' -type d -prune -exec rm -rf {} +
"$PY" -I -m compileall -q -j0 --invalidation-mode unchecked-hash "$SP/onion_desktop" >/dev/null

# ---- desktop integration ---------------------------------------------------------------------
install -m 755 "$HERE/AppRun" "$APPDIR/AppRun"
install -m 644 "$HERE/onion-desktop-tools.desktop" "$APPDIR/onion-desktop-tools.desktop"
install -m 644 "$HERE/onion-desktop-tools.desktop" "$APPDIR/usr/share/applications/"
install -m 644 "$HERE/io.github.onion_desktop_tools.metainfo.xml" "$APPDIR/usr/share/metainfo/onion-desktop-tools.appdata.xml"
QT_QPA_PLATFORM=offscreen "$PY" -I - "$SP/onion_desktop/resources/onion.ico" "$APPDIR/onion-desktop-tools.png" <<'PYEOF'
import sys
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtCore import Qt
app = QGuiApplication([])
img = QImage(sys.argv[1])
assert not img.isNull(), "cannot read icon"
img.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation).save(sys.argv[2])
PYEOF
cp "$APPDIR/onion-desktop-tools.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/onion-desktop-tools.png"
ln -sf onion-desktop-tools.png "$APPDIR/.DirIcon"
cp "$ROOT/LICENSE" "$ROOT/THIRD_PARTY_NOTICES.md" "$APPDIR/usr/share/licenses/onion-desktop-tools/"

# ---- glibc baseline report -------------------------------------------------------------------
"$PY" -I - "$APPDIR" <<'PYEOF' | tee "$WORK/glibc-baseline.txt"
import os, re, sys
best = (0, 0); who = ""
for root, _, files in os.walk(sys.argv[1]):
    for f in files:
        p = os.path.join(root, f)
        if os.path.islink(p) or not (f.endswith(".so") or ".so." in f or os.access(p, os.X_OK)):
            continue
        try:
            data = open(p, "rb").read()
        except OSError:
            continue
        if not data.startswith(b"\x7fELF"):
            continue
        for m in set(re.findall(rb"GLIBC_2\.(\d+)", data)):
            v = (2, int(m))
            if v > best:
                best, who = v, os.path.relpath(p, sys.argv[1])
print(f"Highest required glibc symbol version: {best[0]}.{best[1]} (from {who})")
PYEOF

# ---- pack ------------------------------------------------------------------------------------
OUTFILE="$OUT/Onion_Desktop_Tools-$VERSION-$ARCH.AppImage"
# Run appimagetool from an extracted copy: works without FUSE and avoids shared /tmp extraction dirs.
if [ ! -x "$CACHE/appimagetool-root/AppRun" ]; then
    rm -rf "$CACHE/appimagetool-root" "$CACHE/squashfs-root"
    ( cd "$CACHE" && ./appimagetool.AppImage --appimage-extract >/dev/null && mv squashfs-root appimagetool-root )
fi
rm -f "$OUTFILE"
# mksquashfs rejects SOURCE_DATE_EPOCH together with the -mkfs-time option appimagetool passes.
env -u SOURCE_DATE_EPOCH ARCH=$ARCH "$CACHE/appimagetool-root/AppRun" --no-appstream \
    --runtime-file "$CACHE/runtime-$ARCH" "$APPDIR" "$OUTFILE"
( cd "$OUT" && sha256sum "$(basename "$OUTFILE")" > "$(basename "$OUTFILE").sha256" )
echo ">> built $OUTFILE"
cat "$OUTFILE.sha256"
