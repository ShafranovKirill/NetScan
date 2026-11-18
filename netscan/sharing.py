"""Standard HTTP share links, compatible with Qt/QUrl-based clients."""
import ipaddress
from urllib.parse import quote
from netscan.core import Result


def make_links(results: list[Result], username: str = '', password: str = '') -> str:
    links = []
    seen = set()
    for result in results:
        if not result.working or result.address in seen:
            continue
        host, port = result.address.rsplit(':', 1)
        ipaddress.IPv4Address(host)
        if not 1 <= int(port) <= 65535:
            raise ValueError('Некорректный порт прокси.')
        auth = ''
        if result.auth == 'Принята' and username:
            auth = quote(username, safe='') + ':' + quote(password, safe='') + '@'
        name = quote('NetScan ' + result.address, safe='')
        links.append(f'http://{auth}{host}:{port}#{name}')
        seen.add(result.address)
    return '\n'.join(links)


def write_links(path, text: str) -> None:
    """Private atomic file export, including when replacing an existing file."""
    import os
    import tempfile
    from pathlib import Path
    destination = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=destination.parent, delete=False) as out:
            temporary = out.name
            os.chmod(temporary, 0o600)
            out.write(text + '\n')
        os.replace(temporary, destination)
    finally:
        if temporary and os.path.exists(temporary): os.unlink(temporary)


def make_throne_links(results: list[Result], username: str = '', password: str = '') -> str:
    """Throne native sing-box outbound profiles, one deep link per row."""
    import base64
    import json
    links = []
    seen = set()
    for result in results:
        if not result.working or result.address in seen:
            continue
        host, port = result.address.rsplit(':', 1)
        ipaddress.IPv4Address(host)
        if not 1 <= int(port) <= 65535:
            raise ValueError('Некорректный порт прокси.')
        profile = {'type':'http', 'server':host, 'server_port':int(port), 'tag':'NetScan ' + result.address}
        if username:
            profile.update(username=username, password=password)
        payload = base64.urlsafe_b64encode(json.dumps(profile,ensure_ascii=True,separators=(',',':')).encode()).decode()
        links.append('throne://add/' + payload)
        seen.add(result.address)
    return '\n'.join(links)
