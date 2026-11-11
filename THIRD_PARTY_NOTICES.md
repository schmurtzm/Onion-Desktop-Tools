# Third-party notices

Onion Desktop Tools for Linux is licensed under the GNU GPL v3.0 (see `LICENSE`). It is a port of
[Onion Desktop Tools](https://github.com/schmurtzm/Onion-Desktop-Tools) by Schmurtz (Onion Team), GPL-3.0.

The AppImage bundles:

| Component | Licence | Source |
|---|---|---|
| CPython 3.12 (python-build-standalone) | PSF-2.0 (+ bundled OpenSSL Apache-2.0, SQLite PD, zlib, libffi MIT, …) | https://github.com/astral-sh/python-build-standalone |
| Qt 6 / PySide6-Essentials, Shiboken6 | LGPL-3.0 | https://www.qt.io/qt-for-python — Qt libraries are shipped as unmodified shared libraries and can be replaced by the user |
| httpx, httpcore | BSD-3-Clause | https://github.com/encode/httpx |
| h11 | MIT | https://github.com/python-hyper/h11 |
| anyio | MIT | https://github.com/agronholm/anyio |
| idna | BSD-3-Clause | https://github.com/kjd/idna |
| certifi | MPL-2.0 | https://github.com/certifi/python-certifi |
| sniffio | MIT / Apache-2.0 | https://github.com/python-trio/sniffio |
| jeepney | MIT | https://gitlab.com/takluyver/jeepney |
| AppImage type2-runtime | MIT | https://github.com/AppImage/type2-runtime |

Data files:

| File | Origin |
|---|---|
| `resources/fbneo_cheat.zip` | FBNeo `cheat.dat` from the FBNeo-cheats project (https://github.com/finalburnneo/FBNeo-cheats), as shipped by upstream ODT in `tools/cheat.7z`; repacked as ZIP, content unchanged (SHA-256 `7c32380c…ceae`) |
| `resources/*.ico`, `*.png`, `onion_flags.json` | Upstream Onion Desktop Tools repository (GPL-3.0) |

Onion OS itself is downloaded at run time from https://github.com/OnionUI/Onion and is not bundled.
