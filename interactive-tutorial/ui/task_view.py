from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPlainTextEdit, QPushButton
import io, contextlib

class TaskView(QWidget):
    def __init__(self, task: dict):
        super().__init__()
        self.task = task
        self.setWindowTitle(task.get("title", "Задача"))

        layout = QVBoxLayout(self)

        self.statement = QLabel(task.get("statement", ""))
        self.code = QPlainTextEdit(task.get("template", ""))
        self.check_btn = QPushButton("Проверить")
        self.result = QLabel(" ")

        layout.addWidget(self.statement)
        layout.addWidget(self.code)
        layout.addWidget(self.check_btn)
        layout.addWidget(self.result)

        self.check_btn.clicked.connect(self.check_solution)

    def check_solution(self):
        code = self.code.toPlainText()
        check = self.task.get("check", {})
        buf = io.StringIO()
        ns = {}
        try:
            with contextlib.redirect_stdout(buf):
                exec(code, ns, ns)
        except Exception as e:
            self.result.setText(f"Ошибка: {e}")
            return

        if check.get("type") == "stdout_equals":
            expected = check.get("expected", "")
            got = buf.getvalue().strip()
            self.result.setText("Верно!" if got == expected else f"Неверно. Ожидалось: {expected}, получено: {got}")
        else:
            self.result.setText("Неизвестный тип проверки")
