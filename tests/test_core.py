import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import httpx
import pytest
from netscan import core


def test_network_import_normalizes_and_deduplicates():
    assert core.normalize_networks('10.0.4.1/24\r\n10.0.4.0/24;10.0.0.1') == ['10.0.4.0/24', '10.0.0.1/32']
    assert core.host_count(['10.0.0.0/24', '10.0.1.0/31', '10.0.2.0/32']) == 257
    with pytest.raises(ValueError): core.normalize_networks('::1')
    with pytest.raises(ValueError): core.normalize_networks('invalid')


def test_auth_required_real_socket():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(407)
            self.send_header('Proxy-Authenticate', 'Basic realm="lab"')
            self.send_header('Content-Length', '0')
            self.end_headers()
        def log_message(self, *args): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        result = core.test_proxy('127.0.0.1', '127.0.0.1/32', core.Options(port=server.server_port))
        assert result.status == 'Нужна авторизация'
        assert not result.working
    finally:
        server.shutdown(); server.server_close(); thread.join()


def mock_clients(monkeypatch, handler):
    real_client = httpx.Client
    class Socket:
        def __enter__(self): return self
        def __exit__(self, *args): pass
    monkeypatch.setattr(core.socket, 'create_connection', lambda *a, **k: Socket())
    def factory(**kwargs):
        return real_client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(core.httpx, 'Client', factory)


def test_captive_portal_is_not_internet(monkeypatch):
    mock_clients(monkeypatch, lambda request: httpx.Response(200, text='Sign in'))
    result = core.test_proxy('127.0.0.1', '127.0.0.1/32', core.Options())
    assert not result.working
    assert result.google == 'Ответ 200'
    assert result.example == 'Ответ 200'


def test_verified_targets_required(monkeypatch):
    def handler(request):
        return httpx.Response(204) if request.url.host == 'www.google.com' else httpx.Response(200, text='Example Domain')
    mock_clients(monkeypatch, handler)
    assert core.test_proxy('127.0.0.1', '127.0.0.1/32', core.Options()).working


def test_auth_only_after_challenge(monkeypatch):
    real_client = httpx.Client
    proxies = []
    class Socket:
        def __enter__(self): return self
        def __exit__(self, *args): pass
    monkeypatch.setattr(core.socket, 'create_connection', lambda *a, **k: Socket())
    count = 0
    def handler(request):
        nonlocal count
        count += 1
        if count <= 2:
            return httpx.Response(407, headers={'Proxy-Authenticate': 'Basic realm="lab"'})
        raise AssertionError('Must stop after rejected auth')
    def factory(**kwargs):
        proxies.append(kwargs['proxy'])
        assert kwargs['trust_env'] is False
        assert kwargs['follow_redirects'] is False
        return real_client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(core.httpx, 'Client', factory)
    options = core.Options(username='test-user', password='test-password')
    result = core.test_proxy('127.0.0.1', '127.0.0.1/32', options)
    assert isinstance(proxies[0], str)
    assert proxies[1].auth == ('test-user', 'test-password')
    assert result.auth == 'Не принята'
    assert 'test-password' not in repr(result)
    assert 'test-password' not in repr(options)


def test_priority_dedup_and_limit(monkeypatch):
    checked = []
    def probe(ip, subnet, options, stop):
        checked.append(ip)
        return core.Result(ip, subnet, 'OK', google='OK', example='OK')
    monkeypatch.setattr(core, 'test_proxy', probe)
    results = []
    scanner = core.Scanner(core.Options(concurrency=1, limit=2))
    reason = scanner.run(['10.0.2.1/32', '10.0.2.1/32', '10.0.1.0/30'], results.append, lambda *a: None)
    assert reason == 'Достигнут лимит'
    assert checked == ['10.0.2.1', '10.0.1.1']
    assert len(results) == 2


def test_stop_before_scan(monkeypatch):
    scanner = core.Scanner(core.Options())
    scanner.stop.set()
    assert scanner.run(['10.0.0.0/24'], lambda r: pytest.fail('unexpected probe'), lambda *a: None) == 'Остановлено'


def test_scope_guard():
    scanner = core.Scanner(core.Options())
    with pytest.raises(ValueError): scanner.run(['10.0.0.0/8'], lambda *a: None, lambda *a: None)
