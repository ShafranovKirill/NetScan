"""Bounded proxy discovery. Never changes system networking or persists credentials."""
from __future__ import annotations
import ipaddress
import socket
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from typing import Callable
import httpx

MAX_HOSTS = 65536


def normalize_networks(text: str) -> list[str]:
    result = []
    for token in text.replace(',', '\n').replace(';', '\n').split():
        net = ipaddress.ip_network(token, strict=False)
        if net.version != 4:
            raise ValueError('Поддерживаются только IPv4-подсети и адреса.')
        name = str(net)
        if name not in result:
            result.append(name)
    return result


def host_count(networks: list[str]) -> int:
    return sum(n.num_addresses if n.prefixlen >= 31 else n.num_addresses - 2
               for n in map(ipaddress.ip_network, networks))


@dataclass
class Result:
    address: str
    subnet: str
    status: str
    http: str = '—'
    google: str = '—'
    example: str = '—'
    auth: str = 'Не требуется'
    elapsed_ms: int = 0
    checked: str = field(default_factory=lambda: time.strftime('%H:%M:%S'))

    @property
    def working(self) -> bool:
        return self.google == 'OK' and self.example == 'OK'


@dataclass
class Options:
    port: int = 3128
    concurrency: int = 12
    connect_timeout: float = 0.8
    request_timeout: float = 5.0
    limit: int = 0
    username: str = field(default='', repr=False)
    password: str = field(default='', repr=False)


def failure(exc: Exception) -> str:
    # Never expose exception text: proxy URLs/headers may contain credentials.
    if isinstance(exc, httpx.TimeoutException):
        return 'Таймаут'
    if isinstance(exc, httpx.ProxyError):
        return 'Ошибка CONNECT / авторизации'
    if isinstance(exc, httpx.ConnectError):
        return 'Ошибка соединения / TLS'
    return 'Ошибка запроса'


def test_proxy(ip: str, subnet: str, options: Options,
               stop: threading.Event | None = None) -> Result | None:
    stop = stop or threading.Event()
    if stop.is_set():
        return None
    try:
        with socket.create_connection((ip, options.port), timeout=options.connect_timeout):
            pass
    except OSError:
        return None
    result = Result(f'{ip}:{options.port}', subnet, 'Порт открыт')
    start = time.monotonic()
    proxy_url = f'http://{ip}:{options.port}'
    timeout = httpx.Timeout(options.request_timeout)
    auth = None
    try:
        # Explicit proxy and trust_env=False prevent accidental environment bypass.
        with httpx.Client(proxy=proxy_url, trust_env=False, timeout=timeout,
                          follow_redirects=False) as client:
            with client.stream('GET', 'http://example.com/') as response:
                result.http = str(response.status_code)
                challenge = response.headers.get('proxy-authenticate', '')
                needs_auth = response.status_code == 407
        if needs_auth:
            result.auth = 'Требуется'
            if not options.username:
                result.status = 'Нужна авторизация'
                return result
            if not challenge.lower().startswith('basic'):
                result.auth = 'Неподдерживаемая схема'
                result.status = 'Нужна другая схема авторизации'
                return result
            auth = (options.username, options.password)
        if stop.is_set():
            result.status = 'Проверка остановлена'
            return result
        proxy = httpx.Proxy(proxy_url, auth=auth)
        with httpx.Client(proxy=proxy, trust_env=False, timeout=timeout,
                          follow_redirects=False) as client:
            if auth:
                with client.stream('GET', 'http://example.com/') as response:
                    result.http = str(response.status_code)
                    if response.status_code == 407:
                        result.auth = 'Не принята'
                        result.status = 'Авторизация не принята (407)'
                        return result
                result.auth = 'Принята'
            for name, url in [('google', 'https://www.google.com/generate_204'),
                              ('example', 'https://example.com/')]:
                if stop.is_set():
                    result.status = 'Проверка остановлена'
                    return result
                try:
                    with client.stream('GET', url) as response:
                        if name == 'google':
                            valid = response.status_code == 204
                        else:
                            body = bytearray()
                            deadline = time.monotonic() + options.request_timeout
                            for chunk in response.iter_bytes():
                                body.extend(chunk[:32768 - len(body)])
                                if stop.is_set() or time.monotonic() >= deadline or len(body) >= 32768:
                                    break
                            valid = response.status_code == 200 and b'Example Domain' in body
                        setattr(result, name, 'OK' if valid else f'Ответ {response.status_code}')
                except httpx.HTTPError as exc:
                    setattr(result, name, failure(exc))
        result.status = 'Интернет проверен' if result.working else 'Проверка не пройдена полностью'
    except (httpx.HTTPError, OSError) as exc:
        result.status = failure(exc)
    finally:
        result.elapsed_ms = round((time.monotonic() - start) * 1000)
    return result


class Scanner:
    def __init__(self, options: Options):
        self.options = options
        self.stop = threading.Event()
        self.paused = threading.Event()
        self.found = 0
        self.completed = 0

    def run(self, networks: list[str], on_result: Callable[[Result], None],
            on_progress: Callable[[int, int, str], None]) -> str:
        if not 1 <= self.options.concurrency <= 64:
            raise ValueError('Число проверок должно быть от 1 до 64.')
        if not 1 <= self.options.port <= 65535:
            raise ValueError('Некорректный порт.')
        if host_count(networks) > MAX_HOSTS:
            raise ValueError(f'За один запуск разрешено до {MAX_HOSTS} адресов.')
        total = host_count(networks)
        seen = set()
        with ThreadPoolExecutor(max_workers=self.options.concurrency) as pool:
            for network in networks:
                hosts = iter(ipaddress.ip_network(network).hosts())
                pending = {}
                exhausted = False
                while pending or not exhausted:
                    if self.stop.is_set():
                        for future in pending:
                            future.cancel()
                        return 'Достигнут лимит' if self.options.limit and self.found >= self.options.limit else 'Остановлено'
                    while not exhausted and not self.paused.is_set() and len(pending) < self.options.concurrency:
                        try:
                            ip = str(next(hosts))
                        except StopIteration:
                            exhausted = True
                            break
                        if ip in seen:
                            self.completed += 1
                            on_progress(self.completed, total, network)
                            continue
                        seen.add(ip)
                        f = pool.submit(test_proxy, ip, network, self.options, self.stop)
                        pending[f] = ip
                    if not pending:
                        self.stop.wait(0.1)
                        continue
                    ready, _ = wait(pending, timeout=0.1, return_when=FIRST_COMPLETED)
                    for future in ready:
                        pending.pop(future)
                        result = future.result()
                        self.completed += 1
                        if result is not None:
                            on_result(result)
                            if result.working:
                                self.found += 1
                        on_progress(self.completed, total, network)
                        if self.options.limit and self.found >= self.options.limit:
                            self.stop.set()
                            break
        return 'Достигнут лимит' if self.stop.is_set() and self.options.limit and self.found >= self.options.limit else 'Остановлено' if self.stop.is_set() else 'Завершено'
