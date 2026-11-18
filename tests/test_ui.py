import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from netscan.core import Result
from netscan import ui

APP = QApplication.instance() or QApplication([])


@pytest.fixture
def window(tmp_path, monkeypatch):
    monkeypatch.setattr(ui, 'load_credentials', lambda: ('', ''))
    settings = QSettings(str(tmp_path / 'test.ini'), QSettings.Format.IniFormat)
    window = ui.Window(settings=settings)
    yield window
    window.close()
    import shiboken6
    shiboken6.delete(window)
    APP.processEvents()


def test_queue_order_results_and_filter(window, tmp_path):
    window.add_text('10.0.1.1/24\n10.0.2.1/24')
    window.networks.setCurrentRow(1); window.move(-1)
    assert window.networks.item(0).text() == '10.0.2.0/24'
    window.add_result(Result('10.0.2.1:3128', '10.0.2.0/24', 'OK', google='OK', example='OK'))
    window.add_result(Result('10.0.2.2:3128', '10.0.2.0/24', 'Нужна авторизация'))
    window.only_working.setChecked(True)
    assert not window.table.isRowHidden(0)
    assert window.table.isRowHidden(1)
    window.table.selectRow(0); window.copy_address()
    assert APP.clipboard().text() == '10.0.2.1:3128'
    window.password.setText('temporary-secret'); window.save()
    window.settings.sync()
    assert 'temporary-secret' not in (tmp_path / 'test.ini').read_text()


def test_mask_and_ipv4_validation(window):
    assert window.mask.value() == 24
    assert window.port.value() == 3128
    window.mask.setValue(25); window.save()
    assert window.settings.value('mask') == 25
    window.mask.setValue(24)
    window.input.setText('192.168.10.17'); window.add_input()
    assert window.networks.item(0).text() == '192.168.10.0/24'
    window.mask.setValue(32)
    window.input.setText('192.168.10.17'); window.add_input()
    assert window.networks.item(1).text() == '192.168.10.17/32'
    for invalid in ['256.0.0.1', '192.168', '192.168.1.1/24', '01.2.3.4']:
        window.input.setText(invalid); window.add_input()
        assert window.networks.count() == 2
        assert 'четырёх' in window.input_hint.text() or 'Неверный' in window.input_hint.text()


def test_sidebar_and_empty_start(window):
    assert window.pages.currentIndex() == 0
    window.nav.setCurrentRow(2)
    assert window.pages.currentIndex() == 2
    window.start_scan()
    assert window.pages.currentIndex() == 1
    assert window.worker is None


def test_credentials_only_saved_on_explicit_choice(window, monkeypatch):
    saved = []
    monkeypatch.setattr(ui, 'save_credentials', lambda user, password: saved.append((user, password)))
    window.username.setText('test-user'); window.password.setText('test-password')
    window.save_parameters()
    assert not saved
    window.remember.setChecked(True); window.save_parameters()
    assert saved == [('test-user', 'test-password')]


def test_gui_process_exits_cleanly():
    import subprocess
    import sys
    env = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'NETSCAN_SMOKE_TEST': '1', 'NETSCAN_NO_CREDENTIALS': '1'}
    process = subprocess.run([sys.executable, '-m', 'netscan'], env=env, timeout=15, capture_output=True)
    assert process.returncode == 0, process.stderr.decode(errors='replace')
