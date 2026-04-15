from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtWidgets import QGraphicsDropShadowEffect
from PySide6.QtCore import QPropertyAnimation


class Card(QFrame):
    def __init__(self, title):
        super().__init__()

        layout = QVBoxLayout(self)

        self.title = QLabel(title)
        self.value = QLabel("...")

        layout.addWidget(self.title)
        layout.addWidget(self.value)

    def flash(self):
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(200)
        self.anim.setStartValue(0.6)
        self.anim.setEndValue(1.0)
        self.anim.start()

    def highlight(self):
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(20)
        effect.setXOffset(0)
        effect.setYOffset(0)
        effect.setColor("#3a86ff")
        self.setGraphicsEffect(effect)

    def apply_theme(self, theme):
        if theme == "Blue":
            self.setStyleSheet("""
                QFrame {
                    background:#1a1f2e;
                    border:1px solid #3a86ff;
                    border-radius:10px;
                    padding:10px;
                }
                QLabel { color:white; }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background:#2a2a2a;
                    border-radius:10px;
                    padding:10px;
                }
                QLabel { color:white; }
            """)