import sys
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow

app = QApplication(sys.argv)

w = MainWindow()

# ✅ OTOMATİK EKRANA OTURTMA (fullscreen değil)
w.resize(400, 500)
w.show()

sys.exit(app.exec())