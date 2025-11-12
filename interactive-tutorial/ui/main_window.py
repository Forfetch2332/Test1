import os
from typing import Any, Dict, List, Optional

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QPushButton, QLabel, QMessageBox
)
from PyQt5.QtCore import Qt
from ui.lesson_view import LessonView
from ui.task_view import TaskView
import resource_helper as rh
from content_validator import validate_lesson, validate_task

JSONDict = Dict[str, Any]


def _normalize_hints(raw) -> List[str]:
    """Привести raw к списку непустых строк."""
    if not isinstance(raw, list):
        return []
    out: List[str] = []
    for i, item in enumerate(raw):
        try:
            s = "" if item is None else str(item)
        except Exception:
            rh.log(f"Hint normalization: could not stringify hint[{i}] -> {item!r}")
            continue
        s = s.strip()
        if s:
            out.append(s)
    return out


def _extract_hints_from_lesson(data: Dict[str, Any]) -> List[str]:
    """
    Извлечь подсказки из lesson-объекта:
      - сначала смотрим поле "hints" (список строк),
      - затем поле "notes" (список объектов с ключом "hint").
    """
    if not isinstance(data, dict):
        return []

    raw_hints = data.get("hints", [])
    if isinstance(raw_hints, list) and any(isinstance(x, str) for x in raw_hints):
        return _normalize_hints(raw_hints)

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


class MainWindow(QMainWindow):
    topics: List[JSONDict]
    current_task_path: Optional[str]
    _task_windows: List[QWidget]

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Interactive Tutorial")
        self.resize(1000, 700)

        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)

        left = QVBoxLayout()
        left.addWidget(QLabel("Темы"))
        self.topics_list = QListWidget()
        left.addWidget(self.topics_list)

        self.open_task_btn = QPushButton("Задача")
        self.open_task_btn.clicked.connect(self.open_task)
        left.addWidget(self.open_task_btn)
        left.addStretch(1)

        layout.addLayout(left, 1)

        self.lesson_view = LessonView()
        layout.addWidget(self.lesson_view, 3)

        # состояние
        self.current_task_path = None
        self._task_windows = []
        self.topics = []

        # загрузка topics
        topics_data, err = rh.load_json_resource(os.path.join("content", "topics.json"))
        if err:
            self._error_dialog("Ошибка загрузки тем", err)
            self.topics = []
        else:
            self.topics = topics_data.get("topics", [])

        for t in self.topics:
            self.topics_list.addItem(t.get("title", "-"))

        self.topics_list.currentRowChanged.connect(self.on_topic_selected)
        if self.topics:
            self.topics_list.setCurrentRow(0)

    def on_topic_selected(self, idx: int) -> None:
        if idx < 0 or idx >= len(self.topics):
            return

        topic = self.topics[idx]
        lesson_rel = topic.get("lesson")
        if not lesson_rel:
            rh.log(f"Topic has no lesson path: {topic}")
            self.lesson_view.show_error("У этой темы нет урока")
            self.current_task_path = None
            return

        rel_lesson = os.path.join("content", lesson_rel)
        data, err = rh.load_json_resource(rel_lesson)
        if err:
            self.lesson_view.show_error(f"Ошибка загрузки урока:\n{err}")
            self.current_task_path = None
            return

        ok, verr = validate_lesson(data)
        if not ok:
            rh.log(f"Lesson validation error ({lesson_rel}): {verr}")
            self.lesson_view.show_error(f"Ошибка валидации урока:\n{verr}")
            self.current_task_path = None
            return

        # Извлекаем подсказки из lesson (hints или notes) и подставляем их в копию данных
        hints = _extract_hints_from_lesson(data)
        data_copy = dict(data)
        data_copy["hints"] = hints  # теперь LessonView увидит подсказки как список строк

        rh.log(f"on_topic_selected: extracted {len(hints)} hints for lesson {rel_lesson}")

        self.lesson_view.load_lesson(data_copy)
        self.current_task_path = topic.get("task")

    def open_task(self) -> None:
        if not getattr(self, "current_task_path", None):
            self._info_dialog("Задача недоступна", "Для этой темы задача не предусмотрена")
            return

        rel = os.path.join("content", self.current_task_path)
        task, err = rh.load_json_resource(rel)
        if err:
            self._error_dialog("Ошибка загрузки задачи", err)
            return

        ok, verr = validate_task(task)
        if not ok:
            rh.log(f"Task validation error ({rel}): {verr}")
            self._error_dialog("Ошибка валидации задачи", verr)
            return

        tv: TaskView = TaskView(task)

        # сохраняем ссылку, чтобы окно не было удалено сборщиком мусора
        self._task_windows.append(tv)

        tv.setWindowFlag(Qt.Window, True)
        tv.setWindowModality(Qt.ApplicationModal)
        tv.show()
        tv.raise_()
        tv.activateWindow()

    def _error_dialog(self, title: str, msg: str) -> None:
        QMessageBox.critical(self, title, msg)

    def _info_dialog(self, title: str, msg: str) -> None:
        QMessageBox.information(self, title, msg)
