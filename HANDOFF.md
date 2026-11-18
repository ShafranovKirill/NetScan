# NetScan — 0.2.0

Updated: 2026-11-18 11:28 Europe/Moscow.

Goal and authorization: installable Russian-language proxy scanner, prioritized user-supplied IPv4 subnet queue, search3128, optional proxy authentication, verified Google/Example HTTPS, stop after N working results. User approved implementation/testing and publishing installers to GitHub Releases. Latest UX request: sidebar pages, no slogan or numbered panels, separate strict IPv4 and mask default /24; supplied PNG logo. Default working mode; main must remain untouched.

Implemented in feat/sidebar-ui: new sidebar UX, strict IPv4 and /24 mask with single-IP shortcut, saved numeric preferences, OS credential vault (Secret Service/Linux, Credential Manager/Windows), user logo across application/icons/installers. Defaults on this device are configured in OS vault; never copy credentials or real inventories into repository or release notes.

Core scanner: bounded concurrency, priority by subnet, pause/stop, exact N working result limit, per-client proxy routing, Basic only after407, TLS verification, CSV export/recheck. No system networking, DNS, Throne or proxy settings changed. Network verification showed success with current local credentials; do not record values here.

Validation:22 targeted tests pass; source and frozen GUI lifecycle pass. Compatible Linux binary built in Debian12 container (glibc2.36), actual DEB installation/start/removal and AppImage startup passed in Debian12 before upload. RPM metadata inspected; Fedora GUI launch validated. UI screenshots inspected. No external full subnet sweep. Existing initial GUI may remain open; avoid terminating an active user scan.

Packaging: Linux RPM/DEB/AppImage and Windows Setup EXE/portable ZIP. GitHub Actions has tag and manually requested release builds, SHA/version validation, installer smoke checks and idempotent upload. Optional GHCR not required. Actions enabled but GitHub currently exposes zero workflows/runs despite valid files/default develop; exact cause unknown (registration delay is only a hypothesis). Windows executable not yet built or validated. Source workflow validated with actionlint and release-validation tests.

Current release plan: publish0.2.0 Linux preview only after local install tests; Windows assets require an actual hosted Windows run. Linux local artifacts require glibc>=2.36, x86_64; no digital signing. AppImage fallback --appimage-extract-and-run. Earlier tagv0.1.0 exists but has no release; leave history intact.

Continue: `.venv/bin/python -m netscan`; tests `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q`; packaging `packaging/README.md`. Check PR/release and GitHub Actions state before claiming Windows delivery. Do not use main. Never include credentials in screenshots of parameter page or diagnostic logs.
