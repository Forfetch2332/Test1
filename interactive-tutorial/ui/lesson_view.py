from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPlainTextEdit, QPushButton, QSizePolicy
)
import io, contextlib, traceback
import resource_helper as rh
from typing import Any, Dict, List

from ui.hints_renderer import HintsRenderer
from ui.hints_utils import extract_hints_from_lesson


class LessonView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.title = QLabel("Урок")
        self.title.setStyleSheet("font-weight: bold; font-size: 18px;")

        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.text.setMinimumHeight(200)

        # Встраиваем компактный HintsRenderer
        self.hints_renderer = HintsRenderer()
        # делаем renderer предпочтительным, но не доминирующим
        self.hints_renderer.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        self.code = QPlainTextEdit()
        self.code.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.run_btn = QPushButton("Запустить")
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMinimumHeight(120)
        self.output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout.addWidget(self.title)
        layout.addWidget(self.text)
        layout.addWidget(self.hints_renderer)
        layout.addWidget(QLabel("Пример кода"))
        layout.addWidget(self.code)
        layout.addWidget(self.run_btn)
        layout.addWidget(QLabel("Вывод"))
        layout.addWidget(self.output)

        self.run_btn.clicked.connect(self.run_code)

    def load_lesson(self, lesson: Dict[str, Any]):
        try:
            rh.log(f"LessonView.load_lesson called; keys={list(lesson.keys())}")
        except Exception:
            rh.log("LessonView.load_lesson called")

        self.title.setText(lesson.get("title", "Урок"))

        body = lesson.get("text", [])
        if isinstance(body, list):
            self.text.setPlainText("\n\n".join(body))
        else:
            self.text.setPlainText(str(body))

        self.code.setPlainText(lesson.get("example", "") or "")

        # извлекаем подсказки и передаём в renderer
        hints = extract_hints_from_lesson(lesson)
        self.hints_renderer.show_hints(hints)

    def show_error(self, message: str):
        self.title.setText("Ошибка урока")
        self.text.setPlainText(message)
        self.code.clear()
        self.output.clear()
        self.hints_renderer.clear()

    def run_code(self):
        code = self.code.toPlainText()
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
