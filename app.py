import sys
import ctypes
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from core.resources import resource_path
from ui.main_window import MainWindow


def set_windows_app_user_model_id() -> None:
    """Give Windows a stable app identity so taskbar grouping uses our icon."""
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "RottenZombie.FinanceTerminal"
            )
        except (AttributeError, OSError):
            # Window and executable icons are still set below as a fallback.
            pass


set_windows_app_user_model_id()
app = QApplication(sys.argv)
app.setApplicationName("FinanceTerminal")
app.setApplicationDisplayName("FinanceTerminal")
app.setOrganizationName("RottenZombie")
app.setQuitOnLastWindowClosed(False)
app.setWindowIcon(QIcon(str(resource_path("assets/finance_terminal.png"))))

w = MainWindow()
w.setWindowIcon(QIcon(str(resource_path("assets/finance_terminal.png"))))

# FinanceTerminal 2.2.8-dev: optional GitHub Releases updater.
w.resize(1100, 760)
w.show()

sys.exit(app.exec())
