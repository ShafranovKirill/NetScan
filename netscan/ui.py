from __future__ import annotations
import csv
import os
import sys
from dataclasses import asdict
from pathlib import Path
from PySide6.QtCore import Qt, QSettings, QThread, Signal, QTimer
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QLineEdit, QListWidget, QAbstractItemView, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QHBoxLayout, QFormLayout, QSpinBox, QDoubleSpinBox, QSplitter,
    QGroupBox, QFileDialog, QMessageBox, QProgressBar, QHeaderView, QCheckBox)
from netscan.core import Options, Scanner, Result, normalize_networks, host_count, MAX_HOSTS


class Worker(QThread):
    result = Signal(object)
    progress = Signal(int, int, str)
    summary = Signal(str)

    def __init__(self, scanner, networks):
        super().__init__()
        self.scanner, self.networks = scanner, networks

    def run(self):
        try:
            message = self.scanner.run(self.networks, self.result.emit, self.progress.emit)
        except Exception:
            message = 'Ошибка проверки. Проверьте параметры и повторите запуск.'
        finally:
            self.scanner.options.username = ''
            self.scanner.options.password = ''
        self.summary.emit(message)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('NetScan • Поиск прокси')
        self.resize(1240, 820)
        self.settings = QSettings('NetScan', 'NetScan')
        self.worker = None
        self.results = []
        self.last_summary = ''
        icon_root = Path(getattr(sys, '_MEIPASS', Path(__file__).parent.parent / 'packaging'))
        self.setWindowIcon(QIcon(str(icon_root / 'netscan.svg')))
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 20, 24, 20)
        title = QLabel('NetScan')
        title.setObjectName('title')
        layout.addWidget(title)
        caption = QLabel('Найдите прокси. Проверьте интернет. Сохраните рабочие адреса.')
        caption.setObjectName('caption')
        layout.addWidget(caption)
        split = QSplitter()
        layout.addWidget(split, 1)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 12, 12, 0)
        self.config = QGroupBox('01   Подсети и порядок проверки')
        ll.addWidget(self.config, 1)
        box = QVBoxLayout(self.config)
        self.input = QLineEdit()
        self.input.setPlaceholderText('Например: 10.133.51.0/24 или один IP')
        self.input.returnPressed.connect(self.add_input)
        box.addWidget(self.input)
        row = QHBoxLayout()
        row.addWidget(self.button('Добавить', self.add_input))
        row.addWidget(self.button('Импорт .txt', self.import_networks))
        box.addLayout(row)
        self.networks = QListWidget()
        self.networks.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.networks.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        box.addWidget(self.networks, 1)
        saved = self.settings.value('networks', [])
        if isinstance(saved, str):
            saved = [saved]
        for network in saved or []:
            self.networks.addItem(network)
        row = QHBoxLayout()
        row.addWidget(self.button('↑ Выше', lambda: self.move(-1)))
        row.addWidget(self.button('↓ Ниже', lambda: self.move(1)))
        row.addWidget(self.button('Удалить', self.remove))
        box.addLayout(row)
        help_label = QLabel('Сверху — первый приоритет. Перетаскивайте строки.\nСледующая подсеть начнётся после текущей.')
        help_label.setWordWrap(True)
        box.addWidget(help_label)
        self.params = QGroupBox('02   Параметры поиска')
        ll.addWidget(self.params)
        form = QFormLayout(self.params)
        self.port = QSpinBox(); self.port.setRange(1, 65535); self.port.setValue(3128)
        self.parallel = QSpinBox(); self.parallel.setRange(1, 64); self.parallel.setValue(12)
        self.timeout = QDoubleSpinBox(); self.timeout.setRange(.2, 5); self.timeout.setSingleStep(.2); self.timeout.setValue(.8); self.timeout.setSuffix(' с')
        self.limit = QSpinBox(); self.limit.setRange(0, 10000); self.limit.setSpecialValueText('Без ограничения')
        for label, field in [('TCP-порт', self.port), ('Одновременно', self.parallel), ('Ожидание порта', self.timeout), ('Найти рабочих и остановиться', self.limit)]:
            form.addRow(label, field)
        self.username = QLineEdit(); self.username.setPlaceholderText('Необязательно')
        self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow('Логин прокси', self.username)
        form.addRow('Пароль', self.password)
        note = QLabel('Данные отправляются только после запроса Basic-авторизации. Пароль не сохраняется. Для Basic используйте доверенные прокси.')
        note.setWordWrap(True)
        form.addRow(note)
        right = QWidget(); rl = QVBoxLayout(right); rl.setContentsMargins(10, 12, 0, 0)
        header = QHBoxLayout()
        self.count = QLabel('03   Результаты • 0 рабочих')
        header.addWidget(self.count, 1)
        self.only_working = QCheckBox('Только рабочие'); self.only_working.toggled.connect(self.filter_rows)
        header.addWidget(self.only_working)
        rl.addLayout(header)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(['Прокси', 'Результат', 'Google HTTPS', 'Example HTTPS', 'Авторизация', 'HTTP', 'Проверка, мс', 'Время'])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        rl.addWidget(self.table, 1)
        info = QLabel('Рабочий = Google вернул 204 и Example.com подтвердил страницу по HTTPS.\nПроверяются сертификаты TLS. Настройки системы и Throne не изменяются.')
        info.setWordWrap(True)
        rl.addWidget(info)
        actions = QHBoxLayout()
        actions.addWidget(self.button('Копировать адрес', self.copy_address))
        self.recheck = self.button('Перепроверить найденные', self.retest)
        actions.addWidget(self.recheck)
        actions.addWidget(self.button('Экспорт CSV', self.export))
        rl.addLayout(actions)
        split.addWidget(left); split.addWidget(right); split.setSizes([390, 820])
        self.state = QLabel('Готово • добавьте подсети для проверки')
        layout.addWidget(self.state)
        self.progress = QProgressBar(); self.progress.setRange(0, 100); self.progress.setValue(0)
        layout.addWidget(self.progress)
        controls = QHBoxLayout()
        self.start = self.button('Начать поиск', self.start_scan); self.start.setObjectName('primary')
        self.pause = self.button('Пауза', self.toggle_pause); self.pause.setEnabled(False)
        self.stop = self.button('Остановить', self.stop_scan); self.stop.setEnabled(False)
        controls.addWidget(self.start); controls.addWidget(self.pause); controls.addWidget(self.stop); controls.addStretch()
        controls.addWidget(QLabel('NetScan 0.1.0'))
        layout.addLayout(controls)

    def button(self, text, callback):
        button = QPushButton(text); button.clicked.connect(callback); return button

    def error(self, text):
        QMessageBox.warning(self, 'NetScan', text)

    def add_text(self, text):
        try:
            names = normalize_networks(text)
            current = {self.networks.item(i).text() for i in range(self.networks.count())}
            for name in names:
                if name not in current:
                    self.networks.addItem(name); current.add(name)
            self.save()
        except ValueError as exc:
            self.error(str(exc))

    def add_input(self):
        self.add_text(self.input.text()); self.input.clear()

    def import_networks(self):
        name, _ = QFileDialog.getOpenFileName(self, 'Импорт подсетей', '', 'Текст (*.txt);;Все файлы (*)')
        if name:
            try:
                self.add_text(Path(name).read_text(encoding='utf-8-sig'))
            except (OSError, UnicodeError):
                self.error('Не удалось прочитать файл UTF-8.')

    def move(self, delta):
        row = self.networks.currentRow(); target = row + delta
        if row >= 0 and 0 <= target < self.networks.count():
            item = self.networks.takeItem(row); self.networks.insertItem(target, item); self.networks.setCurrentRow(target); self.save()

    def remove(self):
        for item in self.networks.selectedItems():
            self.networks.takeItem(self.networks.row(item))
        self.save()

    def save(self):
        self.settings.setValue('networks', [self.networks.item(i).text() for i in range(self.networks.count())])

    def options(self):
        return Options(port=self.port.value(), concurrency=self.parallel.value(),
                       connect_timeout=self.timeout.value(), limit=self.limit.value(),
                       username=self.username.text(), password=self.password.text())

    def start_scan(self):
        self.launch([self.networks.item(i).text() for i in range(self.networks.count())])

    def launch(self, networks):
        if self.worker and self.worker.isRunning():
            return
        if not networks:
            self.error('Добавьте хотя бы одну подсеть или адрес.'); return
        if host_count(networks) > MAX_HOSTS:
            self.error(f'За один запуск — не более {MAX_HOSTS} адресов. Разделите список.'); return
        self.save()
        self.results = []; self.table.setRowCount(0); self.count.setText('03   Результаты • 0 рабочих')
        scanner = Scanner(self.options())
        self.worker = Worker(scanner, networks)
        self.worker.result.connect(self.add_result)
        self.worker.progress.connect(self.update_progress)
        self.worker.summary.connect(self.got_summary)
        self.worker.finished.connect(self.finished)
        self.config.setEnabled(False); self.params.setEnabled(False)
        self.start.setEnabled(False); self.recheck.setEnabled(False)
        self.pause.setEnabled(True); self.stop.setEnabled(True)
        self.progress.setValue(0); self.state.setText('Поиск запущен…')
        self.worker.start()

    def add_result(self, result):
        self.results.append(result)
        row = self.table.rowCount(); self.table.insertRow(row)
        values = [result.address, result.status, result.google, result.example, result.auth, result.http, str(result.elapsed_ms), result.checked]
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            if col == 1:
                item.setForeground(QColor('#5ee6b3' if result.working else '#f3c47a'))
            self.table.setItem(row, col, item)
        self.table.setRowHidden(row, self.only_working.isChecked() and not result.working)
        self.count.setText(f'03   Результаты • {sum(r.working for r in self.results)} рабочих / {len(self.results)} найдено')

    def filter_rows(self):
        for row, result in enumerate(self.results):
            self.table.setRowHidden(row, self.only_working.isChecked() and not result.working)

    def update_progress(self, done, total, network):
        self.progress.setValue(round(done / total * 100) if total else 0)
        mode = 'Пауза' if self.worker.scanner.paused.is_set() else 'Проверка'
        self.state.setText(f'{mode}: {network} • {done:,} / {total:,} адресов')

    def got_summary(self, message):
        self.last_summary = message

    def finished(self):
        self.config.setEnabled(True); self.params.setEnabled(True)
        self.start.setEnabled(True); self.recheck.setEnabled(True)
        self.pause.setEnabled(False); self.stop.setEnabled(False); self.pause.setText('Пауза')
        self.state.setText(f'{self.last_summary} • {sum(r.working for r in self.results)} рабочих прокси')
        if self.last_summary == 'Завершено':
            self.progress.setValue(100)

    def toggle_pause(self):
        scanner = self.worker.scanner
        if scanner.paused.is_set():
            scanner.paused.clear(); self.pause.setText('Пауза'); self.state.setText('Поиск продолжен…')
        else:
            scanner.paused.set(); self.pause.setText('Продолжить'); self.state.setText('Пауза • уже начатые проверки завершаются')

    def stop_scan(self):
        self.worker.scanner.stop.set(); self.state.setText('Остановка • ожидаем завершения текущих запросов…')
        self.stop.setEnabled(False)

    def retest(self):
        if not self.results:
            self.error('Пока нет найденных адресов.'); return
        self.launch(list(dict.fromkeys(r.address.split(':')[0] + '/32' for r in self.results)))

    def copy_address(self):
        row = self.table.currentRow()
        if row >= 0:
            QApplication.clipboard().setText(self.results[row].address)

    def export(self):
        selected = [r for r in self.results if r.working or not self.only_working.isChecked()]
        if not selected:
            self.error('Нет результатов для экспорта.'); return
        name, _ = QFileDialog.getSaveFileName(self, 'Экспорт результатов', 'netscan-results.csv', 'CSV (*.csv)')
        if not name: return
        try:
            with open(name, 'w', encoding='utf-8-sig', newline='') as out:
                writer = csv.DictWriter(out, fieldnames=list(asdict(selected[0])))
                writer.writeheader()
                for result in selected:
                    writer.writerow(asdict(result))
        except OSError:
            self.error('Не удалось сохранить файл.')

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.stop_scan(); event.ignore()
            self.state.setText('Останавливаем поиск. Закройте окно после завершения проверок.')
        else:
            self.password.clear(); self.save(); event.accept()


