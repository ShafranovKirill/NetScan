import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from PySide6.QtCore import QSettings, QItemSelectionModel
from PySide6.QtWidgets import QApplication
from netscan.core import Result
from netscan import ui

APP = QApplication.instance() or QApplication([])


@pytest.fixture
def window(tmp_path, monkeypatch):
    monkeypatch.setattr(ui, 'load_credentials', lambda: ('', ''))
    monkeypatch.setattr(ui, 'load_history', lambda: [])
    monkeypatch.setattr(ui, 'save_history', lambda results: None)
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
    env = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'NETSCAN_SMOKE_TEST': '1', 'NETSCAN_NO_CREDENTIALS': '1', 'NETSCAN_NO_HISTORY': '1'}
    process = subprocess.run([sys.executable, '-m', 'netscan'], env=env, timeout=15, capture_output=True)
    assert process.returncode == 0, process.stderr.decode(errors='replace')


def add_working(window, address, auth='Не требуется'):
    window.add_result(Result(address, '192.168.1.0/24', 'Интернет проверен', google='OK', example='OK', auth=auth))


def test_share_selected_working_and_encode_credentials(window):
    add_working(window, '192.168.1.10:3128', auth='Принята')
    add_working(window, '192.168.1.11:3128')
    window.add_result(Result('192.168.1.12:3128', '192.168.1.0/24', 'Нужна авторизация'))
    window.username.setText('test@user'); window.password.setText('test:pass')
    window.table.selectRow(0)
    window.copy_links()
    text = APP.clipboard().text()
    import base64,json
    profile=json.loads(base64.urlsafe_b64decode(text.split('/',3)[3]))
    assert profile['server']=='192.168.1.10' and profile['username']=='test@user' and profile['password']=='test:pass'
    window.copy_links(native=False)
    assert 'test%40user:test%3Apass@192.168.1.10:3128' in APP.clipboard().text()
    window.include_credentials.setChecked(False); window.copy_links()
    profile=json.loads(base64.urlsafe_b64decode(APP.clipboard().text().split('/',3)[3]))
    assert 'username' not in profile and 'password' not in profile
    assert profile['server']=='192.168.1.10'
    window.table.selectRow(2)
    APP.clipboard().setText('unchanged'); window.copy_links()
    assert APP.clipboard().text() == 'unchanged'


def test_copy_all_working_and_multi_selection(window):
    add_working(window, '192.168.1.10:3128')
    add_working(window, '192.168.1.11:3128')
    window.add_result(Result('192.168.1.12:3128', '192.168.1.0/24', 'Нужна авторизация'))
    window.copy_address()
    assert APP.clipboard().text().splitlines() == ['192.168.1.10:3128', '192.168.1.11:3128']
    window.table.selectRow(0)
    window.table.selectionModel().select(window.table.model().index(1,0), QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
    window.copy_links()
    assert len(APP.clipboard().text().splitlines()) == 2
    assert '192.168.1.12' not in APP.clipboard().text()


def test_links_file_and_csv_selected(window, monkeypatch, tmp_path):
    add_working(window, '192.168.1.10:3128')
    add_working(window, '192.168.1.11:3128')
    window.table.selectRow(1)
    target = tmp_path / 'links.txt'
    monkeypatch.setattr(ui.QFileDialog, 'getSaveFileName', lambda *args: (str(target), ''))
    window.export_links()
    import base64,json
    profile=json.loads(base64.urlsafe_b64decode(target.read_text().strip().split('/',3)[3]))
    assert profile['server']=='192.168.1.11' and profile['server_port']==3128
    target = tmp_path / 'table.csv'
    window.export()
    assert '192.168.1.11:3128' in target.read_text(encoding='utf-8-sig')
    assert '192.168.1.10:3128' not in target.read_text(encoding='utf-8-sig')


def test_saved_results_load_and_clear(tmp_path, monkeypatch):
    result = Result('192.168.1.10:3128', '192.168.1.0/24', 'Интернет проверен', google='OK', example='OK')
    monkeypatch.setattr(ui, 'load_credentials', lambda: ('', ''))
    monkeypatch.setattr(ui, 'load_history', lambda: [result])
    saved = []
    monkeypatch.setattr(ui, 'save_history', lambda results: saved.append(list(results)))
    w = ui.Window(settings=QSettings(str(tmp_path / 'history.ini'), QSettings.Format.IniFormat))
    try:
        assert w.results == [result]
        assert 'Сохранённые' in w.state.text()
        w.clear_results()
        assert w.results == [] and saved == [[]]
    finally:
        w.close()
        import shiboken6
        shiboken6.delete(w)


def test_hidden_selection_falls_back_to_visible_working(window):
    add_working(window, '192.168.1.10:3128')
    window.add_result(Result('192.168.1.12:3128', '192.168.1.0/24', 'Нужна авторизация'))
    window.table.selectRow(1)
    window.only_working.setChecked(True)
    window.copy_address()
    assert APP.clipboard().text() == '192.168.1.10:3128'


def test_bad_result_link_reports_status(window, monkeypatch):
    add_working(window, '192.168.1.10:3128')
    def invalid(*args, **kwargs): raise ValueError('bad saved address')
    monkeypatch.setattr(ui, 'make_throne_links', invalid)
    APP.clipboard().setText('unchanged')
    window.copy_links()
    assert APP.clipboard().text() == 'unchanged'
    assert 'Перепроверьте' in window.state.text()
