import sys
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtWidgets import QPushButton

# Создаём приложение
app = QApplication(sys.argv)

# Создаём окно
окно = QWidget()
окно.setWindowTitle("Привет, Максим!")
окно.resize(300, 100)

# Добавляем текст
метка = QLabel("Это твоё первое окно на PyQt!", окно)
метка.move(50, 40)

# Кнопка
кнопка = QPushButton("Нажми меня", окно)
кнопка.move(100, 60)

# Обработчик нажатия
def при_нажатии():
    метка.setText("Ты нажал кнопку!")

кнопка.clicked.connect(при_нажатии)

# Показываем окно
окно.show()

# Запускаем цикл обработки событий
sys.exit(app.exec_())
