import sys
import ctypes
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from core.autostart import AUTOSTART_FLAG
from core.log_setup import setup_logging
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


setup_logging()
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

w.resize(1100, 760)
# Started by Windows at sign-in (see Ayarlar): optionally stay in the tray, and give
# the network a moment to come up before retrying a failed first refresh.
started_by_windows = AUTOSTART_FLAG in sys.argv[1:]
if started_by_windows and w.should_start_in_tray():
    w.start_hidden_in_tray()
else:
    w.show()
if started_by_windows:
    for delay_ms in (25_000, 75_000):
        QTimer.singleShot(delay_ms, w.retry_refresh_if_offline)

sys.exit(app.exec())
