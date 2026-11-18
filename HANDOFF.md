# NetScan — initial release

Updated: 2026-11-18 (Europe/Moscow).

Goal: installable Russian-language Qt app for prioritized IPv4 subnet proxy discovery on port 3128, Basic authentication after challenge, verified HTTPS checks, stop after N working results, pause/stop/retest and CSV export. User authorized implementation, local network testing and GitHub release installers. Default working mode. Main must remain untouched.

Implemented: core scanner, PySide6 UI, local subnet preferences (no passwords), tests, packaging for RPM/DEB/AppImage and Windows Setup/portable ZIP; release-on-tag GitHub Actions. Repository began empty; work started on feat/netscan. Develop will be established from reviewed initial implementation.

Validation: targeted tests, GUI offscreen lifecycle, and actual proxy checks in the user's current local subnet. Live test with concurrency 4 and limit 2 stopped at exactly two verified proxies. No system networking, proxy settings, Throne or DNS changed. No private inventory or credentials committed.

Known limits: Basic proxy authentication only (not NTLM/Digest/Kerberos/web portal), fixed Google and Example.com HTTPS targets, x86_64 installers, no signing, pause/stop waits for in-flight request timeouts. Local subnet queue persists; scan progress/results are not restored after restart. Full remote build/install verification pending until CI finishes; check GitHub Actions before claiming release artifacts are available.

Continue: `.venv/bin/python -m netscan`; tests `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q`; packaging `packaging/README.md`. Review actual workflow run status and fix failures, then tag release only after tests pass. Do not store credentials or real proxy inventories in this file.
