import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QPushButton, QLabel, QMessageBox
)
from PyQt5.QtCore import Qt
from ui.lesson_view import LessonView
from ui.task_view import TaskView
import resource_helper as rh
from content_validator import validate_lesson, validate_task


class MainWindow(QMainWindow):
    def __init__(self):
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

        self.current_task_path = None
        self._task_windows = []

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

    def on_topic_selected(self, idx: int):
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

        self.lesson_view.load_lesson(data)
        self.current_task_path = topic.get("task")

    def open_task(self):
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

        tv = TaskView(task)

        # Сохраняем ссылку, чтобы окно не было уничтожено сборщиком мусора
        self._task_windows.append(tv)

        tv.setWindowFlag(Qt.Window, True)
        tv.setWindowModality(Qt.ApplicationModal)
        tv.show()
        tv.raise_()
        tv.activateWindow()

    def _error_dialog(self, title: str, msg: str):
        QMessageBox.critical(self, title, msg)

    def _info_dialog(self, title: str, msg: str):
        QMessageBox.information(self, title, msg)
