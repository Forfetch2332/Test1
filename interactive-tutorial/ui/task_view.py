from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPlainTextEdit, QPushButton
import io, contextlib, traceback
import resource_helper as rh
from typing import Any, Dict, List

from ui.hints_renderer import HintsRenderer
from ui.hints_utils import normalize_hints


class TaskView(QWidget):
    def __init__(self, task: Dict[str, Any]):
        super().__init__()
        self.setWindowTitle(task.get("title", "Задача"))
        layout = QVBoxLayout(self)

        self.title = QLabel(task.get("title", "Задача"))
        self.title.setStyleSheet("font-weight: bold; font-size: 16px;")

        self.statement = QPlainTextEdit()
        self.statement.setReadOnly(True)
        self.statement.setPlainText(task.get("statement", ""))

        # HintsRenderer — одинаковый формат показа подсказок
        self.hints_renderer = HintsRenderer()

        self.code_input = QPlainTextEdit()
        self.run_btn = QPushButton("Запустить")
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)

        layout.addWidget(self.title)
        layout.addWidget(self.statement)
        layout.addWidget(self.hints_renderer)
        layout.addWidget(QLabel("Ввод кода"))
        layout.addWidget(self.code_input)
        layout.addWidget(self.run_btn)
        layout.addWidget(QLabel("Вывод"))
        layout.addWidget(self.output)

        self.run_btn.clicked.connect(self.run_code)

        # Подсказки: ожидаем что task["hints"] — список строк или элементов
        raw_hints = task.get("hints", [])
        hints = normalize_hints(raw_hints)
        self.hints_renderer.show_hints(hints)

    def run_code(self):
        code = self.code_input.toPlainText()
        buf = io.StringIO()
        err_buf = io.StringIO()
        ns = {}
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err_buf):
                exec(code, ns)
        except Exception:
            tb = traceback.format_exc()
            self.output.setPlainText(f"Ошибка:\n{tb}")
            return

        out_text = buf.getvalue()
        err_text = err_buf.getvalue()
        combined = out_text
        if err_text:
            if combined:
                combined += "\n"
            combined += "STDERR:\n" + err_text
        self.output.setPlainText(combined)
