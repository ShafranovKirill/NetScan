"""Local default credentials in the operating system's password vault only."""
import json
import sys

SERVICE = 'NetScan'
ACCOUNT = 'default-proxy'


def _vault():
    if sys.platform == 'win32':
        from keyring.backends.Windows import WinVaultKeyring
        return WinVaultKeyring()
    if sys.platform.startswith('linux'):
        from keyring.backends.SecretService import Keyring
        return Keyring()
    raise RuntimeError('Хранилище паролей этой ОС пока не поддерживается.')


def load_credentials() -> tuple[str, str]:
    try:
        value = _vault().get_password(SERVICE, ACCOUNT)
        if not value:
            return '', ''
        data = json.loads(value)
        username, password = data['username'], data['password']
        if not isinstance(username, str) or not isinstance(password, str):
            return '', ''
        return username, password
    except Exception:
        return '', ''


def save_credentials(username: str, password: str) -> None:
    try:
        _vault().set_password(SERVICE, ACCOUNT, json.dumps({'username': username, 'password': password}))
    except Exception:
        raise RuntimeError('Хранилище паролей недоступно. Разблокируйте его и повторите попытку. Данные не сохранены.') from None