STYLE = '''
QWidget { background: #101923; color: #e4edf6; font-family: "Segoe UI", "Noto Sans", sans-serif; font-size: 13px; }
QLabel#title { font-size: 32px; font-weight: 700; color: #65dfc6; }
QLabel#caption { color: #a1b4c7; padding-bottom: 8px; }
QGroupBox { border: 1px solid #304253; border-radius: 10px; margin-top: 14px; padding: 16px 10px 10px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; }
QLineEdit, QSpinBox, QDoubleSpinBox, QListWidget { background: #172534; border: 1px solid #34495c; border-radius: 6px; padding: 7px; selection-background-color: #286b69; }
QPushButton { background: #223648; border: 1px solid #3a5268; border-radius: 6px; padding: 9px 12px; }
QPushButton:hover { background: #2c465d; }
QPushButton:disabled { color: #6b7e8e; border-color: #263747; }
QPushButton#primary { background: #45cdb3; color: #082b28; font-weight: 700; padding: 11px 28px; }
QTableWidget { background: #12202d; alternate-background-color: #192a39; gridline-color: #293d4e; border: 1px solid #304253; border-radius: 7px; }
QHeaderView::section { background: #23384a; border: none; padding: 9px; font-weight: 600; }
QProgressBar { background: #1c3040; border: none; border-radius: 5px; text-align: center; min-height: 18px; }
QProgressBar::chunk { background: #268c83; border-radius: 5px; }
QListWidget::item { padding: 7px; }
QListWidget::item:selected { background: #286b69; }
'''


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    window = Window(); window.show()
    if os.environ.get('NETSCAN_SMOKE_TEST') == '1':
        QTimer.singleShot(200, app.quit)
    code = app.exec()
    # Dispose Qt ownership cycles before QApplication teardown.
    import shiboken6
    shiboken6.delete(window)
    sys.exit(code)
