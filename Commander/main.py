import sys
import os
import shutil
import psutil
import time
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTreeView, QFileSystemModel, QSplitter,
    QMenu, QAction, QMessageBox, QStatusBar, QComboBox, QVBoxLayout,
    QWidget, QFileDialog, QInputDialog, QCheckBox, QLabel, QHBoxLayout,
    QTextEdit, QPushButton, QSizePolicy, QLineEdit
)
from PyQt5.QtCore import Qt, QPoint, QProcess
from PyQt5.QtGui import QIcon, QPixmap, QFont
from PyQt5.QtWidgets import QSplashScreen

# ---------------------------
# Utility: resource path
# ---------------------------
def resource_path(relative_path: str) -> str:
    """
    Return absolute path to resource, works for dev and for PyInstaller.
    """
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)

# ---------------------------
# Utilities
# ---------------------------
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
    for unit in ['B','KB','MB','GB','TB']:
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"

# ---------------------------
# Main Window
# ---------------------------
class FileManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyCommander")
        self.setGeometry(80, 80, 1300, 800)
        self.dark_mode = True
        self.filter_ext = ""  # e.g. ".txt" or "" for no filter

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
        preview_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.preview_area = QTextEdit()
        self.preview_area.setReadOnly(True)
        self.preview_area.setFixedHeight(240)

        # Terminal panel (simple)
        term_label = QLabel("Terminal")
        term_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setStyleSheet("background-color: black; color: lightgreen;")
        self.terminal.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.proc = QProcess(self)
        self.proc.readyReadStandardOutput.connect(self.on_proc_stdout)
        self.proc.readyReadStandardError.connect(self.on_proc_stderr)
        # Start shell
        self.start_shell()

        right_side_layout.addWidget(preview_label)
        right_side_layout.addWidget(self.preview_area)
        right_side_layout.addWidget(term_label)
        right_side_layout.addWidget(self.terminal)

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

        theme_toggle = QCheckBox("Тёмная тема")
        theme_toggle.setChecked(self.dark_mode)
        theme_toggle.stateChanged.connect(self.toggle_theme)

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

    # -----------------------
    # Theme
    # -----------------------
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

    # -----------------------
    # Context menu and file ops
    # -----------------------
    def show_menu(self, pos: QPoint, tree: QTreeView):
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
        name, ok = QInputDialog.getText(self, "Создать папку", "Имя папки:")
        if ok and name:
            new_path = os.path.join(root_path, name)
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
        new_name, ok = QInputDialog.getText(self, "Переименовать", "Новое имя:", text=old_name)
        if not ok or not new_name:
            return
        new_path = os.path.join(base, new_name)
        try:
            os.rename(path, new_path)
            QMessageBox.information(self, "Переименовано", f"{old_name} → {new_name}")
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

    # -----------------------
    # Selection / preview / status
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

    # -----------------------
    # Filter (placeholder)
    # -----------------------
    def apply_filter(self):
        txt = self.filter_input.text().strip()
        if txt and not txt.startswith('.'):
            txt = '.' + txt
        self.filter_ext = txt.lower()
        QMessageBox.information(self, "Фильтр", f"Фильтр по расширению: {self.filter_ext or 'нет'}.\n(Для реальной фильтрации замените модель на QSortFilterProxyModel.)")

    def clear_filter(self):
        self.filter_input.clear()
        self.filter_ext = ""
        QMessageBox.information(self, "Фильтр", "Фильтр очищен.")

    # -----------------------
    # Terminal handling
    # -----------------------
    def start_shell(self):
        if os.name == 'nt':
            shell = "cmd.exe"
        else:
            shell = "/bin/bash"
        try:
            self.proc.start(shell)
        except Exception as e:
            self.terminal.append(f"Failed to start shell: {e}")

    def on_proc_stdout(self):
        data = bytes(self.proc.readAllStandardOutput()).decode('utf-8', errors='replace')
        self.terminal.moveCursor(self.terminal.textCursor().End)
        self.terminal.insertPlainText(data)

    def on_proc_stderr(self):
        data = bytes(self.proc.readAllStandardError()).decode('utf-8', errors='replace')
        self.terminal.moveCursor(self.terminal.textCursor().End)
        self.terminal.insertPlainText(data)

# ---------------------------
# Splash and run
# ---------------------------
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
