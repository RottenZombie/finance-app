from decimal import Decimal
import sys

from PySide6.QtCore import QTimer
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QComboBox, QLabel, QPushButton, QDialog, QSizePolicy,
    QFileDialog, QMessageBox, QTextBrowser, QCheckBox, QProgressDialog,
    QSystemTrayIcon, QMenu, QApplication,
)

from worker import Worker
from ui.card import Card
from features.metals import Metals
from features.portfolio import Portfolio
from features.summary import SummaryPage
from features.bist.portfolio_tab import BistPortfolioTab
from features.investment_excel import write_combined_portfolio_excel
from features.combined_import import (
    read_combined_portfolio_excel, apply_combined_portfolio_import,
)
from core.resources import resource_path
from settings import load, save, resolve_theme
from core.update_worker import UpdateCheckWorker, UpdateDownloadWorker
from core.updater import (
    UpdateError, current_executable_path, launch_windows_update_helper,
)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowIcon(QIcon(str(resource_path("assets/finance_terminal.png"))))
        self.setWindowTitle("FinanceTerminal")

        # ---------------- SETTINGS ----------------
        self.VERSION = "2.2.9-dev"
        self.settings = load()
        self.worker: Worker | None = None
        self._update_check_worker = None
        self._update_download_worker = None
        self._update_progress = None
        self._update_check_automatic = False
        self._update_check_payload = None
        self._update_download_payload = None
        self._pending_update_release = None
        self._pending_update_automatic = False
        self._close_after_update = False
        self._final_close = False
        self._force_exit = False
        self._in_tray = False
        self._tray_available = QSystemTrayIcon.isSystemTrayAvailable()
        self._tray_icon = None
        self._init_system_tray()

        # Summary was inserted at tab index 0. Migrate old saved tab indexes once.
        if not self.settings.get("summary_tab_migrated", False):
            try:
                old_index = int(self.settings.get("start_tab", 0))
            except (TypeError, ValueError):
                old_index = 0
            self.settings["start_tab"] = old_index + 1 if 0 <= old_index <= 3 else 0
            self.settings["summary_tab_migrated"] = True
            save(self.settings)

        self.theme_preference = self.settings.get("theme", "System")
        self.theme = resolve_theme(self.theme_preference)
        self.precision = self.settings.get("precision", 2)
        self.start_tab = self.settings.get("start_tab", 0)

        # ---------------- WINDOW BEHAVIOR ----------------
        self.setMinimumSize(400, 500)

        # ---------------- TABS ----------------
        self.tabs = QTabWidget()
        self.tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # ---------------- SUMMARY ----------------
        self.summary_page = SummaryPage()
        self.tabs.addTab(self.summary_page, "Summary")

        # ---------------- CURRENCY ----------------
        self.tab1 = QWidget()
        l1 = QVBoxLayout(self.tab1)

        self.usd = Card("USD/TRY")
        self.eur = Card("EUR/TRY")
        self.huf = Card("HUF/TRY")

        self.mode = QComboBox()
        self.mode.addItems(["Normal", "Ters"])
        self.mode.currentIndexChanged.connect(self.refresh)

        self.last = QLabel("-")

        self.update_button = QPushButton("Güncelle")
        self.update_button.clicked.connect(self.update)

        settings_btn = QPushButton("Ayarlar ⚙️")
        settings_btn.clicked.connect(self.open_settings)

        l1.addWidget(self.usd)
        l1.addWidget(self.eur)
        l1.addWidget(self.huf)
        l1.addWidget(self.mode)
        l1.addWidget(self.last)
        l1.addWidget(self.update_button)
        l1.addWidget(settings_btn)
        l1.addStretch()

        # ---------------- OTHER TABS ----------------
        self.portfolio = Portfolio()
        self.metals = Metals()
        self.bist_portfolio = BistPortfolioTab()

        self.tabs.addTab(self.tab1, "Currency")
        self.tabs.addTab(self.portfolio, "Portfolio")
        self.tabs.addTab(self.metals, "Metals")
        self.tabs.addTab(self.bist_portfolio, "BIST AI")

        self.portfolio.investment_panel.portfolio_changed.connect(self.refresh_summary)
        self.metals.investment_panel.portfolio_changed.connect(self.refresh_summary)
        self.bist_portfolio.portfolio_changed.connect(self.refresh_summary)

        try:
            start_index = int(self.start_tab)
        except (TypeError, ValueError):
            start_index = 0
        self.tabs.setCurrentIndex(start_index if 0 <= start_index < self.tabs.count() else 0)

        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        toolbar.addStretch(1)
        self.import_all_button = QPushButton("Tüm Portföyü Excel'den İçe Aktar")
        self.import_all_button.clicked.connect(self.import_complete_portfolio)
        toolbar.addWidget(self.import_all_button)
        self.export_all_button = QPushButton("Tüm Portföyü Excel'e Aktar")
        self.export_all_button.clicked.connect(self.export_complete_portfolio)
        toolbar.addWidget(self.export_all_button)
        layout.addLayout(toolbar)
        layout.addWidget(self.tabs)

        self.apply_theme()
        self.refresh_summary()
        self.update()
        # Startup update preference is asked only by the packaged Windows EXE.
        QTimer.singleShot(1400, self._startup_update_check)

    # ---------------- SUMMARY ----------------
    @staticmethod
    def _decimal_or_none(value):
        try:
            result = Decimal(str(value)) if value is not None else None
            return result if result is not None and result > 0 else None
        except Exception:
            return None

    def refresh_summary(self, *_args):
        rates = getattr(self, "last_data", {}) or {}
        self.summary_page.update_summary(
            currency_holdings=self.portfolio.investment_panel.store.list_holdings("currency"),
            currency_prices=self.portfolio.investment_panel.current_prices,
            metal_holdings=self.metals.investment_panel.store.list_holdings("metals"),
            metal_prices=self.metals.investment_panel.current_prices,
            bist_holdings=self.bist_portfolio.database.list_holdings(),
            try_per_usd=self._decimal_or_none(rates.get("USD")),
            try_per_eur=self._decimal_or_none(rates.get("EUR")),
        )

    # ---------------- COMBINED PORTFOLIO EXPORT ----------------
    def export_complete_portfolio(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Tüm portföyü tek Excel dosyasına aktar",
            str(Path.home() / "FinanceTerminal_Tum_Portfoy.xlsx"),
            "Excel dosyaları (*.xlsx)",
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"

        try:
            currency_panel = self.portfolio.investment_panel
            metal_panel = self.metals.investment_panel
            rates = getattr(self, "last_data", {}) or {}
            usd_rate = self._decimal_or_none(rates.get("USD"))
            eur_rate = self._decimal_or_none(rates.get("EUR"))
            write_combined_portfolio_excel(
                path,
                currency_holdings=currency_panel.store.list_holdings("currency"),
                currency_prices=currency_panel.current_prices,
                metal_holdings=metal_panel.store.list_holdings("metals"),
                metal_prices=metal_panel.current_prices,
                bist_holdings=self.bist_portfolio.database.list_holdings(),
                try_per_usd=usd_rate,
                try_per_eur=eur_rate,
                rates_updated_at=rates.get("fetched_at"),
                rates_status=rates.get("status"),
            )
            QMessageBox.information(
                self,
                "Dışa aktarma tamamlandı",
                f"Tüm portföy tek Excel dosyasına aktarıldı:\n{path}\n\n"
                "Summary, Döviz, Maden, Hisse Senedi ve Veri Bilgisi sayfaları oluşturuldu.",
            )
        except Exception as exc:
            QMessageBox.warning(self, "Dışa aktarma başarısız", str(exc))

    # ---------------- COMBINED PORTFOLIO IMPORT ----------------
    def import_complete_portfolio(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Tüm portföyün bulunduğu Excel dosyasını seç",
            str(Path.home()),
            "Excel dosyaları (*.xlsx)",
        )
        if not path:
            return

        try:
            currency_panel = self.portfolio.investment_panel
            metal_panel = self.metals.investment_panel
            imported_data = read_combined_portfolio_excel(
                path,
                currency_assets=currency_panel.assets,
                metal_assets=metal_panel.assets,
            )
        except Exception as exc:
            QMessageBox.warning(self, "Excel okunamadı", str(exc))
            return

        currency_rows = imported_data["currency"]
        metal_rows = imported_data["metals"]
        bist_rows = imported_data["bist"]
        total_rows = len(currency_rows) + len(metal_rows) + len(bist_rows)
        if total_rows == 0:
            QMessageBox.information(
                self, "İçe aktarma", "Dosyada içe aktarılabilecek portföy kaydı bulunamadı."
            )
            return

        details = (
            f"Döviz: {len(currency_rows)} kayıt\n"
            f"Maden: {len(metal_rows)} kayıt\n"
            f"Hisse senedi: {len(bist_rows)} kayıt\n\n"
            "Aynı varlık veya hisse kodu mevcutsa miktar ve ortalama maliyet Excel dosyasındaki "
            "değerlerle güncellenecek; kayıtlar ikinci kez eklenmeyecek. "
            "Dosyada bulunmayan bölümlerdeki mevcut kayıtlar korunacak.\n\nDevam edilsin mi?"
        )
        answer = QMessageBox.question(
            self, "Tüm portföyü içe aktar", details,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        counts, errors = apply_combined_portfolio_import(
            imported_data,
            currency_store=currency_panel.store,
            metal_store=metal_panel.store,
            bist_database=self.bist_portfolio.database,
        )
        warnings = list(imported_data.get("warnings", []))

        currency_panel.refresh_table()
        metal_panel.refresh_table()
        self.bist_portfolio.refresh_table()
        self.refresh_summary()

        message = (
            "Toplu içe aktarma tamamlandı.\n\n"
            f"Döviz: {counts['currency']} kayıt\n"
            f"Maden: {counts['metals']} kayıt\n"
            f"Hisse senedi: {counts['bist']} kayıt\n"
            f"Toplam: {sum(counts.values())} kayıt"
        )
        if warnings:
            message += "\n\nAtlanan Excel satırları:\n" + "\n".join(warnings[:10])
        if errors:
            message += "\n\nKaydedilemeyen kayıtlar:\n" + "\n".join(errors[:10])
            QMessageBox.warning(self, "İçe aktarma tamamlandı", message)
        elif warnings:
            QMessageBox.warning(self, "İçe aktarma tamamlandı", message)
        else:
            QMessageBox.information(self, "İçe aktarma tamamlandı", message)

    # ---------------- SOFTWARE UPDATES ----------------
    def _startup_update_check(self) -> None:
        """Ask once on the packaged EXE, then follow the saved preference."""
        if not getattr(sys, "frozen", False):
            return

        preference = self.settings.get("auto_update_check", None)
        if preference is None:
            dialog = QMessageBox(self)
            dialog.setWindowTitle("Otomatik güncelleme kontrolü")
            dialog.setIcon(QMessageBox.Icon.Question)
            dialog.setText("FinanceTerminal açılışta güncellemeleri otomatik kontrol etsin mi?")
            dialog.setInformativeText(
                "Yeni sürüm bulunursa indirme ve kurulumdan önce onayınız istenir. "
                "Kontrol için internet bağlantısı gerekir."
            )
            dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            dialog.setDefaultButton(QMessageBox.StandardButton.Yes)
            remember = QCheckBox("Bu tercihi hatırla ve tekrar sorma")
            dialog.setCheckBox(remember)
            enabled = dialog.exec() == QMessageBox.StandardButton.Yes
            if remember.isChecked():
                self.settings["auto_update_check"] = enabled
                save(self.settings)
        else:
            enabled = bool(preference)

        if enabled:
            self.check_for_updates(automatic=True)

    def check_for_updates(self, automatic: bool = False) -> None:
        """Check the latest stable GitHub Release without blocking the UI."""
        if self._update_check_worker is not None and self._update_check_worker.isRunning():
            if not automatic:
                QMessageBox.information(self, "Güncelleme", "Güncelleme kontrolü zaten devam ediyor.")
            return
        if self._update_download_worker is not None and self._update_download_worker.isRunning():
            if not automatic:
                QMessageBox.information(self, "Güncelleme", "Güncelleme dosyası şu anda indiriliyor.")
            return

        self._update_check_automatic = automatic
        self._update_check_payload = None
        worker = UpdateCheckWorker(self.VERSION, self)
        self._update_check_worker = worker
        worker.completed.connect(self._store_update_check_result)
        worker.finished.connect(self._finish_update_check)
        worker.start()

    def _store_update_check_result(self, payload) -> None:
        self._update_check_payload = payload

    def _finish_update_check(self) -> None:
        worker = self._update_check_worker
        if worker is not None:
            worker.deleteLater()
        self._update_check_worker = None
        payload = self._update_check_payload or {"release": None, "error": "Güncelleme kontrolü sonuç vermedi."}
        automatic = self._update_check_automatic
        error = payload.get("error")
        if error:
            QMessageBox.warning(self, "Güncelleme kontrolü", str(error))
            return

        release = payload.get("release")
        if release is None:
            QMessageBox.information(
                self, "FinanceTerminal",
                f"Güncelleme bulunamadı. {self.VERSION} sürümünü kullanıyorsunuz."
            )
            return

        if not getattr(sys, "frozen", False):
            QMessageBox.information(
                self, "Yeni sürüm bulundu",
                f"FinanceTerminal {release.version} yayımlandı.\n\n"
                "Kaynak kod modunda çalıştığınız için uygulama dosyası otomatik değiştirilemez. "
                f"Windows EXE dosyasını buradan indirebilirsiniz:\n{release.release_url}"
            )
            return

        answer = QMessageBox.question(
            self, "FinanceTerminal güncellemesi bulundu",
            f"FinanceTerminal {release.version} sürümü bulundu.\n\n"
            "Güncelleme şimdi indirilsin ve uygulama yeniden başlatılarak kurulsun mu?\n\n"
            "Portföy kayıtlarınız ve ayarlarınız korunur. Güncelleme yalnızca uygulama EXE dosyasını değiştirir.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._start_update_download(release, automatic=automatic)

    def _start_update_download(self, release, automatic: bool) -> None:
        try:
            executable = current_executable_path()
            # Fail early if the application is installed in a protected folder.
            from core.updater import ensure_install_directory_writable
            ensure_install_directory_writable(executable)
        except UpdateError as exc:
            QMessageBox.warning(self, "Güncelleme yapılamıyor", str(exc))
            return

        self._pending_update_release = release
        self._pending_update_automatic = automatic
        self._update_download_payload = None
        self._update_progress = QProgressDialog(self)
        self._update_progress.setLabelText(f"FinanceTerminal {release.version} indiriliyor...")
        self._update_progress.setRange(0, 0)
        self._update_progress.setWindowTitle("Güncelleme indiriliyor")
        self._update_progress.setCancelButton(None)
        self._update_progress.setMinimumDuration(0)
        self._update_progress.setAutoClose(False)
        self._update_progress.show()

        worker = UpdateDownloadWorker(release, self)
        self._update_download_worker = worker
        worker.completed.connect(self._store_update_download_result)
        worker.finished.connect(self._finish_update_download)
        worker.start()

    def _store_update_download_result(self, payload) -> None:
        self._update_download_payload = payload

    def _finish_update_download(self) -> None:
        worker = self._update_download_worker
        if worker is not None:
            worker.deleteLater()
        self._update_download_worker = None
        if self._update_progress is not None:
            self._update_progress.close()
            self._update_progress.deleteLater()
            self._update_progress = None

        payload = self._update_download_payload or {"path": None, "error": "İndirme sonucu alınamadı."}
        error = payload.get("error")
        if error:
            QMessageBox.warning(self, "Güncelleme indirilemedi", str(error))
            return

        downloaded = Path(payload["path"])
        try:
            executable = current_executable_path()
            launch_windows_update_helper(downloaded, executable)
        except Exception as exc:
            try:
                downloaded.unlink(missing_ok=True)
            except OSError:
                pass
            QMessageBox.warning(self, "Güncelleme başlatılamadı", str(exc))
            return

        QMessageBox.information(
            self, "Güncelleme hazır",
            f"FinanceTerminal {self._pending_update_release.version} indirildi. "
            "Uygulama şimdi kapanacak, dosya güncellenecek ve yeniden açılacak."
        )
        self._force_exit = True
        self.close()

    # ---------------- FORMAT ----------------
    def fmt(self, v):
        if v is None:
            return "N/A"
        return f"{v:.{self.precision}f}"

    # ---------------- SYSTEM TRAY ----------------
    def _init_system_tray(self) -> None:
        """Prepare the tray icon and its menu; no background refresh is scheduled."""
        if not self._tray_available:
            return

        self._tray_icon = QSystemTrayIcon(
            QIcon(str(resource_path("assets/finance_terminal.png"))), self
        )
        self._tray_icon.setToolTip("FinanceTerminal - Portföy takibi")
        menu = QMenu(self)
        open_action = menu.addAction("FinanceTerminal'ı Aç")
        open_action.triggered.connect(self.restore_from_tray)
        menu.addSeparator()
        exit_action = menu.addAction("Çıkış")
        exit_action.triggered.connect(self.exit_from_tray)
        self._tray_icon.setContextMenu(menu)
        self._tray_icon.activated.connect(self._on_tray_activated)

    def _on_tray_activated(self, reason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.restore_from_tray()

    def restore_from_tray(self) -> None:
        if self._tray_icon is not None:
            self._tray_icon.hide()
        self._in_tray = False
        self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()

    def show_from_second_instance(self) -> None:
        """Bring this process to the foreground when the user launches it again."""
        if self._in_tray:
            self.restore_from_tray()
            return
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()

    def _minimize_to_tray(self) -> None:
        if not self._tray_available or self._tray_icon is None:
            QMessageBox.information(
                self, "Sistem tepsisi kullanılamıyor",
                "Bu Windows oturumunda sistem tepsisi kullanılamıyor. Uygulama kapatılacak."
            )
            self._force_exit = True
            self.close()
            return

        self._in_tray = True
        self._tray_icon.show()
        self.hide()
        try:
            self._tray_icon.showMessage(
                "FinanceTerminal çalışıyor",
                "FinanceTerminal sistem tepsisinde açık. Fiyatlar otomatik yenilenmez; "
                "güncelleme için uygulamayı açıp Güncelle'ye basın.",
                QSystemTrayIcon.MessageIcon.Information,
                3500,
            )
        except Exception:
            pass

    def _ask_close_behavior(self) -> bool:
        """Return True to hide to tray; optionally persist either user's choice."""
        if not self._tray_available:
            return False

        dialog = QMessageBox(self)
        dialog.setWindowTitle("FinanceTerminal açık kalsın mı?")
        dialog.setIcon(QMessageBox.Icon.Question)
        dialog.setText("Uygulamayı kapatmak yerine sistem tepsisine küçültmek ister misiniz?")
        dialog.setInformativeText(
            "Evet seçerseniz uygulama arka planda açık kalır. Fiyatlar otomatik "
            "yenilenmez; yalnızca Güncelle düğmesine bastığınızda yenilenir."
        )
        dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        dialog.setDefaultButton(QMessageBox.StandardButton.Yes)
        remember = QCheckBox("Bu tercihi hatırla ve tekrar sorma")
        dialog.setCheckBox(remember)
        answer = dialog.exec()
        minimize = answer == QMessageBox.StandardButton.Yes

        if remember.isChecked():
            self.settings["close_to_tray"] = minimize
            save(self.settings)

        return minimize

    def exit_from_tray(self) -> None:
        self._force_exit = True
        self.close()

    def _request_application_close(self, event) -> None:
        for update_worker in (self._update_check_worker, self._update_download_worker):
            if update_worker is not None and update_worker.isRunning():
                QMessageBox.information(
                    self, "İşlem devam ediyor",
                    "Güncelleme işlemi tamamlandıktan sonra uygulamayı kapatabilirsiniz."
                )
                event.ignore()
                return

        worker = self.worker
        if worker is not None and worker.isRunning():
            self._close_after_update = True
            self.update_button.setEnabled(False)
            self.last.setText("Güncelleme tamamlanınca uygulama kapanacak...")
            event.ignore()
            return

        if self._tray_icon is not None:
            self._tray_icon.hide()
        event.accept()
        app = QApplication.instance()
        if app is not None:
            QTimer.singleShot(0, app.quit)

    # ---------------- UPDATE ----------------
    def update(self):
        """Start at most one price-refresh worker at a time."""
        current_worker = self.worker
        if current_worker is not None:
            if current_worker.isRunning():
                # Ignore repeated clicks while the existing request is active.
                return
            current_worker.deleteLater()
            self.worker = None

        worker = Worker(self)
        self.worker = worker
        worker.result.connect(self.on_data)
        worker.finished.connect(self._on_update_finished)
        self.update_button.setEnabled(False)
        self.last.setText("Güncelleniyor...")
        worker.start()

    def _on_update_finished(self):
        """Release the completed QThread safely on the GUI thread."""
        worker = self.worker
        if worker is not None:
            # QThread.finished is emitted at the end of run(); wait() also
            # synchronizes any remaining thread cleanup before releasing it.
            worker.wait()
            worker.deleteLater()
            self.worker = None

        if self._close_after_update:
            self._close_after_update = False
            self._final_close = True
            self.close()
        else:
            self.update_button.setEnabled(True)

    def closeEvent(self, event):
        """Ask once whether to hide in tray; safely close only on an explicit exit."""
        if self._final_close:
            self._final_close = False
            if self._tray_icon is not None:
                self._tray_icon.hide()
            event.accept()
            app = QApplication.instance()
            if app is not None:
                QTimer.singleShot(0, app.quit)
            return

        if self._force_exit:
            self._request_application_close(event)
            return

        preference = self.settings.get("close_to_tray", None)
        if preference is None:
            minimize = self._ask_close_behavior()
        else:
            minimize = bool(preference)

        if minimize and self._tray_available:
            event.ignore()
            self._minimize_to_tray()
            return

        self._request_application_close(event)

    # ---------------- DATA ----------------
    def on_data(self, d):
        self.last_data = d

        if self.mode.currentText() == "Ters":
            self.usd.title.setText("TRY/USD")
            self.eur.title.setText("TRY/EUR")
            self.huf.title.setText("TRY/HUF")

            self.usd.value.setText(self.fmt(1 / d["USD"] if d.get("USD") else None))
            self.eur.value.setText(self.fmt(1 / d["EUR"] if d.get("EUR") else None))
            self.huf.value.setText(self.fmt(1 / d["HUF"] if d.get("HUF") else None))
        else:
            self.usd.title.setText("USD/TRY")
            self.eur.title.setText("EUR/TRY")
            self.huf.title.setText("HUF/TRY")

            self.usd.value.setText(self.fmt(d["USD"]))
            self.eur.value.setText(self.fmt(d["EUR"]))
            self.huf.value.setText(self.fmt(d["HUF"]))

        self.portfolio.set_rates(d)
        self.metals.set_rates(
            d.get("gold"),
            d.get("silver"),
            d.get("USD"),
            rates_updated_at=d.get("fetched_at"),
            rates_status=d.get("status"),
        )
        self.bist_portfolio.rates_updated_at = d.get("fetched_at")
        self.bist_portfolio.rates_status = d.get("status")
        self.last.setText(d.get("status", "-"))
        self.refresh_summary()

    # ---------------- REFRESH ----------------
    def refresh(self):
        if hasattr(self, "last_data"):
            self.on_data(self.last_data)

    # ---------------- THEME ----------------
    def apply_theme(self):
        if self.theme == "White":
            self.setStyleSheet("""
                QWidget { background: #f4f6fa; color: #172033; }
                QLabel { color: #172033; background: transparent; }
                QTabWidget::pane { background: #ffffff; border: 1px solid #cbd5e1; }
                QTabBar::tab { background: #e6eaf0; color: #263449; padding: 8px 12px; border: 1px solid #cbd5e1; }
                QTabBar::tab:selected { background: #ffffff; color: #111827; border-bottom: 2px solid #2563eb; }
                QPushButton { background: #e5eaf1; color: #172033; border: 1px solid #bdc7d5; border-radius: 5px; padding: 5px 10px; }
                QPushButton:hover { background: #d8e2ef; }
                QLineEdit, QComboBox, QTableWidget, QTextEdit { background: #ffffff; color: #111827; border: 1px solid #b8c4d3; selection-background-color: #bfdbfe; selection-color: #111827; }
                QComboBox QAbstractItemView { background: #ffffff; color: #111827; selection-background-color: #bfdbfe; selection-color: #111827; }
                QHeaderView::section { background: #e6eaf0; color: #172033; border: 1px solid #cbd5e1; padding: 5px; }
                QTableWidget::item { color: #172033; }
                QFrame#summaryFrame, QFrame#bistMetricCard, QFrame#bistFormFrame { background: #ffffff; color: #172033; border: 1px solid #d5dde8; border-radius: 7px; }
                QGroupBox { color: #172033; border: 1px solid #cbd5e1; border-radius: 6px; margin-top: 8px; padding-top: 8px; }
                QGroupBox::title { color: #172033; subcontrol-origin: margin; left: 8px; padding: 0 4px; }
            """)
        elif self.theme == "Blue":
            self.setStyleSheet("""
                QWidget { background: #0f172a; color: #eaf2ff; }
                QLabel { color: #eaf2ff; background: transparent; }
                QTabWidget::pane { background: #111c32; border: 1px solid #334b70; }
                QTabBar::tab { background: #1b2a45; color: #d7e6ff; padding: 8px 12px; border: 1px solid #334b70; }
                QTabBar::tab:selected { background: #223b61; color: #ffffff; border-bottom: 2px solid #3a86ff; }
                QPushButton { background: #263b5c; color: #ffffff; border: 1px solid #3a86ff; border-radius: 5px; padding: 5px 10px; }
                QPushButton:hover { background: #31527f; }
                QLineEdit, QComboBox, QTableWidget, QTextEdit { background: #17243a; color: #f4f8ff; border: 1px solid #3b5275; selection-background-color: #3a86ff; selection-color: #ffffff; }
                QComboBox QAbstractItemView { background: #17243a; color: #f4f8ff; selection-background-color: #3a86ff; }
                QHeaderView::section { background: #223b61; color: #ffffff; border: 1px solid #3b5275; padding: 5px; }
                QTableWidget::item { color: #f4f8ff; }
                QFrame#summaryFrame, QFrame#bistMetricCard, QFrame#bistFormFrame { background: #17243a; color: #f4f8ff; border: 1px solid #334b70; border-radius: 7px; }
                QGroupBox { color: #eaf2ff; border: 1px solid #334b70; border-radius: 6px; margin-top: 8px; padding-top: 8px; }
                QGroupBox::title { color: #eaf2ff; subcontrol-origin: margin; left: 8px; padding: 0 4px; }
            """)
        else:  # Dark
            self.setStyleSheet("""
                QWidget { background: #121417; color: #edf0f4; }
                QLabel { color: #edf0f4; background: transparent; }
                QTabWidget::pane { background: #171a1f; border: 1px solid #343a44; }
                QTabBar::tab { background: #20242b; color: #d7dce4; padding: 8px 12px; border: 1px solid #343a44; }
                QTabBar::tab:selected { background: #171a1f; color: #ffffff; border-bottom: 2px solid #60a5fa; }
                QPushButton { background: #2b3038; color: #f4f6f8; border: 1px solid #454c57; border-radius: 5px; padding: 5px 10px; }
                QPushButton:hover { background: #363d47; }
                QLineEdit, QComboBox, QTableWidget, QTextEdit { background: #1b1f25; color: #f4f6f8; border: 1px solid #454c57; selection-background-color: #315b88; selection-color: #ffffff; }
                QComboBox QAbstractItemView { background: #1b1f25; color: #f4f6f8; selection-background-color: #315b88; }
                QHeaderView::section { background: #292f38; color: #f4f6f8; border: 1px solid #454c57; padding: 5px; }
                QTableWidget::item { color: #f4f6f8; }
                QFrame#summaryFrame, QFrame#bistMetricCard, QFrame#bistFormFrame { background: #1b1f25; color: #f4f6f8; border: 1px solid #343a44; border-radius: 7px; }
                QGroupBox { color: #edf0f4; border: 1px solid #343a44; border-radius: 6px; margin-top: 8px; padding-top: 8px; }
                QGroupBox::title { color: #edf0f4; subcontrol-origin: margin; left: 8px; padding: 0 4px; }
            """)

    # ---------------- SETTINGS ----------------
    def open_settings(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Ayarlar")
        dlg.setMinimumWidth(320)

        layout = QVBoxLayout()
        version = QLabel(f"Version: {self.VERSION}")

        start_tab = QComboBox()
        start_tab.addItems(["Summary", "Currency", "Portfolio", "Metals", "BIST AI"])
        start_tab.setCurrentIndex(self.tabs.currentIndex())

        precision = QComboBox()
        precision.addItems(["2", "3", "4"])
        precision.setCurrentText(str(self.precision))

        theme = QComboBox()
        theme.addItem("Windows ayarını takip et", "System")
        theme.addItem("Açık tema", "White")
        theme.addItem("Koyu tema", "Dark")
        theme.addItem("Mavi tema", "Blue")
        theme_index = theme.findData(self.theme_preference)
        theme.setCurrentIndex(theme_index if theme_index >= 0 else 0)

        btn = QPushButton("Kaydet")
        close_behavior = QComboBox()
        close_behavior.addItem("Her kapatmada sor", "ask")
        close_behavior.addItem("Sistem tepsisine küçült", "tray")
        close_behavior.addItem("Uygulamayı tamamen kapat", "exit")
        saved_close = self.settings.get("close_to_tray", None)
        close_key = "ask" if saved_close is None else ("tray" if bool(saved_close) else "exit")
        close_index = close_behavior.findData(close_key)
        close_behavior.setCurrentIndex(close_index if close_index >= 0 else 0)

        auto_update = QCheckBox(
            "Başlangıçta güncellemeleri kontrol et (yeni sürüm bulunursa önce sor)"
        )
        auto_update.setChecked(bool(self.settings.get("auto_update_check", False)))
        update_btn = QPushButton("Güncellemeleri Kontrol Et")

        help_btn = QPushButton("Yardım / Kullanım Kılavuzu")
        help_btn.clicked.connect(lambda: self.open_help(dlg))

        def save_all():
            self.precision = int(precision.currentText())
            self.tabs.setCurrentIndex(start_tab.currentIndex())
            self.theme_preference = str(theme.currentData() or "System")
            self.theme = resolve_theme(self.theme_preference)

            self.settings["precision"] = self.precision
            self.settings["start_tab"] = self.tabs.currentIndex()
            self.settings["theme"] = self.theme_preference
            self.settings["summary_tab_migrated"] = True
            self.settings["auto_update_check"] = auto_update.isChecked()
            close_choice = close_behavior.currentData()
            self.settings["close_to_tray"] = (
                None if close_choice == "ask" else close_choice == "tray"
            )
            self.apply_theme()
            save(self.settings)
            dlg.accept()

        btn.clicked.connect(save_all)

        def manual_update_check():
            save_all()
            QTimer.singleShot(0, lambda: self.check_for_updates(automatic=False))

        update_btn.clicked.connect(manual_update_check)
        layout.addWidget(version)
        layout.addWidget(QLabel("Başlangıç Sekmesi"))
        layout.addWidget(start_tab)
        layout.addWidget(QLabel("Hassasiyet"))
        layout.addWidget(precision)
        layout.addWidget(QLabel("Tema"))
        layout.addWidget(theme)
        layout.addWidget(QLabel("Pencereyi X ile kapatınca"))
        layout.addWidget(close_behavior)
        layout.addWidget(auto_update)
        layout.addWidget(QLabel(
            "Yeni sürüm bulunduğunda indirme ve kurulum için ayrıca onayınız istenir. "
            "Kişisel portföy verileri %APPDATA%\\FinanceTerminal altında saklanır."
        ))
        layout.addWidget(btn)
        layout.addWidget(update_btn)
        layout.addWidget(help_btn)
        dlg.setLayout(layout)
        dlg.exec()

    def open_help(self, parent=None):
        """Show a concise, built-in guide for the application tabs."""
        dlg = QDialog(parent or self)
        dlg.setWindowTitle("FinanceTerminal - Kullanım Kılavuzu")
        dlg.resize(620, 560)

        layout = QVBoxLayout(dlg)
        browser = QTextBrowser(dlg)
        browser.setOpenExternalLinks(True)
        browser.setHtml(r"""
        <h2>FinanceTerminal Kullanım Kılavuzu</h2>
        <p>FinanceTerminal; döviz, yatırım amaçlı döviz birikimi, değerli maden ve
        BIST portföy kayıtlarını tek uygulamada takip etmenizi sağlar.</p>

        <h3>Summary</h3>
        <p>Döviz, maden ve hisse senedi portföylerinizin toplam değerini TRY, EUR
        ve USD cinsinden özetler. Fiyatlar yenilendiğinde ve portföy kayıtları
        değiştiğinde özet otomatik güncellenir. BIST AI bölümünde canlı fiyat
        bulunmadığından hisse toplamı kayıtlı alış maliyeti üzerinden hesaplanır.</p>

        <h3>Currency</h3>
        <p>USD, EUR ve HUF kurlarını gösterir. <b>Normal</b> görünümde dövizin TL
        karşılığını, <b>Ters</b> görünümde TL'nin döviz karşılığını gösterir.
        <b>Güncelle</b> düğmesi fiyat verilerini internetten yeniler.</p>

        <h3>Portfolio</h3>
        <p>USD, EUR ve HUF alımlarınızı miktar ve alış birim fiyatıyla kaydedin.
        Aynı dövizden tekrar alım yaptığınızda miktar birleştirilir ve ağırlıklı
        ortalama maliyet hesaplanır. Güncel değer ve kâr/zarar fiyat verisi varsa
        otomatik gösterilir. Excel içe/dışa aktarma seçeneklerini kullanabilirsiniz.</p>

        <h3>Metals</h3>
        <p>Altın ve gümüş alımlarınızı gram miktarı ve alış fiyatıyla kaydedin.
        Tekrarlanan alımlar birleştirilir; ortalama maliyet, güncel değer ve
        kâr/zarar hesaplanır. Güncel değerler sağlayıcıdan alınan spot fiyatlara
        dayanır; kuyumcu işçilik ve alış-satış farklarını içermez.</p>

        <h3>BIST AI</h3>
        <p>Hisse kodu, şirket adı, adet ve ortalama alış maliyetinizi kaydedin.
        Kayıtlar bilgisayarınızda saklanır ve Excel'e aktarılabilir. Bu sürümde
        canlı BIST fiyatı ve yapay zekâ analizi henüz bulunmamaktadır.</p>

        <h3>Tüm Portföyü Excel'e Aktar</h3>
        <p>Üstteki düğme tüm bölümleri tek Excel dosyasına aktarır. Dosyada Summary,
        Döviz, Maden, Hisse Senedi ve Veri Bilgisi sayfaları bulunur. Veri Bilgisi
        sayfası, dışa aktarım ve son fiyat güncelleme zamanını ve veri sağlayıcılarını
        gösterir.</p>

        <h3>Kayıt silme</h3>
        <p>Portfolio, Metals ve BIST AI tablolarında birden fazla satır seçmek için Ctrl veya Shift
        tuşunu kullanabilirsiniz. <b>Seçili Kayıtları Sil</b> yalnızca seçtiklerinizi kaldırır.
        <b>Tüm Kayıtları Sil</b> ilgili bölümün bütün kayıtlarını temizler ve ayrıca onay ister.
        Silme işlemi geri alınamaz; gerekirse önce Excel dışa aktarımıyla yedek alın.</p>

        <h3>Ayarlar</h3>
        <p>Başlangıç sekmesini, sayı hassasiyetini ve temayı seçebilirsiniz.
        <b>Windows ayarını takip et</b> seçeneği sisteminizin açık/koyu temasını
        kullanır. Açık, koyu veya mavi temayı ayrıca elle seçebilirsiniz.</p>

        <h3>Güncellemeler</h3>
        <p>Güncellemeleri Kontrol Et düğmesi GitHub üzerindeki en son kararlı sürümü denetler.
        Otomatik kontrol açık ise uygulama açılışta kontrol yapar. Yeni sürüm bulunduğunda
        indirme ve kurulum için mutlaka onayınız istenir. Güncelleme yalnızca EXE dosyasını
        değiştirir; %APPDATA%\FinanceTerminal altında saklanan portföy verileriniz ve ayarlarınız korunur.
        Yerel kaynak kod çalıştırmasında EXE otomatik olarak değiştirilemez.</p>

        <h3>Uygulama verileri ve tek örnek</h3>
        <p>Ayarlar ve portföy verileri Windows kullanıcı profilinizdeki
        %APPDATA%\FinanceTerminal klasöründe saklanır. Böylece masaüstünde config.json
        dosyası oluşmaz ve uygulama güncellendiğinde kayıtlarınız silinmez. FinanceTerminal
        zaten açıksa EXE'yi yeniden başlatmak yeni pencere oluşturmaz; açık pencereyi öne getirir.</p>

        <p><i>Not: Uygulamadaki fiyatlar bilgilendirme ve portföy takibi içindir.
        Gerçek işlem öncesinde bankanızın, aracı kurumunuzun veya kuyumcunuzun
        alış-satış fiyatlarını kontrol edin.</i></p>
        """)
        close_btn = QPushButton("Kapat", dlg)
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(browser)
        layout.addWidget(close_btn)
        dlg.exec()
