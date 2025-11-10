# snake.py
import sys
import random
import math
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QPainter, QColor, QFont
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QAction, QMessageBox

CELL_SIZE = 20
GRID_WIDTH = 30
GRID_HEIGHT = 20
INIT_SPEED = 150

# Particles config
MAX_PARTICLES = 60
N_PARTICLES_PER_EAT = 18
PARTICLE_MIN_SPEED = 1.0
PARTICLE_MAX_SPEED = 2.6
PARTICLE_MIN_TTL = 10   # frames
PARTICLE_MAX_TTL = 24   # frames

DIRECTIONS = {
    Qt.Key_Up: (0, -1),
    Qt.Key_Down: (0, 1),
    Qt.Key_Left: (-1, 0),
    Qt.Key_Right: (1, 0),
}

class GameState:
    RUNNING = 1
    PAUSED = 2
    GAME_OVER = 3

class Particle:
    __slots__ = ("x","y","vx","vy","life","max_life","color")
    def __init__(self, x, y, vx, vy, life, color):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.life = int(life)
        self.max_life = int(life)
        # ensure color is tuple of ints (r,g,b)
        if isinstance(color, tuple) and len(color) >= 3:
            self.color = (int(color[0]), int(color[1]), int(color[2]))
        else:
            self.color = (255, 200, 80)

    def step(self):
        # update with bounded floats
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.08
        self.life -= 1
        # sanitize values to avoid invalid floats
        if not math.isfinite(self.x): self.x = 0.0
        if not math.isfinite(self.y): self.y = 0.0
        if not math.isfinite(self.vx): self.vx = 0.0
        if not math.isfinite(self.vy): self.vy = 0.0

    def alive(self):
        return self.life > 0

class SnakeGameWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(CELL_SIZE * GRID_WIDTH, CELL_SIZE * GRID_HEIGHT)
        self.setFocusPolicy(Qt.StrongFocus)

        # interpolation
        self.prev_snake = []
        self.anim_progress = 1.0
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(16)
        self.anim_timer.timeout.connect(self._on_anim_tick)
        self.anim_timer.start()

        # apple pulse
        self.apple_phase = 0.0

        # particles
        self.particles = []

        self.timer = None
        self.reset_game()

    def reset_game(self):
        mid_x = GRID_WIDTH // 2
        mid_y = GRID_HEIGHT // 2
        self.snake = [(mid_x, mid_y), (mid_x - 1, mid_y), (mid_x - 2, mid_y)]
        self.direction = (1, 0)
        self.next_direction = self.direction
        self.spawn_food()
        self.score = 0
        self.speed = INIT_SPEED
        self.state = GameState.RUNNING

        self.prev_snake = list(self.snake)
        self.anim_progress = 1.0
        self.apple_phase = 0.0
        self.particles.clear()

        if self.timer:
            try:
                self.timer.stop()
            except Exception:
                pass
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.game_step)
        self.timer.start(self.speed)

        self.setFocus()

    def spawn_food(self):
        empty = {(x, y) for x in range(GRID_WIDTH) for y in range(GRID_HEIGHT)} - set(self.snake)
        self.food = random.choice(list(empty)) if empty else None

    def _on_anim_tick(self):
        # interpolation progress
        if self.anim_progress < 1.0:
            step = 16.0 / max(80.0, float(getattr(self, "speed", INIT_SPEED)))
            self.anim_progress = min(1.0, self.anim_progress + step)
        # apple pulse
        self.apple_phase = (getattr(self, "apple_phase", 0.0) + 0.12) % (2 * math.pi)

        # update particles safely by building new list
        if self.particles:
            new_particles = []
            for p in self.particles:
                p.step()
                if p.alive():
                    new_particles.append(p)
            # replace list reference
            self.particles = new_particles

        # request repaint
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.fillRect(self.rect(), QColor(10, 10, 10))

        # grid
        pen_color = QColor(28, 28, 28)
        painter.setPen(pen_color)
        for x in range(0, GRID_WIDTH * CELL_SIZE, CELL_SIZE):
            painter.drawLine(x, 0, x, GRID_HEIGHT * CELL_SIZE)
        for y in range(0, GRID_HEIGHT * CELL_SIZE, CELL_SIZE):
            painter.drawLine(0, y, GRID_WIDTH * CELL_SIZE, y)

        # pulsing apple
        if self.food:
            fx, fy = self.food
            phase = self.apple_phase
            scale = 0.9 + 0.06 * math.sin(phase)
            size = max(4, int((CELL_SIZE - 4) * scale))
            rx = fx * CELL_SIZE + (CELL_SIZE - size) // 2
            ry = fy * CELL_SIZE + (CELL_SIZE - size) // 2
            # shadow
            painter.setOpacity(0.22)
            painter.setBrush(QColor(0, 0, 0))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(rx + 3, ry + size - 4, size - 6, 6)
            painter.setOpacity(1.0)
            painter.setBrush(QColor(200, 60, 60))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(rx, ry, size, size)
            # highlight
            painter.setBrush(QColor(255, 190, 190))
            painter.drawEllipse(rx + size // 6, ry + size // 6, size // 3, size // 6)
            # stem
            stem_w = max(2, size // 10)
            stem_h = max(3, size // 6)
            sx = rx + size // 2 - stem_w // 2
            sy = ry - stem_h // 2
            painter.setBrush(QColor(90, 60, 30))
            painter.drawRect(sx, sy, stem_w, stem_h)

        # draw snake (interpolated)
        n = len(self.snake)
        t = self.anim_progress
        for i in range(n):
            prev = self.prev_snake[i] if i < len(self.prev_snake) else self.snake[i]
            cur = self.snake[i]
            ix = prev[0] * (1.0 - t) + cur[0] * t
            iy = prev[1] * (1.0 - t) + cur[1] * t
            rx = int(ix * CELL_SIZE + 2)
            ry = int(iy * CELL_SIZE + 2)
            w = CELL_SIZE - 4
            h = CELL_SIZE - 4
            if i == 0:
                painter.setBrush(QColor(120, 220, 120))
                painter.setPen(Qt.NoPen)
                painter.drawRect(rx, ry, w, h)
                dx, dy = self.direction
                painter.setBrush(QColor(10,10,10))
                eye_offset = CELL_SIZE // 6
                if dx == 1:
                    painter.drawEllipse(rx + w - eye_offset*2, ry + eye_offset, 3, 3)
                    painter.drawEllipse(rx + w - eye_offset*2, ry + h - eye_offset*2, 3, 3)
                elif dx == -1:
                    painter.drawEllipse(rx + eye_offset, ry + eye_offset, 3, 3)
                    painter.drawEllipse(rx + eye_offset, ry + h - eye_offset*2, 3, 3)
                elif dy == -1:
                    painter.drawEllipse(rx + eye_offset, ry + eye_offset, 3, 3)
                    painter.drawEllipse(rx + w - eye_offset*2, ry + eye_offset, 3, 3)
                else:
                    painter.drawEllipse(rx + eye_offset, ry + h - eye_offset*2, 3, 3)
                    painter.drawEllipse(rx + w - eye_offset*2, ry + h - eye_offset*2, 3, 3)
            else:
                painter.setBrush(QColor(60, 160, 60))
                painter.setPen(Qt.NoPen)
                painter.drawRect(rx, ry, w, h)
                prev_cell = self.snake[i + 1] if i + 1 < n else self.snake[i]
                next_cell = self.snake[i - 1] if i - 1 >= 0 else self.snake[i]
                conn_r = max(4, w // 4)
                if prev_cell[0] < self.snake[i][0] or next_cell[0] < self.snake[i][0]:
                    painter.drawEllipse(rx - conn_r//2, ry + h//2 - conn_r//2, conn_r, conn_r)
                if prev_cell[0] > self.snake[i][0] or next_cell[0] > self.snake[i][0]:
                    painter.drawEllipse(rx + w - conn_r//2, ry + h//2 - conn_r//2, conn_r, conn_r)
                if prev_cell[1] < self.snake[i][1] or next_cell[1] < self.snake[i][1]:
                    painter.drawEllipse(rx + w//2 - conn_r//2, ry - conn_r//2, conn_r, conn_r)
                if prev_cell[1] > self.snake[i][1] or next_cell[1] > self.snake[i][1]:
                    painter.drawEllipse(rx + w//2 - conn_r//2, ry + h - conn_r//2, conn_r, conn_r)

        # draw particles
        if self.particles:
            for p in self.particles:
                # guard values and convert color safely
                a = max(0, min(255, int(255 * (p.life / p.max_life))))
                r,g,b = p.color
                col = QColor(int(r), int(g), int(b))
                col.setAlpha(a)
                painter.setBrush(col)
                painter.setPen(Qt.NoPen)
                size = max(1, int(4 * (p.life / p.max_life)))
                # sanitize positions
                px = int(p.x) if math.isfinite(p.x) else 0
                py = int(p.y) if math.isfinite(p.y) else 0
                painter.drawEllipse(px - size//2, py - size//2, size, size)

        # overlay
        painter.setPen(QColor(220, 220, 220))
        painter.setFont(QFont("Arial", 12))
        painter.drawText(6, 18, f"Score: {self.score}")

        if self.state == GameState.PAUSED:
            painter.setFont(QFont("Arial", 32, QFont.Bold))
            painter.setPen(QColor(255, 255, 0))
            painter.drawText(self.rect(), Qt.AlignCenter, "PAUSED")
        elif self.state == GameState.GAME_OVER:
            painter.setFont(QFont("Arial", 28, QFont.Bold))
            painter.setPen(QColor(255, 80, 80))
            painter.drawText(self.rect(), Qt.AlignCenter, "GAME OVER\nPress R to restart")

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Space:
            if self.state == GameState.RUNNING:
                self.pause()
            elif self.state == GameState.PAUSED:
                self.resume()
            event.accept()
            return
        if key == Qt.Key_R and self.state == GameState.GAME_OVER:
            self.reset_game()
            self.update()
            event.accept()
            return
        if key in DIRECTIONS and self.state == GameState.RUNNING:
            dx, dy = DIRECTIONS[key]
            nx, ny = self.direction
            if (dx, dy) != (-nx, -ny):
                self.next_direction = (dx, dy)
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        self.setFocus()
        super().mousePressEvent(event)

    def pause(self):
        if self.state != GameState.RUNNING:
            return
        self.state = GameState.PAUSED
        if self.timer:
            self.timer.stop()
        self.update()

    def resume(self):
        if self.state != GameState.PAUSED:
            return
        self.state = GameState.RUNNING
        if self.timer:
            self.timer.start(self.speed)
        self.setFocus()
        self.update()

    def change_speed(self, delta_ms):
        new_speed = max(30, self.speed + delta_ms)
        self.speed = new_speed
        if self.state == GameState.RUNNING and self.timer:
            self.timer.start(self.speed)

    def game_step(self):
        self.prev_snake = list(self.snake)

        self.direction = self.next_direction
        hx, hy = self.snake[0]
        dx, dy = self.direction
        new_head = (hx + dx, hy + dy)

        x, y = new_head
        if not (0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT):
            self.end_game()
            return

        if new_head in self.snake:
            self.end_game()
            return

        self.snake.insert(0, new_head)
        if self.food and new_head == self.food:
            self.score += 1
            if self.score % 3 == 0:
                self.change_speed(-10)
            # spawn particles centered on eaten cell
            cx = new_head[0] * CELL_SIZE + CELL_SIZE / 2
            cy = new_head[1] * CELL_SIZE + CELL_SIZE / 2
            self._spawn_particles(cx, cy)
            self.spawn_food()
        else:
            self.snake.pop()

        self.anim_progress = 0.0

    def _spawn_particles(self, cx, cy):
        # limit total particles
        space = MAX_PARTICLES - len(self.particles)
        if space <= 0:
            return
        count = min(space, N_PARTICLES_PER_EAT)
        colors = [(255,200,80), (255,140,80), (255,90,90), (255,220,120)]
        for _ in range(count):
            ang = random.random() * 2 * math.pi
            speed = random.uniform(PARTICLE_MIN_SPEED, PARTICLE_MAX_SPEED)
            vx = math.cos(ang) * speed
            vy = math.sin(ang) * speed - random.uniform(0.6, 1.4)
            ttl = random.randint(PARTICLE_MIN_TTL, PARTICLE_MAX_TTL)
            col = random.choice(colors)
            p = Particle(cx + random.uniform(-3,3), cy + random.uniform(-3,3), vx, vy, ttl, col)
            self.particles.append(p)

    def end_game(self):
        self.state = GameState.GAME_OVER
        try:
            if self.timer:
                self.timer.stop()
        except Exception:
            pass
        self.update()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Snake — Particles Fixed")
        self.game_widget = SnakeGameWidget(self)
        self.setCentralWidget(self.game_widget)
        self.create_actions()
        self.create_menu()
        self.statusBar().showMessage("Space — pause/resume | R — restart | Arrows — move")
        self.game_widget.setFocus()

    def create_actions(self):
        self.exit_action = QAction("Exit", self)
        self.exit_action.triggered.connect(self.close)

        self.pause_action = QAction("Pause/Resume", self)
        self.pause_action.setShortcut("Space")
        self.pause_action.triggered.connect(self.toggle_pause)

        self.restart_action = QAction("Restart", self)
        self.restart_action.setShortcut("R")
        self.restart_action.triggered.connect(self.restart)

        self.speed_up_action = QAction("Speed Up", self)
        self.speed_up_action.setShortcut("+")
        self.speed_up_action.triggered.connect(lambda: self.game_widget.change_speed(-20))

        self.slow_down_action = QAction("Slow Down", self)
        self.slow_down_action.setShortcut("-")
        self.slow_down_action.triggered.connect(lambda: self.game_widget.change_speed(20))

    def create_menu(self):
        menu = self.menuBar().addMenu("Game")
        menu.addAction(self.pause_action)
        menu.addAction(self.restart_action)
        menu.addSeparator()
        menu.addAction(self.speed_up_action)
        menu.addAction(self.slow_down_action)
        menu.addSeparator()
        menu.addAction(self.exit_action)

    def toggle_pause(self):
        if self.game_widget.state == GameState.RUNNING:
            self.game_widget.pause()
        elif self.game_widget.state == GameState.PAUSED:
            self.game_widget.resume()

    def restart(self):
        confirm = QMessageBox.question(self, "Restart", "Restart the game?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            self.game_widget.reset_game()
            self.game_widget.update()
            self.game_widget.setFocus()

def main():
    app = QApplication(sys.argv)
    wnd = MainWindow()
    wnd.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
