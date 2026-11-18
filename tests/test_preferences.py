import json
import pytest
from netscan import preferences


class Vault:
    value = None
    def get_password(self, service, account): return self.value
    def set_password(self, service, account, value): self.value = value


def test_local_vault_roundtrip(monkeypatch):
    vault = Vault()
    monkeypatch.setattr(preferences, '_vault', lambda: vault)
    assert preferences.load_credentials() == ('', '')
    preferences.save_credentials('test', 'temporary-value')
    assert preferences.load_credentials() == ('test', 'temporary-value')
    assert json.loads(vault.value)['username'] == 'test'


def test_unavailable_vault_does_not_leak_errors(monkeypatch):
    def unavailable(): raise Exception('sensitive-backend-details')
    monkeypatch.setattr(preferences, '_vault', unavailable)
    assert preferences.load_credentials() == ('', '')
    with pytest.raises(RuntimeError) as error:
        preferences.save_credentials('test', 'temporary-value')
    assert 'sensitive-backend-details' not in str(error.value)
    assert 'temporary-value' not in str(error.value)


def test_invalid_vault_data(monkeypatch):
    vault = Vault(); vault.value = '{"username":42,"password":[]}'
    monkeypatch.setattr(preferences, '_vault', lambda: vault)
    assert preferences.load_credentials() == ('', '')
