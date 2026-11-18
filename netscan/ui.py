from __future__ import annotations
import csv
import os
import ipaddress
import sys
from dataclasses import asdict
from pathlib import Path
from PySide6.QtCore import Qt, QSettings, QThread, Signal, QTimer, QRegularExpression
from PySide6.QtGui import QColor, QIcon, QPixmap, QRegularExpressionValidator, QPalette
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QLineEdit, QListWidget, QAbstractItemView, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QHBoxLayout, QFormLayout, QSpinBox, QDoubleSpinBox, QSplitter,
    QGroupBox, QFileDialog, QMessageBox, QProgressBar, QHeaderView, QCheckBox, QStackedWidget, QFrame)
from netscan.core import Options, Scanner, Result, normalize_networks, host_count, MAX_HOSTS
from netscan import __version__
from netscan.preferences import load_credentials, save_credentials


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
    def __init__(self, settings=None):
        super().__init__()
        self.setWindowTitle('NetScan')
        self.resize(1180, 760)
        self.setMinimumSize(1000, 680)
        self.settings = settings if settings is not None else QSettings('NetScan', 'NetScan')
        self.worker = None
        self.results = []
        self.last_summary = ''
        icon_root = Path(getattr(sys, '_MEIPASS', Path(__file__).parent.parent / 'packaging'))
        self.setWindowIcon(QIcon(str(icon_root / 'netscan.png')))
        root = QWidget(); self.setCentralWidget(root)
        shell = QHBoxLayout(root); shell.setContentsMargins(0, 0, 0, 0); shell.setSpacing(0)
        sidebar = QFrame(); sidebar.setObjectName('sidebar'); sidebar.setFixedWidth(200)
        side = QVBoxLayout(sidebar); side.setContentsMargins(16, 24, 16, 18); side.setSpacing(16)
        brand_row = QHBoxLayout(); brand_row.setSpacing(10)
        logo = QLabel(); logo.setFixedSize(44, 44)
        logo.setPixmap(QPixmap(str(icon_root / 'netscan.png')).scaled(44, 44, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        brand_row.addWidget(logo)
        brand = QLabel('NetScan'); brand.setObjectName('brand'); brand.setStyleSheet('font-size: 22px;'); brand_row.addWidget(brand)
        brand_row.addStretch(); side.addLayout(brand_row)
        self.nav = QListWidget(); self.nav.setObjectName('navigation')
        self.nav.addItems(['Сканирование', 'Подсети', 'Параметры'])
        self.nav.setFixedHeight(150); side.addWidget(self.nav)
        side.addStretch()
        self.queue_summary = QLabel(); self.queue_summary.setObjectName('muted'); self.queue_summary.setWordWrap(True)
        side.addWidget(self.queue_summary)
        version = QLabel(f'Версия {__version__}'); version.setObjectName('muted'); side.addWidget(version)
        shell.addWidget(sidebar)
        content = QWidget(); content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(28, 24, 28, 22); content_layout.setSpacing(16)
        self.pages = QStackedWidget(); content_layout.addWidget(self.pages, 1)
        shell.addWidget(content, 1)

        scan_page = QWidget(); scan = QVBoxLayout(scan_page); scan.setContentsMargins(0, 0, 0, 0); scan.setSpacing(16)
        scan.addWidget(self.heading('Сканирование'))
        top = QHBoxLayout()
        self.count = QLabel('0 рабочих · 0 найдено'); self.count.setObjectName('counter')
        top.addWidget(self.count, 1)
        self.only_working = QCheckBox('Только рабочие'); self.only_working.toggled.connect(self.filter_rows)
        top.addWidget(self.only_working); scan.addLayout(top)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(['Прокси', 'Состояние', 'Google', 'Example', 'Авторизация', 'HTTP', 'мс', 'Время'])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True); self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setToolTip('Рабочий прокси подтвердил доступ к Google и Example.com по HTTPS с проверкой сертификатов.')
        scan.addWidget(self.table, 1)
        self.empty = QLabel('Список пуст. Добавьте подсети и начните поиск.'); self.empty.setObjectName('muted'); scan.addWidget(self.empty)
        actions = QHBoxLayout()
        actions.addWidget(self.button('Копировать адрес', self.copy_address))
        self.recheck = self.button('Перепроверить', self.retest); actions.addWidget(self.recheck)
        actions.addStretch(); actions.addWidget(self.button('Экспорт CSV', self.export)); scan.addLayout(actions)
        self.pages.addWidget(scan_page)

        subnet_page = QWidget(); subnet = QVBoxLayout(subnet_page); subnet.setContentsMargins(0, 0, 0, 0); subnet.setSpacing(16)
        subnet.addWidget(self.heading('Подсети'))
        subtitle = QLabel('Верхние строки проверяются первыми. Перетаскивайте их, чтобы изменить порядок.'); subtitle.setObjectName('muted'); subtitle.setWordWrap(True); subnet.addWidget(subtitle)
        self.config = QWidget(); box = QVBoxLayout(self.config); box.setContentsMargins(0, 0, 0, 0); box.setSpacing(12)
        entry_labels = QHBoxLayout(); entry_labels.addWidget(QLabel('IPv4-адрес'), 1); mask_label = QLabel('Маска'); mask_label.setFixedWidth(90); entry_labels.addWidget(mask_label); entry_labels.addSpacing(192); box.addLayout(entry_labels)
        entry = QHBoxLayout()
        self.input = QLineEdit(); self.input.setPlaceholderText('192.168.1.0'); self.input.setMaxLength(15)
        octet = r'(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)'
        self.input.setValidator(QRegularExpressionValidator(QRegularExpression(rf'{octet}\.{octet}\.{octet}\.{octet}'), self.input))
        self.input.returnPressed.connect(self.add_input); entry.addWidget(self.input, 1)
        self.mask = QSpinBox(); self.mask.setRange(0, 32); self.mask.setValue(24); self.mask.setPrefix('/'); self.mask.setFixedWidth(90)
        self.mask.setToolTip('/24 — подсеть, /32 — один адрес'); entry.addWidget(self.mask)
        entry.addWidget(self.button('Один IP', lambda: self.mask.setValue(32)))
        entry.addWidget(self.button('Добавить', self.add_input)); box.addLayout(entry)
        self.input_hint = QLabel('Подсеть будет приведена к её сетевому адресу. Для одного устройства выберите /32.'); self.input_hint.setObjectName('muted'); self.input_hint.setWordWrap(True); box.addWidget(self.input_hint)
        self.networks = QListWidget(); self.networks.setObjectName('networks')
        self.networks.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.networks.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.networks.model().rowsMoved.connect(lambda *args: self.save())
        box.addWidget(self.networks, 1)
        saved = self.settings.value('networks', [])
        if isinstance(saved, str): saved = [saved]
        for network in saved or []: self.networks.addItem(network)
        row = QHBoxLayout()
        row.addWidget(self.button('↑ Выше', lambda: self.move(-1)))
        row.addWidget(self.button('↓ Ниже', lambda: self.move(1)))
        row.addWidget(self.button('Удалить', self.remove)); row.addStretch()
        row.addWidget(self.button('Импорт .txt', self.import_networks)); box.addLayout(row)
        subnet.addWidget(self.config, 1); self.pages.addWidget(subnet_page)

        params_page = QWidget(); params_layout = QVBoxLayout(params_page); params_layout.setContentsMargins(0, 0, 0, 0); params_layout.setSpacing(20)
        params_layout.addWidget(self.heading('Параметры'))
        self.params = QWidget(); form = QFormLayout(self.params); form.setContentsMargins(0, 0, 0, 0); form.setHorizontalSpacing(28); form.setVerticalSpacing(14)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.port = QSpinBox(); self.port.setRange(1, 65535); self.port.setValue(3128)
        self.parallel = QSpinBox(); self.parallel.setRange(1, 64); self.parallel.setValue(12)
        self.timeout = QDoubleSpinBox(); self.timeout.setRange(.2, 5); self.timeout.setSingleStep(.2); self.timeout.setValue(.8); self.timeout.setSuffix(' с')
        self.limit = QSpinBox(); self.limit.setRange(0, 10000); self.limit.setSpecialValueText('Без ограничения')
        for label, field in [('Порт прокси', self.port), ('Одновременных проверок', self.parallel), ('Ожидание ответа порта', self.timeout), ('Остановиться после рабочих', self.limit)]:
            field.setMaximumWidth(310); form.addRow(label, field)
        self.username = QLineEdit(); self.username.setPlaceholderText('Логин сети')
        self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.EchoMode.Password); self.password.setPlaceholderText('Пароль сети')
        try:
            username, password = ('', '') if os.environ.get('NETSCAN_NO_CREDENTIALS') == '1' else load_credentials()
            self.username.setText(username); self.password.setText(password)
        except RuntimeError:
            pass
        for label, field in [('Логин', self.username), ('Пароль', self.password)]:
            field.setMaximumWidth(310); form.addRow(label, field)
        self.remember = QCheckBox('Запомнить в хранилище паролей'); form.addRow('', self.remember)
        show_password = QCheckBox('Показать пароль')
        show_password.toggled.connect(lambda shown: self.password.setEchoMode(QLineEdit.EchoMode.Normal if shown else QLineEdit.EchoMode.Password)); form.addRow('', show_password)
        note = QLabel('Авторизация используется только по запросу прокси. Системные настройки сети не меняются.'); note.setObjectName('muted'); note.setWordWrap(True); form.addRow(note)
        params_layout.addWidget(self.params)
        params_layout.addStretch()
        params_layout.addWidget(self.button('Сохранить параметры', self.save_parameters), alignment=Qt.AlignmentFlag.AlignLeft)
        self.settings_notice = QLabel(''); self.settings_notice.setObjectName('muted'); params_layout.addWidget(self.settings_notice)
        self.pages.addWidget(params_page)

        self.state = QLabel('Готово'); self.state.setObjectName('muted'); content_layout.addWidget(self.state)
        self.progress = QProgressBar(); self.progress.setRange(0, 100); self.progress.setValue(0); self.progress.setFixedHeight(8); self.progress.setTextVisible(False); content_layout.addWidget(self.progress)
        controls = QHBoxLayout()
        self.start = self.button('Начать поиск', self.start_scan); self.start.setObjectName('primary')
        self.pause = self.button('Пауза', self.toggle_pause); self.pause.setEnabled(False)
        self.stop = self.button('Остановить', self.stop_scan); self.stop.setEnabled(False)
        controls.addWidget(self.start); controls.addWidget(self.pause); controls.addWidget(self.stop); controls.addStretch()
        content_layout.addLayout(controls)
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex); self.nav.setCurrentRow(0)
        for name, field in [('port', self.port), ('parallel', self.parallel), ('timeout', self.timeout), ('limit', self.limit), ('mask', self.mask)]:
            value = self.settings.value(name)
            if value is not None:
                try: field.setValue(float(value) if name == 'timeout' else int(value))
                except (TypeError, ValueError): pass
        self.refresh_queue()

    def heading(self, text):
        label = QLabel(text); label.setObjectName('heading'); return label

    def refresh_queue(self):
        number = self.networks.count()
        self.queue_summary.setText(f'В очереди: {number} подсетей\nПорт {self.port.value()}')
        self.empty.setText('Список пуст. Добавьте подсети и начните поиск.' if not number else 'Результаты появятся после начала поиска.')

    def save_parameters(self):
        if self.remember.isChecked():
            try:
                save_credentials(self.username.text(), self.password.text())
            except RuntimeError as exc:
                self.error(str(exc)); return
        self.save()
        self.settings_notice.setText('Параметры сохранены.' + (' Учётные данные — в хранилище паролей.' if self.remember.isChecked() else ' Пароль не записан в настройки.'))

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
        address = self.input.text().strip()
        if not self.input.hasAcceptableInput():
            self.input_hint.setText('Введите IPv4-адрес из четырёх чисел от 0 до 255.')
            self.input.setProperty('invalid', True); self.input.style().unpolish(self.input); self.input.style().polish(self.input)
            self.input.setFocus(); return
        try:
            ipaddress.IPv4Address(address)
        except ValueError:
            self.input_hint.setText('Неверный IPv4-адрес. Проверьте каждое число.'); return
        self.add_text(f'{address}/{self.mask.value()}')
        self.input.clear(); self.input.setProperty('invalid', False); self.input.style().unpolish(self.input); self.input.style().polish(self.input)
        self.input_hint.setText('Адрес добавлен. Верхние строки проверяются первыми.')

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
        for name, field in [('port', self.port), ('parallel', self.parallel), ('timeout', self.timeout), ('limit', self.limit), ('mask', self.mask)]:
            self.settings.setValue(name, field.value())
        self.refresh_queue()

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
            self.nav.setCurrentRow(1); self.input.setFocus(); self.state.setText('Добавьте хотя бы одну подсеть или адрес.'); return
        if host_count(networks) > MAX_HOSTS:
            self.error(f'За один запуск — не более {MAX_HOSTS} адресов. Разделите список.'); return
        if self.remember.isChecked():
            try: save_credentials(self.username.text(), self.password.text())
            except RuntimeError as exc:
                self.error(str(exc)); return
        self.save()
        self.results = []; self.table.setRowCount(0); self.count.setText('0 рабочих · 0 найдено')
        self.empty.hide(); self.nav.setCurrentRow(0)
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
        self.count.setText(f'{sum(r.working for r in self.results)} рабочих · {len(self.results)} найдено')
        self.empty.hide()

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
QWidget { background: #111821; color: #e4eaf1; font-family: "Segoe UI", "Noto Sans", sans-serif; font-size: 13px; }
QFrame#sidebar { background: #0b1118; border-right: 1px solid #223040; }
QLabel#brand { background: transparent; color: #e8f5f2; font-size: 25px; font-weight: 700; padding: 0 10px 18px; }
QLabel#heading { font-size: 25px; font-weight: 600; padding-bottom: 4px; }
QLabel#muted { color: #8999ac; background: transparent; }
QLabel#counter { color: #b5c3d1; font-size: 14px; }
QListWidget#navigation { background: transparent; border: none; outline: none; }
QListWidget#navigation::item { padding: 12px 14px; margin: 3px 0; border-radius: 7px; color: #9caec0; }
QListWidget#navigation::item:selected { background: #183830; color: #81e3bd; }
QListWidget#navigation::item:hover { background: #172331; }
QLineEdit, QSpinBox, QDoubleSpinBox { background: #192430; border: 1px solid #344456; border-radius: 6px; padding: 9px; selection-background-color: #285f51; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border-color: #62cfa7; }
QLineEdit[invalid="true"] { border-color: #e5a277; }
QPushButton { background: #1c2a38; border: 1px solid #344658; border-radius: 6px; padding: 10px 14px; }
QPushButton:hover { background: #293c4e; }
QPushButton:disabled { color: #607183; border-color: #283746; }
QPushButton#primary { background: #6cd6af; border-color: #6cd6af; color: #092b20; font-weight: 700; padding: 11px 24px; }
QPushButton#primary:hover { background: #90e7c5; }
QPushButton#primary:disabled { background: #244c40; border-color: #244c40; color: #708e82; }
QTableWidget { background: #131e29; alternate-background-color: #172431; gridline-color: #263646; border: 1px solid #293a4b; border-radius: 7px; }
QHeaderView::section { background: #1d2b3a; border: none; color: #a9bacb; padding: 10px 8px; font-weight: 600; }
QTableWidget::item { padding: 8px 6px; }
QTableWidget::item:selected { background: #245445; color: white; }
QProgressBar { background: #22313f; border: none; border-radius: 4px; }
QProgressBar::chunk { background: #6cd6af; border-radius: 4px; }
QListWidget#networks { background: #131e29; border: 1px solid #293a4b; border-radius: 7px; outline: none; }
QListWidget#networks::item { padding: 13px; border-bottom: 1px solid #223141; }
QListWidget#networks::item:selected { background: #245445; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #52677c; border-radius: 3px; background: #182430; }
QCheckBox::indicator:checked { background: #6cd6af; border-color: #6cd6af; }
QToolTip { background: #223345; border: 1px solid #43576c; color: #e4edf6; }
'''



def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    palette = app.palette()
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        palette.setColor(role, QColor('#e4eaf1'))
    palette.setColor(QPalette.ColorRole.Base, QColor('#192430'))
    palette.setColor(QPalette.ColorRole.Button, QColor('#1c2a38'))
    palette.setColor(QPalette.ColorRole.Highlight, QColor('#245445'))
    app.setPalette(palette)
    app.setStyleSheet(STYLE)
    window = Window(); window.show()
    if os.environ.get('NETSCAN_SMOKE_TEST') == '1':
        QTimer.singleShot(200, app.quit)
    code = app.exec()
    # Dispose Qt ownership cycles before QApplication teardown.
    import shiboken6
    shiboken6.delete(window)
    sys.exit(code)
