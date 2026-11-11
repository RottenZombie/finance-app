from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtWidgets import QGraphicsDropShadowEffect
from PySide6.QtCore import QPropertyAnimation


class Card(QFrame):
    def __init__(self, title, subtitle=None):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setSpacing(5)

        self.title = QLabel(title)
        self.title.setObjectName("currencyCardTitle")
        layout.addWidget(self.title)

        self.subtitle = QLabel(str(subtitle or ""))
        self.subtitle.setObjectName("currencyCardSubtitle")
        if subtitle:
            layout.addWidget(self.subtitle)
        else:
            self.subtitle.hide()

        self.value = QLabel("...")
        self.value.setObjectName("currencyCardValue")
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
                    background:#1a2740;
                    border:1px solid #477fce;
                    border-radius:10px;
                    padding:10px;
                }
                QLabel#currencyCardTitle { color:#ffffff; font-size:13px; font-weight:800; }
                QLabel#currencyCardSubtitle { color:#a9bfdc; font-size:9px; font-weight:500; }
                QLabel#currencyCardValue { color:#f8fbff; font-size:17px; font-weight:750; }
            """)
        elif theme == "White":
            self.setStyleSheet("""
                QFrame {
                    background:#ffffff;
                    border:1px solid #cbd5e1;
                    border-radius:10px;
                    padding:10px;
                }
                QLabel#currencyCardTitle { color:#10213b; font-size:13px; font-weight:800; }
                QLabel#currencyCardSubtitle { color:#66758a; font-size:9px; font-weight:500; }
                QLabel#currencyCardValue { color:#172033; font-size:17px; font-weight:750; }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background:#202a38;
                    border:1px solid #46566d;
                    border-radius:10px;
                    padding:10px;
                }
                QLabel#currencyCardTitle { color:#ffffff; font-size:13px; font-weight:800; }
                QLabel#currencyCardSubtitle { color:#aebbd0; font-size:9px; font-weight:500; }
                QLabel#currencyCardValue { color:#f4f7fb; font-size:17px; font-weight:750; }
            """)
