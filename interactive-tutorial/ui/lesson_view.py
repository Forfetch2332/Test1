from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPlainTextEdit, QPushButton, QTextEdit
import io, contextlib

class LessonView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.title = QLabel("Урок")
        self.title.setStyleSheet("font-weight: bold, font-size: 18px")
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.code = QPlainTextEdit()
        self.run_btn = QPushButton("Запустить")
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)

        layout.addWidget(self.title)
        layout.addWidget(self.text)
        layout.addWidget(QLabel("Пример кода"))
        layout.addWidget(self.code)
        layout.addWidget(self.run_btn)
        layout.addWidget(QLabel("Вывод"))
        layout.addWidget(self.output)

        self.run_btn.clicked.connect(self.run_code)

    def load_lesson(self, lesson):
        self.text.setText(lesson.get("title", "Урок"))
        body = lesson.get("text", [])
        self.text.setPlainText("\n\n".join(body))
        self.code.setPlainText(lesson.get("example", ""))

    def show_error(self, message: str):
        self.title.setText("Ошибка урока")
        self.text.setPlainText(message)
        self.code.clear()
        self.output.clear()

    def run_code(self):
        code = self.code.toPlainText()
        buf = io.StringIO()
        ns = {}
        try:
            with contextlib.redirect_stdout(buf):
                exec(code, ns, ns)
        except Exception as e:
            self.ouyput.setPlainText(f"Ошибка: {e}")
            return
        self.output.setPlainText(buf.getvalue())