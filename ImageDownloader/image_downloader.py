import os
import sys
import threading
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTimeEdit, QFileDialog,
    QProgressBar, QCheckBox, QMessageBox, QTextEdit
)

VALID_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp",".svg"}
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
)

def sanitize_filename(name: str) -> str:
    bad = '<>:"/\\|?*'
    for ch in bad:
        name = name.replace(ch, "_")
    return name

class DownloaderSignals(QObject):
    log = pyqtSignal(str)
    progress = pyqtSignal(int)
    done = pyqtSignal(int, int)

class ImageDownloaderThread(threading.Thread):
    def __init__(self, url: str, folder: str, include_query: bool, min_side: int, signals: DownloaderSignals):
        super().__init__(daemon=True)
        self.url = url
        self.folder = folder
        self.include_query = include_query
        self.min_side = min_side
        self.signals = signals
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            headers = {"User-Agent": DEFAULT_USER_AGENT}
            resp = requests.get(self.url, headers=headers, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            self.signals.log.emit(f"[Error] Не удалось загрузить страницу: {e}")
            self.signals.done.emit(0, 1)
            return

        soup = BeautifulSoup(resp.content, "lxml") if resp.text else BeautifulSoup(resp.content, "html.parser")

        candidates = []
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data - original")
            if not src:
                continue
            candidates.append(src)

        for a in soup.find_all("a"):
            href = a.get("href")
            if not href:
                continue
            lower = href.lower()
            if any(lower.endswith(ext) for ext in VALID_EXTS):
                candidates.append(href)

        if not candidates:
            self.signals.log.emit(f"[Info] На странице не найдено изображений")
            self.signals.done.emit(0, 0)
            return

        urls = []
        for raw in candidates:
            if self._stop:
                break
            full = urljoin(self.url, raw)
            parsed = urlparse(full)

            if parsed.scheme not in ["http", "https"]:
                continue
            path = parsed.path
            ext = os.path.splitext(path)[1].lower()
            if not ext and ".svg" in full:
                ext = ".svg"
            if ext and ext in VALID_EXTS:
                if not self.include_query:
                    full = parsed.scgeme + "://" + parsed.netloc + parsed.path
                urls.append((full, ext))

        urls = list(dict.fromkeys(urls))
        total = len(urls)
        if total == 0:
            self.signals.log.emit(f"[Info] Нет вфлидных ссылок")
            self.signals.done.emit(0, 0)
            return

        os.makedirs(self.folder, exist_ok=True)
        success = 0
        fail = 0

        for i, (img_url, ext) in enumerate(urls, start=1):
            if self._stop:
                break

            try:
                r = requests.get(img_url, headers={"User-Agent": DEFAULT_USER_AGENT}, timeout=30, stream=True)
                r.raise_for_status()
                content = r.content
                if self.min_side > 0 and len(content) < max(800, self.min_side * 4):
                    self.signals.log.emit(f"[Пропуск] Слишком маленький файл: {img_url} ({len(content)} байт)")
                    fail += 1
                    self.signals.progress.emit(int(i/total*100))
                    continue
                ts = time.strftime("%Y%m%d%H%M%S")
                base = sanitize_filename(os.path.basename(urlparse(img_url).path)) or f"image_{i}{ext}"
                filename = os.path.join(self.folder, f"{ts}_{i}_{base}")
                with open(filename, "wb") as f:
                    f.write(content)
                success += 1
                self.signals.log.emit(f"[OK] Downloaded: {filename}")
            except Exception as e:
                fail += 1
                self.signals.log.emit(f"[Error] {img_url}: {e}")

            self.signals.progress.emit(int(i/total*100))

        self.signals.done.emit(success, fail)

class ImageDownloaderWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Downloader")
        self.setFixedSize(640, 440)
        self._thread = None
        self._signals = DownloaderSignals()

        central = QWidget(self)
        self.setCentralWidget(central)
        v = QVBoxLayout(central)

        url_row = QHBoxLayout()
        v.addLayout(url_row)
        url_row.addWidget(QLabel("URL страницы: "))
        self.url_edit = QLineEdit(self)
        self.url_edit.setPlaceholderText("https://example.com/article")
        url_row.addWidget(self.url_edit)

        folder_row = QHBoxLayout()
        v.addLayout(folder_row)
        folder_row.addWidget(QLabel("Папка сохранения:"))
        self.folder_edit = QLineEdit(self)
        self.folder_edit.setPlaceholderText("Выьери папку...")
        folder_row.addWidget(self.folder_edit)
        choose_btn = QPushButton("Выбрать...", self)
        choose_btn.clicked.connect(self.on_choose_folder)
        folder_row.addWidget(choose_btn)

        opt_row = QHBoxLayout()
        v.addLayout(opt_row)
        self.include_query_cb = QCheckBox("Сохранять query в URL (Уникальные имена)", self)
        self.include_query_cb.setChecked(False)
        opt_row.addWidget(self.include_query_cb)

        self.min_side_cb = QCheckBox("Отсеивать очень маленькте файлы (эвристика)", self)
        self.min_side_cb.setChecked(True)
        opt_row.addWidget(self.min_side_cb)

        self.progress = QProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        v.addWidget(self.progress)

        btn_row = QHBoxLayout()
        v.addLayout(btn_row)
        self.start_btn = QPushButton("Скачать", self)
        self.start_btn.clicked.connect(self.on_start)
        btn_row.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Стоп", self)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.on_stop)
        btn_row.addWidget(self.stop_btn)

        self.log = QTextEdit(self)
        self.log.setReadOnly(True)
        v.addWidget(self.log)

        self._signals.log.connect(self.append_log)
        self._signals.progress.connect(self.progress.setValue)
        self._signals.done.connect(self.on_done)

    def on_choose_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Выбери папку для сохранения")
        if d:
            self.folder_edit.setText(d)

    def validate_inputs(self):
        url = self.url_edit.text().strip()
        folder = self.folder_edit.text().strip()
        if not url or not urlparse(url).scheme in ["http", "https"]:
            QMessageBox.warning(self, "Ошибка","Введи корректный URL")
            return None
        if not folder:
            QMessageBox.warning(self, "<Ошибка>","Выбери папку для сохранения")
            return None
        return url, folder

    def on_start(self):
        inputs = self.validate_inputs()
        if not inputs:
            return

        url, folder = inputs
        include_query = self.include_query_cb.isChecked()
        min_side = 16 if self.min_side_cb.isChecked() else 0

        self.progress.setValue(0)
        self.log.clear()

        self._thread = ImageDownloaderThread(
            url = url,
            folder = folder,
            include_query = include_query,
            min_side = min_side,
            signals = self._signals
        )
        self._thread.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.append_log("[Старт] Загрузка изображений начата...")

    def on_stop(self):
        if self._thread:
            self._thread.stop()
        self.append_log("[Стоп] Остановка запрошена пользователем.")

    def on_done(self, success: int, fail: int):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._thread = None
        self.append_log("[Готово] Успех: {success}, Ошибки: {fail}")

    def append_log(self, text: str):
        self.log.append(text)


def main():
    app = QApplication(sys.argv)
    w = ImageDownloaderWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
