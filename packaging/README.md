# Building NetScan 0.1.0

All bundles target x86-64. Build Windows binaries on Windows and Linux packages
on Linux. No credentials or subnet inventory belong in build inputs.

Install Python 3.12 and development dependencies:

```sh
python -m pip install -e '.[dev]'
python -m pytest -q
python packaging/build.py
```

`dist/NetScan` is a standalone directory including its Python runtime and Qt shared
libraries. It does not require Python on the target machine. Keep the complete
directory together. For Windows the setup installer and portable ZIP both retain
this directory layout, permitting replacement of compatible Qt libraries.

Linux packaging requires Ruby/fpm, rpm, and appimagetool. See the workflow for exact
commands, dependency packages, and the pinned appimagetool checksum.
`bash packaging/linux.sh 0.1.0` emits DEB, RPM, and AppImage into `release/`.
AppImage may need FUSE on the target; without FUSE, launch using
`APPIMAGE_EXTRACT_AND_RUN=1 ./NetScan-0.1.0-x86_64.AppImage`.

Windows packaging requires Inno Setup 6:

```powershell
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" /DAppVersion=0.1.0 packaging/windows.iss
```

GitHub Actions runs tests before building. Manual runs produce downloadable
artifacts. A `v0.1.0` tag publishes the installers as a GitHub Release after all
builds succeed; the tag must match the version in `pyproject.toml`. Update that
version before tagging subsequent releases. Publishing a tag is a separate step.

Builds are unsigned. Windows may display its usual unknown-publisher prompt.
Cross-platform CI builds do not replace installation testing on each target OS.
