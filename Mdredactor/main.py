import sys
import os
import shutil
import psutil
import time
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QSplitter,
    QAction, QFileDialog, QMessageBox, QToolBar, QLabel,
    QVBoxLayout, QWidget, QStatusBar, QLineEdit, QPushButton,
    QHBoxLayout, QSizePolicy, QComboBox, QFileSystemModel, QTreeView
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QFont
from PyQt5.QtWidgets import QSplashScreen
import markdown


def resource_path(relative_path: str) -> str:
    """
    Return absolute path to resource, works for dev and for PyInstaller.
    """
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


def get_disks():
    """Return list of disk devices (Windows and Unix-friendly)."""
    disks = []
    try:
        parts = psutil.disk_partitions(all=False)
        for p in parts:
            if 'cdrom' in p.opts:
                continue
            disks.append(p.device)
    except Exception:
        if os.name == 'nt':
            for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                drive = f"{letter}:/"
                if os.path.exists(drive):
                    disks.append(drive)
        else:
            disks = ['/']
    return disks or (['/'] if os.name != 'nt' else ['C:/'])


def human_size(num):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"


class FileManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyCommander")
        self.setGeometry(80, 80, 1300, 800)
        self.dark_mode = True
        self.filter_ext = ""  # e.g. ".txt" or "" for no filter

        # Terminal command history
        self.cmd_history = []
        self.cmd_history_index = -1

        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # Top-level splitter for panels and right-side tools
        main_splitter = QSplitter(Qt.Horizontal)

        # Left and right panel widgets
        left_widget = self.create_panel(side='left')
        right_widget = self.create_panel(side='right')

        # Right side: preview + terminal
        right_side = QWidget()
        right_side_layout = QVBoxLayout()
        right_side.setLayout(right_side_layout)

        # Preview panel
        preview_label = QLabel("Preview")
        pfont = preview_label.font()
        pfont.setBold(True)
        preview_label.setFont(pfont)
        self.preview_area = QTextEdit()
        self.preview_area.setReadOnly(True)
        self.preview_area.setFixedHeight(240)

        # Terminal panel (simple)
        term_label = QLabel("Terminal")
        tfont = term_label.font()
        tfont.setBold(True)
        term_label.setFont(tfont)
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setStyleSheet("background-color: black; color: lightgreen;")
        self.terminal.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))

        # Command input under terminal
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Введите команду и нажмите Enter")
        self.command_input.returnPressed.connect(self.execute_command)
        self.command_input.installEventFilter(self)  # for history navigation

        # Optional clear terminal button
        clear_term_btn = QPushButton("Clear")
        clear_term_btn.clicked.connect(self.terminal.clear)

        cmd_bar = QWidget()
        cmd_layout = QHBoxLayout()
        cmd_layout.setContentsMargins(0, 0, 0, 0)
        cmd_bar.setLayout(cmd_layout)
        cmd_layout.addWidget(self.command_input)
        cmd_layout.addWidget(clear_term_btn)

        # QProcess (if available)
        self.proc = None
        try:
            from PyQt5.QtCore import QProcess
            self.proc = QProcess(self)
            self.proc.readyReadStandardOutput.connect(self.on_proc_stdout)
            self.proc.readyReadStandardError.connect(self.on_proc_stderr)
            self.proc.finished.connect(self.on_proc_finished)
        except Exception:
            self.proc = None

        # Start shell if QProcess is available
        if self.proc:
            self.start_shell()

        right_side_layout.addWidget(preview_label)
        right_side_layout.addWidget(self.preview_area)
        right_side_layout.addWidget(term_label)
        right_side_layout.addWidget(self.terminal)
        right_side_layout.addWidget(cmd_bar)

        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.addWidget(right_side)
        main_splitter.setStretchFactor(0, 3)
        main_splitter.setStretchFactor(1, 3)
        main_splitter.setStretchFactor(2, 2)

        # Bottom toolbar: filter and theme toggle
        bottom_bar = QWidget()
        bottom_layout = QHBoxLayout()
        bottom_bar.setLayout(bottom_layout)

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Фильтр по расширению, например .txt  (Enter применяет)")
        self.filter_input.returnPressed.connect(self.apply_filter)

        apply_btn = QPushButton("Применить фильтр")
        apply_btn.clicked.connect(self.apply_filter)
        clear_btn = QPushButton("Очистить фильтр")
        clear_btn.clicked.connect(self.clear_filter)

        theme_toggle = QPushButton("Тёмная тема")
        theme_toggle.setCheckable(True)
        theme_toggle.setChecked(self.dark_mode)
        theme_toggle.clicked.connect(lambda: self.toggle_theme(not self.dark_mode))

        bottom_layout.addWidget(self.filter_input)
        bottom_layout.addWidget(apply_btn)
        bottom_layout.addWidget(clear_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(theme_toggle)

        # Central layout
        central = QWidget()
        central_layout = QVBoxLayout()
        central.setLayout(central_layout)
        central_layout.addWidget(main_splitter)
        central_layout.addWidget(bottom_bar)
        self.setCentralWidget(central)

        # Set application icon if exists
        ico_path = resource_path(os.path.join("icons", "app.ico"))
        if os.path.exists(ico_path):
            self.setWindowIcon(QIcon(ico_path))

    def create_panel(self, side='left'):
        """Create panel widget with combo (disks) + tree view."""
        panel_widget = QWidget()
        layout = QVBoxLayout()
        panel_widget.setLayout(layout)

        combo = QComboBox()
        combo.addItems(get_disks())
        combo.setEditable(False)

        model = QFileSystemModel()
        model.setRootPath('')

        tree = QTreeView()
        tree.setModel(model)
        tree.setAnimated(False)
        tree.setIndentation(20)
        tree.setSortingEnabled(True)
        tree.setContextMenuPolicy(Qt.CustomContextMenu)
        tree.customContextMenuRequested.connect(lambda pos, t=tree: self.show_menu(pos, t))
        tree.clicked.connect(lambda idx, t=tree: self.on_item_clicked(idx, t))
        # Enable drag/drop
        tree.setDragEnabled(True)
        tree.setAcceptDrops(True)
        tree.setDropIndicatorShown(True)
        tree.setDefaultDropAction(Qt.CopyAction)

        # set initial root
        initial = combo.currentText()
        tree.setRootIndex(model.index(initial))

        # wiring based on side
        if side == 'left':
            self.combo_left = combo
            self.model_left = model
            self.tree_left = tree
        else:
            self.combo_right = combo
            self.model_right = model
            self.tree_right = tree

        combo.currentTextChanged.connect(lambda path, m=model, t=tree: t.setRootIndex(m.index(path)))

        # pack
        layout.addWidget(combo)
        layout.addWidget(tree)
        return panel_widget

    def apply_theme(self):
        if self.dark_mode:
            self.setStyleSheet("""
                QMainWindow { background-color: #2b2b2b; color: white; }
                QTreeView { background-color: #1e1e1e; color: white; font-size: 13px; }
                QComboBox { background-color: #3c3c3c; color: white; }
                QPushButton { background-color: #4CAF50; color: white; padding: 6px; border-radius: 4px; }
                QLineEdit { background-color: #1e1e1e; color: white; }
                QTextEdit { background-color: #121212; color: #dcdcdc; }
                QLabel { color: white; }
            """)
        else:
            self.setStyleSheet("")

    def toggle_theme(self, state):
        self.dark_mode = bool(state)
        self.apply_theme()

    def show_menu(self, pos, tree):
        from PyQt5.QtWidgets import QMenu, QAction
        index = tree.indexAt(pos)
        menu = QMenu()
        # If empty area -> allow create folder
        if not index.isValid():
            create_action = QAction("Создать папку", self)
            create_action.triggered.connect(lambda t=tree: self.create_folder(t))
            menu.addAction(create_action)
            menu.exec_(tree.viewport().mapToGlobal(pos))
            return

        file_path = tree.model().filePath(index)
        self.status.showMessage(f"Selected: {file_path}")

        copy_icon_path = resource_path(os.path.join("icons", "copy.png"))
        delete_icon_path = resource_path(os.path.join("icons", "delete.png"))
        rename_icon_path = resource_path(os.path.join("icons", "rename.png"))

        copy_action = QAction(QIcon(copy_icon_path) if os.path.exists(copy_icon_path) else None, "Копировать", self)
        delete_action = QAction(QIcon(delete_icon_path) if os.path.exists(delete_icon_path) else None, "Удалить", self)
        rename_action = QAction(QIcon(rename_icon_path) if os.path.exists(rename_icon_path) else None, "Переименовать", self)
        properties_action = QAction("Свойства", self)

        copy_action.triggered.connect(lambda: self.copy_item(file_path))
        delete_action.triggered.connect(lambda: self.delete_item(file_path))
        rename_action.triggered.connect(lambda: self.rename_item(file_path))
        properties_action.triggered.connect(lambda: self.show_properties(file_path))

        menu.addAction(copy_action)
        menu.addAction(delete_action)
        menu.addAction(rename_action)
        menu.addSeparator()
        menu.addAction(properties_action)

        menu.exec_(tree.viewport().mapToGlobal(pos))

    def create_folder(self, tree):
        root_index = tree.rootIndex()
        model = tree.model()
        root_path = model.filePath(root_index)
        name, ok = QFileDialog.getSaveFileName(self, "Создать папку", root_path)
        # QFileDialog used to get a name; if cancelled, ok == ''
        if not name:
            return
        new_path = os.path.join(root_path, os.path.basename(name))
        try:
            os.makedirs(new_path, exist_ok=True)
            QMessageBox.information(self, "Создано", f"{new_path}")
        except PermissionError:
            QMessageBox.critical(self, "Ошибка", "Нет прав доступа. Запусти от имени администратора.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def copy_item(self, source):
        target = QFileDialog.getExistingDirectory(self, "Выберите папку назначения")
        if not target:
            return
        try:
            if os.path.isdir(source):
                dest = os.path.join(target, os.path.basename(source))
                shutil.copytree(source, dest)
            else:
                shutil.copy2(source, target)
            QMessageBox.information(self, "Успех", "Копирование завершено")
        except PermissionError:
            QMessageBox.critical(self, "Ошибка", "Нет прав доступа. Запусти от имени администратора.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def delete_item(self, path):
        reply = QMessageBox.question(self, "Подтвердите удаление", f"Удалить {path} ?", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            QMessageBox.information(self, "Удалено", "Удаление выполнено")
        except PermissionError:
            QMessageBox.critical(self, "Ошибка", "Нет прав доступа. Запусти от имени администратора.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def rename_item(self, path):
        base = os.path.dirname(path)
        old_name = os.path.basename(path)
        new_name, ok = QFileDialog.getSaveFileName(self, "Переименовать", os.path.join(base, old_name))
        if not new_name:
            return
        new_path = os.path.join(base, os.path.basename(new_name))
        try:
            os.rename(path, new_path)
            QMessageBox.information(self, "Переименовано", f"{old_name} → {os.path.basename(new_path)}")
        except PermissionError:
            QMessageBox.critical(self, "Ошибка", "Нет прав доступа. Запусти от имени администратора.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def show_properties(self, path):
        try:
            is_dir = os.path.isdir(path)
            size = 0
            if is_dir:
                for root, dirs, files in os.walk(path):
                    for f in files:
                        try:
                            fp = os.path.join(root, f)
                            size += os.path.getsize(fp)
                        except Exception:
                            pass
            else:
                size = os.path.getsize(path)
            created = time.ctime(os.path.getctime(path))
            modified = time.ctime(os.path.getmtime(path))
            info = f"Путь: {path}\nТип: {'Папка' if is_dir else 'Файл'}\nРазмер: {human_size(size)}\nСоздан: {created}\nИзменён: {modified}"
            QMessageBox.information(self, "Свойства", info)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def on_item_clicked(self, index, tree):
        model = tree.model()
        path = model.filePath(index)
        try:
            if os.path.exists(path):
                size = os.path.getsize(path) if os.path.isfile(path) else 0
                mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
                self.status.showMessage(f"{path}    Size: {human_size(size)}    Modified: {mtime}")
            else:
                self.status.showMessage(path)
        except Exception:
            self.status.showMessage(path)
        if os.path.isfile(path):
            try:
                ext = os.path.splitext(path)[1].lower()
                if ext in ['.txt', '.py', '.md', '.json', '.log', '.csv', '.ini']:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        data = f.read(10000)
                    self.preview_area.setPlainText(data)
                else:
                    self.preview_area.setPlainText(f"Preview not available for {ext} files.")
            except Exception:
                self.preview_area.setPlainText("Невозможно показать превью.")
        else:
            self.preview_area.setPlainText("")

    def apply_filter(self):
        txt = self.filter_input.text().strip()
        if txt and not txt.startswith('.'):
            txt = '.' + txt
        self.filter_ext = txt.lower()
        QMessageBox.information(self, "Фильтр", f"Фильтр по расширению: {self.filter_ext or 'нет'}.\n(В этом примере фильтр применяется при поиске или можно доработать через QSortFilterProxyModel.)")

    def clear_filter(self):
        self.filter_input.clear()
        self.filter_ext = ""
        QMessageBox.information(self, "Фильтр", "Фильтр очищен.")

    def start_shell(self):
        try:
            from PyQt5.QtCore import QProcess
            self.proc = QProcess(self)
            # объединяем stderr в stdout — удобнее читать
            self.proc.setProcessChannelMode(QProcess.MergedChannels)
            self.proc.readyReadStandardOutput.connect(self.on_proc_stdout)
            self.proc.finished.connect(self.on_proc_finished)

            if os.name == 'nt':
                # Запуск cmd.exe в интерактивном режиме
                self.proc.start("cmd.exe")
            else:
                self.proc.start("/bin/bash")

            # подождать, чтобы убедиться, что процесс действительно стартовал
            started = self.proc.waitForStarted(3000)
            if not started:
                self.terminal.append("Не удалось запустить shell (waitForStarted timed out).")
                self.proc = None
        except Exception as e:
            self.terminal.append(f"Failed to start shell: {e}")
            self.proc = None

    def execute_command(self):
        cmd = self.command_input.text().strip()
        if not cmd:
            return
        if not self.proc or self.proc.state() != self.proc.Running:
            self.terminal.append("Процесс терминала не запущен.")
            return

        # Сохраняем историю
        self.cmd_history.append(cmd)
        self.cmd_history_index = len(self.cmd_history)

        # Показываем команду в терминале
        self.terminal.append(f"> {cmd}")

        # Формируем корректный перевод строки для платформы
        nl = "\r\n" if os.name == 'nt' else "\n"
        try:
            written = self.proc.write((cmd + nl).encode("utf-8"))
            # дождаться записи данных в процесс (не блокировать надолго)
            self.proc.waitForBytesWritten(1000)
            if written == -1:
                self.terminal.append("Не удалось записать команду в процесс.")
        except Exception as e:
            self.terminal.append(f"Failed to write to process: {e}")

        self.command_input.clear()

    def eventFilter(self, obj, event):
        """Handle up/down arrow navigation for command history in command_input."""
        from PyQt5.QtCore import QEvent
        if obj is self.command_input and event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Up:
                if self.cmd_history:
                    self.cmd_history_index = max(0, self.cmd_history_index - 1)
                    self.command_input.setText(self.cmd_history[self.cmd_history_index])
                    return True
            elif key == Qt.Key_Down:
                if self.cmd_history:
                    self.cmd_history_index = min(len(self.cmd_history) - 1, self.cmd_history_index + 1)
                    if self.cmd_history_index >= len(self.cmd_history):
                        self.command_input.clear()
                    else:
                        self.command_input.setText(self.cmd_history[self.cmd_history_index])
                    return True
        return super().eventFilter(obj, event)

    def on_proc_stdout(self):
        if not self.proc:
            return
        try:
            while self.proc.bytesAvailable():
                data = bytes(self.proc.readAllStandardOutput()).decode('utf-8', errors='replace')
                # добавляем без лишних переносов
                self.terminal.moveCursor(self.terminal.textCursor().End)
                self.terminal.insertPlainText(data)
        except Exception as e:
            self.terminal.append(f"[read error] {e}")

    def on_proc_stderr(self):
        if not self.proc:
            return
        data = bytes(self.proc.readAllStandardError()).decode('utf-8', errors='replace')
        # For stderr we prefix to make it noticeable
        self.terminal.moveCursor(self.terminal.textCursor().End)
        self.terminal.insertPlainText(data)

    def on_proc_finished(self):
        self.terminal.append("\n[Shell process finished]\n")
        self.proc = None

    # -----------------------
    # Remaining helper methods (preview, file ops, etc.)
    # -----------------------
    def on_item_clicked(self, index, tree):
        model = tree.model()
        path = model.filePath(index)
        try:
            if os.path.exists(path):
                size = os.path.getsize(path) if os.path.isfile(path) else 0
                mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
                self.status.showMessage(f"{path}    Size: {human_size(size)}    Modified: {mtime}")
            else:
                self.status.showMessage(path)
        except Exception:
            self.status.showMessage(path)
        if os.path.isfile(path):
            try:
                ext = os.path.splitext(path)[1].lower()
                if ext in ['.txt', '.py', '.md', '.json', '.log', '.csv', '.ini']:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        data = f.read(10000)
                    self.preview_area.setPlainText(data)
                else:
                    self.preview_area.setPlainText(f"Preview not available for {ext} files.")
            except Exception:
                self.preview_area.setPlainText("Невозможно показать превью.")
        else:
            self.preview_area.setPlainText("")

    def apply_filter(self):
        txt = self.filter_input.text().strip()
        if txt and not txt.startswith('.'):
            txt = '.' + txt
        self.filter_ext = txt.lower()
        QMessageBox.information(self, "Фильтр", f"Фильтр по расширению: {self.filter_ext or 'нет'}.\n(В этом примере фильтр применяется при поиске или можно доработать через QSortFilterProxyModel.)")

    def clear_filter(self):
        self.filter_input.clear()
        self.filter_ext = ""
        QMessageBox.information(self, "Фильтр", "Фильтр очищен.")

    # Note: create_folder, copy_item, delete_item, rename_item, show_properties,
    # human_size and get_disks are defined above and used here.

def main():
    app = QApplication(sys.argv)

    # Splash (if splash.png exists)
    splash_path = resource_path("splash.png")
    splash = None
    if os.path.exists(splash_path):
        pix = QPixmap(splash_path)
        splash = QSplashScreen(pix)
        splash.show()
        app.processEvents()
        time.sleep(0.8)  # short pause to show splash

    window = FileManager()
    window.show()

    if splash:
        splash.finish(window)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
