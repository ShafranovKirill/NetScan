# NetScan — 0.2.0

Updated: 2026-11-18 11:35 Europe/Moscow.

Goal and authorization: installable Russian-language proxy scanner, prioritized user-supplied IPv4 subnet queue, search3128, optional proxy authentication, verified Google/Example HTTPS, stop after N working results. User approved implementation/testing and publishing installers to GitHub Releases. Latest UX request: sidebar pages, no slogan or numbered panels, separate strict IPv4 and mask default /24; supplied PNG logo. Default working mode; main must remain untouched.

Implemented and merged through PR1 into develop: new sidebar UX, strict IPv4 and /24 mask with single-IP shortcut, saved numeric preferences, OS credential vault (Secret Service/Linux, Credential Manager/Windows), user logo across application/icons/installers. Defaults on this device are configured in OS vault; never copy credentials or real inventories into repository or release notes.

Core scanner: bounded concurrency, priority by subnet, pause/stop, exact N working result limit, per-client proxy routing, Basic only after407, TLS verification, CSV export/recheck. No system networking, DNS, Throne or proxy settings changed. Network verification showed success with current local credentials; do not record values here.

Validation:22 targeted tests pass; source and frozen GUI lifecycle pass. Compatible Linux binary built in Debian12 container (glibc2.36), actual DEB installation/start/removal and AppImage startup passed in Debian12 before upload. RPM metadata inspected; Fedora GUI launch validated. UI screenshots inspected. No external full subnet sweep. Existing initial GUI may remain open; avoid terminating an active user scan.

Packaging/release: GitHub Actions registered successfully after an initial delay. Release v0.2.0 is published with Linux RPM/DEB/AppImage and Windows Setup EXE/portable ZIP: https://github.com/ShafranovKirill/NetScan/releases/tag/v0.2.0 . Both cloud builds passed, including DEB and Windows installer install/start/remove tests and AppImage smoke. Cloud test count22. Run: https://github.com/ShafranovKirill/NetScan/actions/runs/44267440319 . PR1 merged: https://github.com/ShafranovKirill/NetScan/pull/1 . Release commit f3a5e7fb2097d6bd0b317c6f5c1a0895ab910f7f; main untouched.

Local new UI launched and full live UI worker scan passed with local vault defaults. Original earlier app window may also remain open; do not terminate an active user scan. Logo supplied by user is preserved in packaging/netscan.png. Private diagnostic screenshot stays outside Git in the chat outputs directory.

Compatibility: hosted Linux assets require glibc>=2.35, local Debian12 assets require2.36. All builds x86_64; unsigned. Basic only, no NTLM/Digest/Kerberos/web portal. AppImage fallback --appimage-extract-and-run. Future release: bump version, commit to working branch, review/integrate develop, push matching version tag. Optional manual workflow requires selecting the matching existing tag ref. GHCR is not required. Earlier v0.1.0 tag has no release; leave history intact.

Continue: `.venv/bin/python -m netscan`; tests `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q`; packaging `packaging/README.md`. Check Actions and assets before claiming future release delivery. Do not use main. Never include credentials in screenshots of parameter page or diagnostic logs.


## 0.2.1 follow-up
User requested removing logo from sidebar and keeping only NetScan name; logo remains window/application/installer icon. Source inventory import TXT is prepared outside Git, first current subnet then other networks ranked by a lightweight check of each listed .1 endpoint on3128; this is a heuristic, not an exhaustive subnet scan. No private inventory or credentials committed.

0.2.1 published successfully through Actions: https://github.com/ShafranovKirill/NetScan/releases/tag/v0.2.1 . PR2 merged, release commitde3a56b; cloud tests and Linux/Windows package install checks passed. User subnet import file generated in chat outputs,65 unique networks with current network first. Representative .1/.21/.200 checks did not find additional verified proxies outside the known current network. User is now discussing potential additions (Throne/Nekoray export etc.); no implementation of new features approved yet.


## 0.3.0 approved scope
User approved nearest proposed update: quick share-link export for selected working proxies (Throne/Nekoray), bulk selection/copy, optional TXT exports and automatic credential-free result persistence. Keep existing ready-to-use defaults and system connection untouched. No auto-switching, background monitors or scan-resume implemented. URI format matched against official Nekoray fmt/Link2Bean.cpp QUrl parser and Throne protocol reference. Private live tests and exports must stay outside Git.
