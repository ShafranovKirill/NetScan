import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from netscan.core import Result
from netscan.ui import Window

APP = QApplication.instance() or QApplication([])


def test_queue_order_results_and_filter(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = Window()
    window.settings = QSettings(str(tmp_path / 'test.ini'), QSettings.Format.IniFormat)
    window.networks.clear()
    window.add_text('10.0.1.1/24\n10.0.2.1/24')
    window.networks.setCurrentRow(1); window.move(-1)
    assert window.networks.item(0).text() == '10.0.2.0/24'
    window.add_result(Result('10.0.2.1:3128', '10.0.2.0/24', 'OK', google='OK', example='OK'))
    window.add_result(Result('10.0.2.2:3128', '10.0.2.0/24', 'Нужна авторизация'))
    window.only_working.setChecked(True)
    assert not window.table.isRowHidden(0)
    assert window.table.isRowHidden(1)
    window.table.selectRow(0); window.copy_address()
    assert app.clipboard().text() == '10.0.2.1:3128'
    window.password.setText('temporary-secret'); window.save()
    window.settings.sync()
    assert 'temporary-secret' not in (tmp_path / 'test.ini').read_text()
    window.close()
    import shiboken6
    shiboken6.delete(window)
    app.processEvents()
