# gui.py
import sys
import webbrowser
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QTableWidget, QTableWidgetItem
)
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtCore import Qt

# Импортируй свои клиенты/хранилища
from api_clients.hh_client import search_vacancies
from api_clients.remoteok_client import search_remoteok
from storage import save_to_csv, save_to_json


def safe_str(value, max_len=300):
    """Безопасное преобразование значения в строку для таблицы."""
    if value is None:
        return "—"
    # Преобразуем списки/словаря в строку (обрезаем)
    try:
        if isinstance(value, (list, dict)):
            s = str(value)
        else:
            s = str(value)
    except Exception:
        # На случай необычных объектов
        s = repr(value)
    # Убираем управляющие символы
    s = s.replace("\r", " ").replace("\n", " ").replace("\t", " ").strip()
    if len(s) > max_len:
        s = s[:max_len] + "…"
    return s


def normalize_link(u):
    """Гарантируем, что ссылка безопасна и имеет http/https или заменяем на '-'."""
    if not u:
        return "-"
    try:
        s = str(u).strip()
    except Exception:
        return "-"
    if s.startswith("//"):
        s = "https:" + s
    if s.startswith("/"):
        s = "https://remoteok.com" + s
    if s.lower().startswith(("http://", "https://")):
        return s
    return "-"


class FreelanceHelper(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Freelance Helper")
        self.setGeometry(200, 200, 1000, 650)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Панель поиска
        row = QHBoxLayout()
        layout.addLayout(row)

        row.addWidget(QLabel("Запрос:"))
        self.query_edit = QLineEdit()
        row.addWidget(self.query_edit)

        row.addWidget(QLabel("Платформа:"))
        self.platform_box = QComboBox()
        self.platform_box.addItem("hh.ru", "hh")
        self.platform_box.addItem("remoteok", "ro")
        self.platform_box.addItem("WeWorkRemotely", "wwr")

        row.addWidget(self.platform_box)

        self.search_button = QPushButton("Поиск")
        self.search_button.clicked.connect(self.run_search)
        row.addWidget(self.search_button)

        # Таблица результатов
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Название", "Компания", "Зарплата", "Ссылка"])
        layout.addWidget(self.table)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)

        # Стабильные настройки
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.table.cellClicked.connect(self.open_link)

        # Кнопки сохранения
        save_row = QHBoxLayout()
        layout.addLayout(save_row)

        self.save_csv_btn = QPushButton("Сохранить CSV")
        self.save_csv_btn.clicked.connect(self.save_csv)
        save_row.addWidget(self.save_csv_btn)

        self.save_json_btn = QPushButton("Сохранить JSON")
        self.save_json_btn.clicked.connect(self.save_json)
        save_row.addWidget(self.save_json_btn)

        self.results = []

    def run_search(self):
        query = self.query_edit.text().strip()
        platform = self.platform_box.currentData()

        # Получаем данные из выбранной платформы
        try:
            if platform == "hh":
                self.results = search_vacancies(query, area=1, pages=2) or []
            elif platform == "ro":
                self.results = search_remoteok(query) or []
            elif platform == "wwr":
                from api_clients.wework_client import search_weworkremotely
                self.results = search_weworkremotely(query, limit=100)

            else:
                self.results = []
        except Exception as e:
            print(f"[ERROR] fetch data failed: {e}")
            self.results = []

        print("DEBUG results count:", len(self.results))

        # Ограничим размер выдачи для стабильности GUI
        MAX_ROWS = 200
        if len(self.results) > MAX_ROWS:
            self.results = self.results[:MAX_ROWS]
            print(f"[INFO] trimming results to first {MAX_ROWS} rows for stability")

        # Отключим сигнал клика на время наполнения (защита от гонок)
        try:
            self.table.cellClicked.disconnect(self.open_link)
        except Exception:
            pass

        # Очистка и подготовка таблицы
        self.table.clearContents()
        self.table.setRowCount(len(self.results))

        # Наполнение таблицы с жёсткой защитой
        for row, v in enumerate(self.results):
            # Нормализация полей
            try:
                title = safe_str(v.get("title") or v.get("position") or v.get("name"), max_len=300)
            except Exception:
                title = "—"
            try:
                company = safe_str(v.get("company") or v.get("employer") or v.get("company_name"), max_len=200)
            except Exception:
                company = "—"
            try:
                salary = safe_str(v.get("salary") or v.get("budget") or v.get("payment"), max_len=200)
            except Exception:
                salary = "—"
            try:
                raw_link = v.get("link") or v.get("url") or v.get("apply_url") or v.get("company_url")
                link = normalize_link(raw_link)
            except Exception:
                link = "-"

            # Лог до вставки — помогает локализовать проблему
            print(f"INSERT ROW {row:04d}: title={repr(title)[:160]} | company={repr(company)[:100]} | salary={repr(salary)[:60]} | link={repr(link)[:200]}")

            # Создание и вставка элементов в try/except
            try:
                item_title = QTableWidgetItem(title)
                item_company = QTableWidgetItem(company)
                item_salary = QTableWidgetItem(salary)
                item_link = QTableWidgetItem(link)

                for it in (item_title, item_company, item_salary, item_link):
                    it.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

                self.table.setItem(row, 0, item_title)
                self.table.setItem(row, 1, item_company)
                self.table.setItem(row, 2, item_salary)
                self.table.setItem(row, 3, item_link)

            except Exception as e_item:
                # В случае ошибки логируем и ставим плейсхолдеры
                print(f"[ERROR] setItem failed at row {row}: {e_item}")
                for col in range(4):
                    try:
                        ph = QTableWidgetItem("—")
                        ph.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                        self.table.setItem(row, col, ph)
                    except Exception as ee:
                        print(f"[ERROR] placeholder setItem failed at row {row} col {col}: {ee}")

        # Избегаем вызовов resizeRowsToContents, оставляем безопасные resizeColumnToContents
        try:
            self.table.resizeColumnToContents(0)
            self.table.resizeColumnToContents(1)
            self.table.resizeColumnToContents(2)
            self.table.resizeColumnToContents(3)
        except Exception as e:
            print(f"[WARN] resizeColumnToContents failed: {e}")

        # Восстанавливаем обработчик клика
        try:
            self.table.cellClicked.connect(self.open_link)
        except Exception:
            pass

    def open_link(self, row, column):
        if column != 3:
            return
        item = self.table.item(row, column)
        if not item:
            return
        link = item.text().strip()
        if not link or not link.lower().startswith(("http://", "https://")):
            print(f"[INFO] invalid link clicked: {link}")
            return
        try:
            webbrowser.open(link)
        except Exception as e:
            print(f"[ERROR] webbrowser.open failed: {e}")

    def save_csv(self):
        if self.results:
            try:
                save_to_csv(self.results)
                print("CSV сохранён")
            except Exception as e:
                print(f"[ERROR] save_to_csv failed: {e}")
        else:
            print("Нет данных для сохранения")

    def save_json(self):
        if self.results:
            try:
                save_to_json(self.results)
                print("JSON сохранён")
            except Exception as e:
                print(f"[ERROR] save_to_json failed: {e}")
        else:
            print("Нет данных для сохранения")


def main():
    app = QApplication(sys.argv)
    w = FreelanceHelper()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
