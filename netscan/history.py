"""Credential-free result snapshot; not a live connectivity guarantee."""
from dataclasses import asdict, fields
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
from PySide6.QtCore import QStandardPaths
from netscan.core import Result


def _path():
    return Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericDataLocation)) / 'NetScan' / 'results.json'


def _disabled():
    return os.environ.get('NETSCAN_NO_HISTORY') == '1' or os.environ.get('NETSCAN_SMOKE_TEST') == '1'


def load_history() -> list[Result]:
    if _disabled(): return []
    try:
        p = _path()
        if p.stat().st_size > 10_000_000: return []
        document = json.loads(p.read_text(encoding='utf-8'))
        if document.get('version') != 1: return []
        allowed = {f.name for f in fields(Result)}
        results = []
        for row in document['results'][:10000]:
            if not isinstance(row, dict) or set(row) != allowed: continue
            if not all(isinstance(v, str) for k,v in row.items() if k != 'elapsed_ms'): continue
            if not isinstance(row['elapsed_ms'], int): continue
            results.append(Result(**row))
        return results
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return []


def save_history(results: list[Result]) -> None:
    if _disabled(): return
    path = _path(); path.parent.mkdir(parents=True, exist_ok=True)
    data = {'version':1, 'saved_at':datetime.now().astimezone().isoformat(),
            'results':[asdict(r) for r in results[:10000]]}
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as out:
            name = out.name
            json.dump(data,out,ensure_ascii=False)
        os.chmod(name,0o600)
        os.replace(name,path)
    finally:
        if name and os.path.exists(name): os.unlink(name)
