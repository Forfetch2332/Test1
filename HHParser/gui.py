import sys
import webbrowser
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QTableWidget, QTableWidgetItem
)
from PyQt5.QtWidgets import QHeaderView
from hh_api import search_vacancies
from storage import save_to_csv, save_to_json


class HHParserApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HH.ru Parser")
        self.setGeometry(200, 200, 900, 600)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Панель поиска
        row = QHBoxLayout()
        layout.addLayout(row)

        row.addWidget(QLabel("Запрос"))
        self.query_edit = QLineEdit()
        row.addWidget(self.query_edit)

        row.addWidget(QLabel("Регион"))
        self.area_box = QComboBox()
        self.area_box.addItem("Москва", 1)
        self.area_box.addItem("СПб", 2)
        self.area_box.addItem("Беларусь", 16)
        row.addWidget(self.area_box)

        self.search_button = QPushButton("Поиск")
        self.search_button.clicked.connect(self.run_search)
        row.addWidget(self.search_button)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Название", "Компания", "Зарплата", "Ссылка"])
        layout.addWidget(self.table)

        # Авто‑подстройка ширины колонок
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)

        # Обработчик клика по ячейке
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

        self.vacancies = []

    def run_search(self):
        query = self.query_edit.text().strip()
        area = self.area_box.currentData()
        self.vacancies = search_vacancies(query, area=area, pages=2)

        self.table.setRowCount(len(self.vacancies))
        for row, v in enumerate(self.vacancies):
            self.table.setItem(row, 0, QTableWidgetItem(str(v.get("title", ""))))
            self.table.setItem(row, 1, QTableWidgetItem(str(v.get("company", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(str(v.get("salary", ""))))
            self.table.setItem(row, 3, QTableWidgetItem(str(v.get("link", ""))))

        self.table.resizeRowsToContents()

    def open_link(self, row, column):
        if column == 3:  # колонка "Ссылка"
            item = self.table.item(row, column)
            if item:
                link = item.text()
                if link.startswith("http"):
                    webbrowser.open(link)

    def save_csv(self):
        if self.vacancies:
            save_to_csv(self.vacancies)
        else:
            print("Нет данных для сохранения")

    def save_json(self):
        if self.vacancies:
            save_to_json(self.vacancies)
        else:
            print("Нет данных для сохранения")


def main():
    app = QApplication(sys.argv)
    w = HHParserApp()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
