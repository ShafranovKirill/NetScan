#!/usr/bin/env bash
set -euo pipefail
VERSION="${1:?Usage: packaging/linux.sh VERSION}"
GLIBC_MIN="${NETSCAN_GLIBC_MIN:-$(getconf GNU_LIBC_VERSION | cut -d ' ' -f 2)}"
rm -rf build/root build/NetScan.AppDir

mkdir -p release build/root/opt/netscan build/root/usr/bin build/root/usr/share/applications build/root/usr/share/icons/hicolor/256x256/apps
cp -a dist/NetScan/. build/root/opt/netscan/
cat > build/root/usr/bin/netscan <<'LAUNCH'
#!/bin/sh
exec /opt/netscan/NetScan "$@"
LAUNCH
chmod +x build/root/usr/bin/netscan
cp packaging/netscan.desktop build/root/usr/share/applications/
cp build/icons/netscan.png build/root/usr/share/icons/hicolor/256x256/apps/
for kind in deb rpm; do
  extra=()
  if [ "$kind" = deb ]; then
    extra=(--depends "libc6 >= $GLIBC_MIN" --depends libxcb-cursor0 --depends libxkbcommon-x11-0 --depends libegl1 --depends libgl1 --depends libglib2.0-0 --depends libfontconfig1 --depends libdbus-1-3)
  else
    extra=(--depends "glibc >= $GLIBC_MIN" --depends xcb-util-cursor --depends libxkbcommon-x11 --depends mesa-libEGL --depends mesa-libGL --depends glib2 --depends fontconfig --depends dbus-libs)
  fi
  fpm -s dir -t "$kind" -n netscan -v "$VERSION" --architecture x86_64 \
      --license MIT --maintainer 'Kirill Shafranov' \
      --url https://github.com/ShafranovKirill/NetScan \
      --description 'NetScan desktop HTTP proxy scanner' \
      "${extra[@]}" -C build/root -p "release/NetScan-${VERSION}-x86_64.${kind}" .
done
mkdir -p build/NetScan.AppDir/usr/bin
cp -a dist/NetScan build/NetScan.AppDir/usr/bin/
cat > build/NetScan.AppDir/usr/bin/netscan <<'LAUNCH'
#!/bin/sh
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
exec "$HERE/NetScan/NetScan" "$@"
LAUNCH
chmod +x build/NetScan.AppDir/usr/bin/netscan
cp packaging/netscan.desktop build/NetScan.AppDir/
cp build/icons/netscan.png build/NetScan.AppDir/
cat > build/NetScan.AppDir/AppRun <<'LAUNCH'
#!/bin/sh
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
exec "$HERE/usr/bin/NetScan/NetScan" "$@"
LAUNCH
chmod +x build/NetScan.AppDir/AppRun
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 ./build/appimagetool-x86_64.AppImage \
  build/NetScan.AppDir "release/NetScan-${VERSION}-x86_64.AppImage"
