import sys
import ctypes
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from core.resources import resource_path
from core.single_instance import SingleInstance
from ui.main_window import MainWindow


def set_windows_app_user_model_id() -> None:
    """Give Windows a stable app identity so taskbar grouping uses our icon."""
    if sys.platform == "win32":
        try:
            # Use the product name as the Windows notification identity so
            # notifications no longer display the publisher prefix.
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "FinanceTerminal"
            )
        except (AttributeError, OSError):
            # Window and executable icons are still set below as a fallback.
            pass


set_windows_app_user_model_id()
app = QApplication(sys.argv)
app.setApplicationName("FinanceTerminal")
app.setApplicationDisplayName("FinanceTerminal")
app.setOrganizationName("")
app.setQuitOnLastWindowClosed(False)
app.setWindowIcon(QIcon(str(resource_path("assets/finance_terminal.png"))))

# A second launch wakes the existing window (including an instance in the tray)
# instead of creating a duplicate application process/window.
single_instance = SingleInstance()
if not single_instance.is_primary:
    error = getattr(single_instance, "error_string", "")
    if error:
        QMessageBox.critical(
            None,
            "FinanceTerminal başlatılamadı",
            "Tek uygulama örneği başlatılamadı. Bilgisayarınızı yeniden başlatıp tekrar deneyin.\n\n"
            + str(error),
        )
    sys.exit(0)

w = MainWindow()
w.setWindowIcon(QIcon(str(resource_path("assets/finance_terminal.png"))))
single_instance.activated.connect(w.show_from_second_instance)
# Keep the IPC server alive for the complete QApplication lifetime.
app._finance_terminal_single_instance = single_instance
app.aboutToQuit.connect(single_instance.close)

# FinanceTerminal 2.3.0-dev: selectable currencies, independent profiles and editable holdings.
w.resize(1100, 760)
w.show()

sys.exit(app.exec())
