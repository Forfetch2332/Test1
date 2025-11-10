import os
import sys
import csv
from datetime import datetime

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QSpinBox
)

CSV_FILENAME = os.path.join(
    os.path.expanduser("~"),
    "FocusTimer",
    "session.csv"
)
os.makedirs(os.path.dirname(CSV_FILENAME), exist_ok=True)

def format_elapsed(ms: int) -> str:
    seconds, millis = divmod(ms, 1000)
    minutes, secs = divmod(seconds, 60)
    hours, mins = divmod(minutes, 60)
    return f"{hours:02d}:{mins:02d}:{secs:02d}.{millis:03d}"

class FocusTimerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FocusTimer - Minimal MVP")
        self.setFixedSize(420, 260)
        self._is_running = False
        self._elapsed_ms = 0
        self._last_tick_epoch_ms = None
        self._today_saved_ms = 0   # кэш суммы сохранённых сессий за сегодня

        central = QWidget(self)
        self.setCentralWidget(central)
        vbox = QVBoxLayout(central)

        # Метка времени
        self.time_label = QLabel("00:00:00.000", self)
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet(
            "font-family: Consolas, 'Courier New', monospace; font-size: 16pt; color: #222;"
        )
        vbox.addWidget(self.time_label)

        # Поле комментария
        self.comment_edit = QLineEdit(self)
        self.comment_edit.setPlaceholderText("Comment to session (optional)")
        vbox.addWidget(self.comment_edit)

        # Цель и прогресс
        goal_layout = QHBoxLayout()
        vbox.addLayout(goal_layout)

        goal_label = QLabel("Daily goal (min):", self)
        goal_layout.addWidget(goal_label)

        self.goal_spin = QSpinBox(self)
        self.goal_spin.setRange(1, 600)
        self.goal_spin.setValue(120)
        self.goal_spin.valueChanged.connect(self._update_progress)
        goal_layout.addWidget(self.goal_spin)

        self.progress = QProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.setFormat("%p% of daily goal")
        self.progress.setTextVisible(True)
        vbox.addWidget(self.progress)

        # Кнопки
        hbox = QHBoxLayout()
        vbox.addLayout(hbox)

        self.start_btn = QPushButton("Start", self)
        self.start_btn.clicked.connect(self.on_start_clicked)
        hbox.addWidget(self.start_btn)

        self.pause_btn = QPushButton("Pause", self)
        self.pause_btn.clicked.connect(self.on_pause_clicked)
        self.pause_btn.setEnabled(False)
        hbox.addWidget(self.pause_btn)

        self.reset_btn = QPushButton("Reset", self)
        self.reset_btn.clicked.connect(self.on_reset_clicked)
        self.reset_btn.setEnabled(False)
        hbox.addWidget(self.reset_btn)

        self.stats_btn = QPushButton("Stats", self)
        self.stats_btn.clicked.connect(self.on_stats_clicked)
        hbox.addWidget(self.stats_btn)

        # Таймер
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.on_tick)

        self._ensure_csv_header()
        self._recalc_today_saved_ms()
        self._update_progress()

    # --- CSV header ---
    def _ensure_csv_header(self):
        try:
            with open(CSV_FILENAME, "a", newline="", encoding="utf-8") as f:
                if f.tell() == 0:
                    writer = csv.writer(f)
                    writer.writerow(["datetime","duration_ms","duration_str","comment"])
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    # --- UI state ---
    def _update_ui_state(self):
        self.start_btn.setEnabled(not self._is_running)
        self.pause_btn.setEnabled(self._is_running)
        self.reset_btn.setEnabled(self._elapsed_ms > 0)

    def _set_time_label(self, ms: int):
        self.time_label.setText(format_elapsed(ms))

    # --- Buttons ---
    def on_start_clicked(self):
        if self._is_running:
            return
        self._is_running = True
        self._last_tick_epoch_ms = int(datetime.now().timestamp() * 1000)
        self.timer.start()
        self._update_ui_state()
        self._update_progress()

    def on_pause_clicked(self):
        if not self._is_running:
            return
        self.timer.stop()
        self._is_running = False
        self._update_ui_state()
        self._update_progress()

    def on_reset_clicked(self):
        if self._elapsed_ms > 0:
            now_iso = datetime.now().isoformat(timespec="seconds")
            duration_ms = self._elapsed_ms
            duration_str = format_elapsed(duration_ms)
            comment = self.comment_edit.text().strip()

            try:
                with open(CSV_FILENAME, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([now_iso, duration_ms, duration_str, comment])
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))
            else:
                QMessageBox.information(self, "Saved", f"Session {duration_str} saved to {CSV_FILENAME}")

        self.timer.stop()
        self._is_running = False
        self._elapsed_ms = 0
        self._last_tick_epoch_ms = None
        self._set_time_label(0)
        self.comment_edit.clear()
        self._update_ui_state()

        # пересчёт кэша и обновление прогресса
        self._recalc_today_saved_ms()
        self._update_progress()

    def on_tick(self):
        now_epoch_ms = int(datetime.now().timestamp() * 1000)
        if self._last_tick_epoch_ms is None:
            delta = self.timer.interval()
        else:
            delta = max(0, now_epoch_ms - self._last_tick_epoch_ms)

        self._elapsed_ms += delta
        self._last_tick_epoch_ms = now_epoch_ms
        self._set_time_label(self._elapsed_ms)
        self._update_ui_state()
        self._update_progress()

    def on_stats_clicked(self):
        try:
            with open(CSV_FILENAME, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                today = datetime.now().date()
                durations = []
                for row in reader:
                    try:
                        raw_dt = row.get("datetime", "").strip()
                        if not raw_dt:
                            continue
                        dt = datetime.fromisoformat(raw_dt)
                        if dt.date() == today:
                            val = row.get("duration_ms", "").strip()
                            if val:
                                durations.append(int(float(val)))
                    except Exception:
                        continue
        except FileNotFoundError:
            QMessageBox.information(self, "Stats", "File not found")
            return
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
            return

        if not durations:
            QMessageBox.information(self, "Stats", "Сегодня ещё нет завершённых сессий")
            return

        total_ms = sum(durations)
        avg_ms = total_ms // len(durations)

        msg = (
            f"Сегодняшние сессии: {len(durations)}\n"
            f"Суммарное время: {format_elapsed(total_ms)}\n"
            f"Средняя длительность: {format_elapsed(avg_ms)}"
        )
        QMessageBox.information(self, "Stats", msg)

        # синхронизируем кэш
        self._recalc_today_saved_ms()
        self._update_progress()

    # --- Progress helpers ---
    def _recalc_today_saved_ms(self):
        total = 0
        try:
            with open(CSV_FILENAME, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                today = datetime.now().date()
                for row in reader:
                    try:
                        raw_dt = row.get("datetime", "").strip()
                        if not raw_dt:
                            continue
                        dt = datetime.fromisoformat(raw_dt)
                        if dt.date() == today:
                            val = row.get("duration_ms", "").strip()
                            if val:
                                total += int(float(val))
                    except Exception:
                        continue
        except FileNotFoundError:
            total = 0
        self._today_saved_ms = total

    def _update_progress(self):
        total_ms = self._today_saved_ms
        if self._is_running and self._elapsed_ms > 0:
            total_ms += self._elapsed_ms

        goal_minutes = self.goal_spin.value()
        goal_ms = goal_minutes * 60 * 1000
        percent = min(100, int(total_ms / goal_ms * 100)) if goal_ms > 0 else 0
        self.progress.setValue(percent)


def main():
    app = QApplication(sys.argv)
    window = FocusTimerWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

