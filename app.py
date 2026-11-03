import sys
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow

app = QApplication(sys.argv)
app.setApplicationName("FinanceTerminal")

w = MainWindow()

# FinanceTerminal 2.2.0: the BIST tab needs a wider workspace.
w.resize(1100, 760)
w.show()

sys.exit(app.exec())
