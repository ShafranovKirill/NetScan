import json
from netscan import history
from netscan.core import Result


def test_snapshot_and_corruption(tmp_path,monkeypatch):
    path=tmp_path/'history.json';monkeypatch.setattr(history,'_path',lambda:path)
    monkeypatch.setattr(history,'_disabled',lambda:False)
    r=Result('192.0.2.4:3128','192.0.2.0/24','OK')
    history.save_history([r]);assert history.load_history()==[r]
    assert set(json.loads(path.read_text())['results'][0])==set(r.__dict__)
    path.write_text('corrupt');assert history.load_history()==[]
