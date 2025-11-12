from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPlainTextEdit, QPushButton, QTextEdit
)
import io, contextlib, traceback
import resource_helper as rh
from typing import Any, Dict, List


def _normalize_hints(raw) -> List[str]:
    """Привести raw к списку непустых строк."""
    if not isinstance(raw, list):
        return []
    out: List[str] = []
    for i, item in enumerate(raw):
        try:
            s = "" if item is None else str(item)
        except Exception:
            rh.log(f"LessonView: could not stringify hint[{i}] -> {item!r}")
            continue
        s = s.strip()
        if s:
            out.append(s)
    return out


def _extract_hints_from_lesson(data: Dict[str, Any]) -> List[str]:
    """
    Извлечь подсказки из lesson-объекта.
    Поддерживаем два варианта:
      - поле "hints": список строк
      - поле "notes": список объектов {"hint": "..."}
    Возвращаем список строк (возможен пустой список).
    """
    if not isinstance(data, dict):
        return []

    # Прямые hints (если это список строк)
    raw_hints = data.get("hints", [])
    if isinstance(raw_hints, list) and any(isinstance(x, str) for x in raw_hints):
        return _normalize_hints(raw_hints)

    # notes -> [{"hint": "..."}]
    notes = data.get("notes", [])
    if isinstance(notes, list):
        extracted: List[str] = []
        for i, note in enumerate(notes):
            if not isinstance(note, dict):
                continue
            h = note.get("hint")
            if isinstance(h, str) and h.strip():
                extracted.append(h.strip())
        return extracted

    return []


class LessonView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self.title = QLabel("Урок")
        self.title.setStyleSheet("font-weight: bold; font-size: 18px;")

        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)

        # Подсказки
        self.hints_label = QLabel("Подсказки")
        self.hints = QTextEdit()
        self.hints.setReadOnly(True)
        self.hints.setPlaceholderText("Подсказки появятся здесь, если они есть")

        self.code = QPlainTextEdit()
        self.run_btn = QPushButton("Запустить")
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)

        layout.addWidget(self.title)
        layout.addWidget(self.text)
        layout.addWidget(self.hints_label)
        layout.addWidget(self.hints)
        layout.addWidget(QLabel("Пример кода"))
        layout.addWidget(self.code)
        layout.addWidget(self.run_btn)
        layout.addWidget(QLabel("Вывод"))
        layout.addWidget(self.output)

        self.run_btn.clicked.connect(self.run_code)

        # По умолчанию скрываем секцию подсказок
        self.hints_label.hide()
        self.hints.hide()

    def load_lesson(self, lesson: Dict[str, Any]):
        """
        Ожидает lesson как словарь (parsed JSON).
        Извлекает и отображает подсказки (hints или notes).
        """
        rh.log(f"LessonView.load_lesson called; keys={list(lesson.keys())}")
        self.title.setText(lesson.get("title", "Урок"))

        body = lesson.get("text", [])
        if isinstance(body, list):
            self.text.setPlainText("\n\n".join(body))
        else:
            self.text.setPlainText(str(body))

        self.code.setPlainText(lesson.get("example", ""))

        hints = _extract_hints_from_lesson(lesson)
        if hints:
            # отображаем по одной строке на строку, как в TaskView
            self.hints.setPlainText("\n".join(hints))
            self.hints_label.show()
            self.hints.show()
            rh.log(f"LessonView: displayed {len(hints)} hints")
        else:
            self.hints.clear()
            self.hints_label.hide()
            self.hints.hide()
            rh.log("LessonView: no hints to display")

    def show_error(self, message: str):
        self.title.setText("Ошибка урока")
        self.text.setPlainText(message)
        self.code.clear()
        self.output.clear()
        self.hints.clear()
        self.hints_label.hide()
        self.hints.hide()

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
