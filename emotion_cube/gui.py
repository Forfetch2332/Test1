import sys
import json
import os

from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QPoint
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QOpenGLWidget, QInputDialog,
    QPushButton, QVBoxLayout, QWidget, QFileDialog, QListWidget,
    QLineEdit, QLabel, QHBoxLayout
)
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np


class EmotionCube(QOpenGLWidget):
    selectedFaceChanged = pyqtSignal(int)  # emits -1 when None

    def __init__(self, parent=None):
        super().__init__(parent)

        # rotation state
        self.rot_x = 20.0
        self.rot_y = 30.0
        self.auto_spin_speed = 0.6
        self.dragging = False
        self.last_mouse_pos = QPoint()
        self.mouse_moved_while_dragging = False

        # camera distance (for optional zoom)
        self.cam_dist = 6.0

        # auto-rotate timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.timer.start(16)  # ~60 FPS

        # interaction
        self.setMouseTracking(True)
        self.hover_face = None
        self._selected_face = None

        # emotions storage
        self.emotions = {
            0: {"name": "Гнев", "color": (1, 0, 0), "notes": []},
            1: {"name": "Спокойствие", "color": (0, 0, 1), "notes": []},
            2: {"name": "Надежда", "color": (0, 1, 0), "notes": []},
            3: {"name": "Радость", "color": (1, 1, 0), "notes": []},
            4: {"name": "Вдохновение", "color": (0.5, 0, 0.5), "notes": []},
            5: {"name": "Усталость", "color": (0.5, 0.5, 0.5), "notes": []}
        }
        self.load_emotions()

        # matrices saved from paintGL for picking
        self._modelview = None
        self._projection = None
        self._viewport = None

    @property
    def selected_face(self):
        return self._selected_face

    @selected_face.setter
    def selected_face(self, value):
        if value is None:
            int_val = -1
        else:
            int_val = int(value)
        if self._selected_face != value:
            self._selected_face = value
            self.selectedFaceChanged.emit(int_val)

    # Persistence
    def load_emotions(self):
        if os.path.exists("emotions.json"):
            try:
                with open("emotions.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for face_id, info in data.items():
                        fid = int(face_id)
                        if fid in self.emotions:
                            self.emotions[fid]["notes"] = info.get("notes", [])
            except Exception as e:
                print(f"Ошибка загрузки эмоций: {e}")

    def save_emotions(self):
        try:
            data = {
                face_id: {
                    "name": info["name"],
                    "color": info["color"],
                    "notes": info["notes"]
                }
                for face_id, info in self.emotions.items()
            }
            with open("emotions.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения эмоций: {e}")

    def export_notes(self):
        try:
            path, _ = QFileDialog.getSaveFileName(
                self, "Сохранить мысли", "emotion_notes.txt", "Text Files (*.txt)"
            )
            if not path:
                return
            with open(path, "w", encoding="utf-8") as f:
                for face_id, info in self.emotions.items():
                    f.write(f"{info['name']}:\n")
                    for note in info["notes"]:
                        f.write(f" - {note}\n")
                    f.write("\n")
            print(f"Мысли экспортированы в {path}")
        except Exception as e:
            print(f"Ошибка экспорта: {e}")

    # Rendering and animation
    def rotate(self):
        if not self.dragging:
            self.rot_y += self.auto_spin_speed
        self.update()

    def initializeGL(self):
        glClearColor(0, 0, 0, 1)
        glEnable(GL_DEPTH_TEST)
        glShadeModel(GL_SMOOTH)

    def resizeGL(self, width, height):
        if height == 0:
            height = 1
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, width / float(height), 1.0, 100.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(0.0, 0.0, -self.cam_dist)
        glRotatef(self.rot_x, 1.0, 0.0, 0.0)
        glRotatef(self.rot_y, 0.0, 1.0, 0.0)

        # Save matrices for picking
        try:
            self._modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
            self._projection = glGetDoublev(GL_PROJECTION_MATRIX)
            self._viewport = glGetIntegerv(GL_VIEWPORT)
        except Exception as e:
            self._modelview = None
            self._projection = None
            self._viewport = None
            print(f"Ошибка получения матриц: {e}")

        self.drawCube()

    def drawCube(self):
        glBegin(GL_QUADS)

        def col(c, highlight=False, selected=False):
            r, g, b = c
            if selected:
                return (min(1.0, r + 0.35), min(1.0, g + 0.35), min(1.0, b + 0.35))
            if highlight:
                return (min(1.0, r + 0.25), min(1.0, g + 0.25), min(1.0, b + 0.25))
            return (r, g, b)

        # front (0)
        c = col(self.emotions[0]["color"], highlight=(self.hover_face == 0), selected=(self.selected_face == 0))
        glColor3f(*c)
        glVertex3f(-1, -1, 1)
        glVertex3f(1, -1, 1)
        glVertex3f(1, 1, 1)
        glVertex3f(-1, 1, 1)

        # back (1)
        c = col(self.emotions[1]["color"], highlight=(self.hover_face == 1), selected=(self.selected_face == 1))
        glColor3f(*c)
        glVertex3f(-1, -1, -1)
        glVertex3f(-1, 1, -1)
        glVertex3f(1, 1, -1)
        glVertex3f(1, -1, -1)

        # top (2)
        c = col(self.emotions[2]["color"], highlight=(self.hover_face == 2), selected=(self.selected_face == 2))
        glColor3f(*c)
        glVertex3f(-1, 1, -1)
        glVertex3f(-1, 1, 1)
        glVertex3f(1, 1, 1)
        glVertex3f(1, 1, -1)

        # bottom (3)
        c = col(self.emotions[3]["color"], highlight=(self.hover_face == 3), selected=(self.selected_face == 3))
        glColor3f(*c)
        glVertex3f(-1, -1, -1)
        glVertex3f(1, -1, -1)
        glVertex3f(1, -1, 1)
        glVertex3f(-1, -1, 1)

        # left (4)
        c = col(self.emotions[4]["color"], highlight=(self.hover_face == 4), selected=(self.selected_face == 4))
        glColor3f(*c)
        glVertex3f(-1, -1, -1)
        glVertex3f(-1, -1, 1)
        glVertex3f(-1, 1, 1)
        glVertex3f(-1, 1, -1)

        # right (5)
        c = col(self.emotions[5]["color"], highlight=(self.hover_face == 5), selected=(self.selected_face == 5))
        glColor3f(*c)
        glVertex3f(1, -1, -1)
        glVertex3f(1, 1, -1)
        glVertex3f(1, 1, 1)
        glVertex3f(1, -1, 1)

        glEnd()

    # Interaction: dragging, hover, click
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.mouse_moved_while_dragging = False
            self.last_mouse_pos = event.pos()
            # capture for possible drag; do not open dialog here
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging:
            dx = event.x() - self.last_mouse_pos.x()
            dy = event.y() - self.last_mouse_pos.y()
            self.rot_y += dx * 0.5
            self.rot_x += dy * 0.5
            self.rot_x = max(-89.9, min(89.9, self.rot_x))
            self.last_mouse_pos = event.pos()
            self.mouse_moved_while_dragging = True
            self.update()
            # optionally update hover during dragging (expensive) — uncomment if needed:
            # x = event.x(); y = self.height() - event.y(); self.hover_face = self.detect_face(x, y)
        else:
            # hover behavior when not dragging
            x = event.x()
            y = self.height() - event.y()
            face = self.detect_face(x, y)
            if face != self.hover_face:
                self.hover_face = face
                self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            # if mouse wasn't moved significantly, interpret as click
            if not self.mouse_moved_while_dragging:
                x = event.x()
                y = self.height() - event.y()
                face = self.detect_face(x, y)
                if face is not None:
                    self.selected_face = face
                    print(f"Клик по грани: {face}")
                    text, ok = QInputDialog.getText(self, f"{self.emotions[face]['name']}", "Введи мысль")
                    if ok and text:
                        self.emotions[face]["notes"].append(text)
                        print(f"Добавлено в {self.emotions[face]['name']}: {text}")
                    self.update()
                else:
                    self.selected_face = None
                    print("Грань не определена")
            self.mouse_moved_while_dragging = False
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta().y() / 120.0
        self.cam_dist = max(3.0, min(20.0, self.cam_dist - delta))
        self.update()

    # Picking: reliable ray-AABB + determine face by hit point
    def detect_face(self, x, y):
        if not (0 <= x < self.width() and 0 <= y < self.height()):
            return None
        if self._modelview is None or self._projection is None or self._viewport is None:
            return None

        modelview = self._modelview
        projection = self._projection
        viewport = self._viewport

        try:
            start = gluUnProject(x, y, 0.0, modelview, projection, viewport)
            end = gluUnProject(x, y, 1.0, modelview, projection, viewport)
        except Exception as e:
            # fallback safety
            return None

        ro = np.array(start, dtype=np.float64)
        rd = np.array(end, dtype=np.float64) - ro
        norm = np.linalg.norm(rd)
        if norm < 1e-12:
            return None
        rd /= norm

        box_min = np.array([-1.0, -1.0, -1.0], dtype=np.float64)
        box_max = np.array([1.0, 1.0, 1.0], dtype=np.float64)

        tmin = -np.inf
        tmax = np.inf
        for i in range(3):
            if abs(rd[i]) < 1e-12:
                if ro[i] < box_min[i] or ro[i] > box_max[i]:
                    return None
            else:
                invd = 1.0 / rd[i]
                t1 = (box_min[i] - ro[i]) * invd
                t2 = (box_max[i] - ro[i]) * invd
                if t1 > t2:
                    t1, t2 = t2, t1
                if t1 > tmin:
                    tmin = t1
                if t2 < tmax:
                    tmax = t2
                if tmin > tmax:
                    return None

        if tmax < 0:
            return None

        t_hit = tmin if tmin >= 0 else tmax
        if t_hit < 0:
            return None

        P = ro + t_hit * rd
        abs_coords = np.abs(P)
        idx = int(np.argmax(abs_coords))  # 0->x,1->y,2->z
        coord_val = P[idx]
        eps = 1e-6

        if idx == 0:
            if coord_val >= 1.0 - eps:
                return 5
            if coord_val <= -1.0 + eps:
                return 4
        elif idx == 1:
            if coord_val >= 1.0 - eps:
                return 2
            if coord_val <= -1.0 + eps:
                return 3
        else:
            if coord_val >= 1.0 - eps:
                return 0
            if coord_val <= -1.0 + eps:
                return 1
        return None


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Emotion Cube")
        self.setGeometry(200, 200, 900, 650)

        central = QWidget()
        main_layout = QHBoxLayout()
        central.setLayout(main_layout)

        self.cube = EmotionCube()
        main_layout.addWidget(self.cube, 3)

        side = QVBoxLayout()
        main_layout.addLayout(side, 1)

        self.selected_label = QLabel("Выбранная грань: —")
        side.addWidget(self.selected_label)

        self.notes_list = QListWidget()
        side.addWidget(self.notes_list)

        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText("Новая заметка...")
        side.addWidget(self.note_input)

        add_btn = QPushButton("Добавить заметку")
        add_btn.clicked.connect(self.add_note_from_panel)
        side.addWidget(add_btn)

        export_btn = QPushButton("Экспорт мыслей")
        export_btn.clicked.connect(self.cube.export_notes)
        side.addWidget(export_btn)

        load_btn = QPushButton("Импорт JSON")
        load_btn.clicked.connect(self.import_json)
        side.addWidget(load_btn)

        delete_btn = QPushButton("Удалить выбранную заметку")
        delete_btn.clicked.connect(self.delete_selected_note)
        side.addWidget(delete_btn)

        clear_sel_btn = QPushButton("Очистить выбор")
        clear_sel_btn.clicked.connect(self.clear_selection)
        side.addWidget(clear_sel_btn)

        side.addStretch(1)

        self.setCentralWidget(central)

        # connect signal for immediate sync
        self.cube.selectedFaceChanged.connect(self.on_selected_face_changed)

    def on_selected_face_changed(self, fid_int):
        if fid_int == -1:
            self.selected_label.setText("Выбранная грань: —")
            self.notes_list.clear()
            return
        fid = int(fid_int)
        name = self.cube.emotions[fid]["name"]
        self.selected_label.setText(f"Выбранная грань: {name}")
        self.notes_list.clear()
        for note in self.cube.emotions[fid]["notes"]:
            self.notes_list.addItem(note)

    def add_note_from_panel(self):
        fid = self.cube.selected_face
        if fid is None:
            return
        text = self.note_input.text().strip()
        if not text:
            return
        self.cube.emotions[fid]["notes"].append(text)
        self.note_input.clear()
        self.on_selected_face_changed(fid)
        self.cube.update()

    def delete_selected_note(self):
        fid = self.cube.selected_face
        if fid is None:
            return
        row = self.notes_list.currentRow()
        if row >= 0:
            try:
                del self.cube.emotions[fid]["notes"][row]
            except Exception:
                pass
            self.on_selected_face_changed(fid)
            self.cube.update()

    def clear_selection(self):
        self.cube.selected_face = None

    def import_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "Импорт эмоций", "", "JSON Files (*.json);;All Files (*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for face_id, info in data.items():
                fid = int(face_id)
                if fid in self.cube.emotions:
                    new_notes = info.get("notes", [])
                    if isinstance(new_notes, list):
                        self.cube.emotions[fid]["notes"].extend(new_notes)
            cur = self.cube.selected_face
            if cur is None:
                self.on_selected_face_changed(-1)
            else:
                self.on_selected_face_changed(cur)
            print("Импорт завершён")
        except Exception as e:
            print(f"Ошибка импорта: {e}")

    def closeEvent(self, event):
        self.cube.save_emotions()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
