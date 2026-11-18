# Third-party components

NetScan's own code is MIT licensed. Bundled dependencies retain their own licenses.
The build copies installed distribution license files into THIRD_PARTY_LICENSES.

- Python: Python Software Foundation License — https://www.python.org/psf/license/
- PySide6 / Shiboken6 / Qt: LGPLv3 / GPLv3 / commercial, with individual Qt
  components under their respective terms — https://doc.qt.io/qtforpython-6/licenses.html
  and https://www.qt.io/licensing/open-source-lgpl-obligations
- HTTPX: BSD-3-Clause — https://github.com/encode/httpx
- HTTP Core: BSD-3-Clause — https://github.com/encode/httpcore
- AnyIO: MIT — https://github.com/agronholm/anyio
- Certifi: MPL-2.0 — https://github.com/certifi/python-certifi
- h11: MIT — https://github.com/python-hyper/h11
- IDNA: BSD-3-Clause — https://github.com/kjd/idna
- PyInstaller bootloader: GPL with distribution exception — https://pyinstaller.org/en/stable/license.html

The Linux packages and Windows installer use a directory distribution with shared
Qt libraries. Recipients may replace those libraries with compatible modified
versions. The portable Windows executable can be extracted with PyInstaller
archive tools. Full upstream sources and modification instructions are available
at the links above; NetScan does not modify these dependencies.
