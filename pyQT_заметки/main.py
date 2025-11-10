import sys
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTextEdit, QPushButton, QVBoxLayout,
    QMessageBox, QFileDialog, QLineEdit, QTabWidget, QLabel
)
from PyQt5.QtGui import QIcon

class NotesApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Заметки")
        self.setGeometry(100, 100, 500, 400)
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                font-family: Arial;
                font-size: 14px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QTextEdit, QLineEdit {
                background-color: white;
                border: 1px solid #ccc;
                padding: 6px;
            }
        """)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_note_tab(), "Новая заметка")
        self.tabs.addTab(self.create_search_tab(), "Поиск")

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)

    # 📄 Вкладка "Новая заметка"
    def create_note_tab(self):
        tab = QWidget()
        self.text_field = QTextEdit()
        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.save_note)

        layout = QVBoxLayout()
        layout.addWidget(self.text_field)
        layout.addWidget(save_button)
        tab.setLayout(layout)
        return tab

    # 🔍 Вкладка "Поиск"
    def create_search_tab(self):
        tab = QWidget()
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Введите текст для поиска...")
        search_button = QPushButton("Поиск")
        search_button.clicked.connect(self.search_notes)

        layout = QVBoxLayout()
        layout.addWidget(self.search_field)
        layout.addWidget(search_button)
        tab.setLayout(layout)
        return tab

    # 📂 Сохранение заметки с датой и выбором файла
    def save_note(self):
        text = self.text_field.toPlainText().strip()
        if text:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить заметку", "заметка.txt", "Text Files (*.txt)")
            if file_path:
                try:
                    with open(file_path, "a", encoding="utf-8") as file:
                        file.write(f"[{now}]\n{text}\n{'-'*40}\n")
                    self.text_field.clear()
                    QMessageBox.information(self, "Успех", "Заметка сохранена!")
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {e}")
        else:
            QMessageBox.warning(self, "Пусто", "Введите текст заметки.")

    # 🔍 Поиск по заметкам
    def search_notes(self):
        query = self.search_field.text().strip().lower()
        if query:
            try:
                with open("заметка.txt", "r", encoding="utf-8") as file:
                    content = file.read()
                results = [block.strip() for block in content.split("-"*40) if query in block.lower()]
                if results:
                    QMessageBox.information(self, "Результаты", "\n\n".join(results))
                else:
                    QMessageBox.information(self, "Результаты", "Ничего не найдено.")
            except FileNotFoundError:
                QMessageBox.warning(self, "Ошибка", "Файл заметок не найден.")
        else:
            QMessageBox.warning(self, "Пусто", "Введите текст для поиска.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NotesApp()
    window.show()
    sys.exit(app.exec_())
