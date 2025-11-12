from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QSizePolicy, QHBoxLayout
)
from typing import List
import resource_helper as rh


class HintsRenderer(QWidget):
    """
    Компактный виджет для подсказок.
    По умолчанию свернут; кнопка раскрывает/скрывает.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        header_layout = QHBoxLayout()
        self.header = QLabel("Подсказки")
        self.toggle_btn = QPushButton("Показать")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(False)
        self.toggle_btn.clicked.connect(self._on_toggle)

        header_layout.addWidget(self.header)
        header_layout.addStretch(1)
        header_layout.addWidget(self.toggle_btn)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setPlaceholderText("Подсказки появятся здесь, если они есть")

        layout.addLayout(header_layout)
        layout.addWidget(self.text)

        # скрываем содержимое подсказок по умолчанию (только заголовок и кнопка видимы)
        self.header.setVisible(True)
        self.toggle_btn.setVisible(True)
        self.text.setVisible(False)

        self.text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.text.setMinimumHeight(140)
        self.setMinimumWidth(260)

    def show_hints(self, hints: List[str]) -> None:
        if hints:
            self.text.setPlainText("\n".join(hints))
            # по умолчанию кнопка в состоянии скрыто -> показываем кнопку, но контент скрыт
            self.toggle_btn.setEnabled(True)
            self.toggle_btn.setText("Показать")
            self.toggle_btn.setChecked(False)
            self.text.setVisible(False)
            rh.log(f"HintsRenderer: prepared {len(hints)} hints")
        else:
            self.clear()

    def clear(self) -> None:
        self.text.clear()
        self.toggle_btn.setEnabled(False)
        self.text.setVisible(False)
        self.toggle_btn.setChecked(False)
        self.toggle_btn.setText("Показать")
        rh.log("HintsRenderer: cleared")

    def _on_toggle(self, checked: bool):
        if checked:
            self.text.setVisible(True)
            self.toggle_btn.setText("Скрыть")
        else:
            self.text.setVisible(False)
            self.toggle_btn.setText("Показать")
