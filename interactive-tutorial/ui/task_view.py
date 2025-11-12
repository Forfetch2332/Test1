from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPlainTextEdit, QPushButton, QTextEdit
import io, contextlib, traceback

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

        # Виджет для подсказок
        self.hints_label = QLabel("Подсказки")
        self.hints = QTextEdit()
        self.hints.setReadOnly(True)
        self.hints.setPlaceholderText("Подсказки появятся здесь, если они есть")

        layout.addWidget(self.statement)
        layout.addWidget(self.hints_label)
        layout.addWidget(self.hints)
        layout.addWidget(self.code)
        layout.addWidget(self.check_btn)
        layout.addWidget(self.result)

        self.check_btn.clicked.connect(self.check_solution)

        # Загрузить подсказки при инициализации
        self.load_hints(self.task)

    def load_hints(self, task: dict):
        hints = task.get("hints", [])
        if isinstance(hints, list) and hints:
            # Отображаем каждую подсказку на новой строке
            self.hints.setPlainText("\n".join(hints))
            self.hints_label.show()
            self.hints.show()
        else:
            # Если подсказок нет, скрыть секцию
            self.hints.clear()
            self.hints_label.hide()
            self.hints.hide()

    def check_solution(self):
        code = self.code.toPlainText()
        check = self.task.get("check", {})
        buf = io.StringIO()
        err_buf = io.StringIO()
        ns = {}

        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err_buf):
                exec(code, ns)
        except Exception:
            tb = traceback.format_exc()
            self.result.setText(f"Ошибка:\n{tb}")
            return

        if check.get("type") == "stdout_equals":
            expected = check.get("expected", "")
            got = buf.getvalue().strip()
            if got == expected:
                self.result.setText("Верно!")
            else:
                self.result.setText(f"Неверно. Ожидалось: {expected}, получено: {got}")
        else:
            self.result.setText("Неизвестный тип проверки")
