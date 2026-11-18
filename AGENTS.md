# NetScan

Python + PySide6 + httpx. Entry point: `python -m netscan`.
- Core: `netscan/core.py`; Qt interface: `netscan/ui.py`.
- Tests: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q`.
- Build: `.venv/bin/python packaging/build.py`; packaging instructions in `packaging/README.md`.
- Never persist proxy credentials, actual network inventories, private diagnostic data or environment secrets in source/results/logs.
- Never alter system networking, proxy, DNS or routes. All checks use per-client explicit proxies.
- Keep TLS verification enabled and distinguish open ports from confirmed internet connectivity.
- Work in feature/fix branches, integrate to develop; main requires explicit authorization.
- Version tags publish installers through GitHub Actions; update project and UI versions together.
