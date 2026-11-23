from decimal import Decimal
import sys

from PySide6.QtCore import QTimer, Qt
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QComboBox, QLabel, QPushButton, QDialog, QSizePolicy,
    QFileDialog, QMessageBox, QTextBrowser, QCheckBox, QProgressDialog,
    QSystemTrayIcon, QMenu, QApplication, QGridLayout, QScrollArea,
    QListWidget, QListWidgetItem, QInputDialog, QDialogButtonBox,
)

from worker import Worker
from ui.card import Card
from features.metals import Metals
from features.portfolio import Portfolio
from features.summary import SummaryPage
from features.bist.portfolio_tab import BistPortfolioTab
from features.bist.database import BistDatabase
from features.investment_store import InvestmentStore, format_localized
from features.currencies import (
    CURRENCY_INFO, DEFAULT_CURRENCY_CODES, DEFAULT_EXTRA_CURRENCY, currency_display_name,
    sort_currency_codes,
)
from features.investment_excel import write_combined_portfolio_excel
from features.export_dialog import EXPORT, TEMPLATE, ask_export_mode, run_template_export
from features.export_templates import write_combined_template
from features.export_metadata import profile_export_filename
from features.profile_utils import profile_selector_label, MAX_PROFILE_SELECTOR_CHARS
from features.combined_import import (
    read_combined_portfolio_excel, apply_combined_portfolio_import,
)
from core.resources import resource_path
from core.version import APP_VERSION
from core import autostart
from core.help_text import help_html
from ui.themes import EXTRA_THEMES, build_stylesheet
from core.app_paths import (
    set_active_profile, migrate_legacy_data_to_profile1, app_data_directory, profile_directory,
)
from settings import load, save, resolve_theme
from core.update_worker import UpdateCheckWorker, UpdateDownloadWorker
from core.updater import (
    UpdateError, current_executable_path, launch_windows_update_helper,
)
from core.i18n import get_language, normalize_language, tr, tr_noop, translate
from features.dialogs import ask_question, ask_warning_question, localize_dialog_buttons, localize_message_buttons


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowIcon(QIcon(str(resource_path("assets/finance_terminal.png"))))
        self.setWindowTitle("FinanceTerminal")

        # ---------------- SETTINGS ----------------
        self.VERSION = APP_VERSION
        self.settings = load()
        self._initialize_profile_settings()
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

        self.summary_page = SummaryPage()
        self.tabs.addTab(self.summary_page, tr("Özet"))

        # ---------------- CURRENCY ----------------
        self.tab1 = QWidget()
        l1 = QVBoxLayout(self.tab1)

        self.currency_cards_container = QWidget(self.tab1)
        self.currency_cards_layout = QGridLayout(self.currency_cards_container)
        self.currency_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.currency_cards_layout.setHorizontalSpacing(10)
        self.currency_cards_layout.setVerticalSpacing(10)
        self.currency_cards_scroll = QScrollArea(self.tab1)
        self.currency_cards_scroll.setWidgetResizable(True)
        self.currency_cards_scroll.setWidget(self.currency_cards_container)
        self.currency_cards_scroll.setMinimumHeight(145)
        self.currency_cards_scroll.setMaximumHeight(360)
        self.currency_cards = {}
        self.refresh_currency_cards()

        self.mode = QComboBox()
        self.mode.addItem(tr("Normal"), "normal")
        self.mode.addItem(tr("Ters"), "reverse")
        self.mode.currentIndexChanged.connect(self.refresh)

        self.last = QLabel("-")
        self.currency_settings_button = QPushButton(tr("Görüntülenecek Para Birimlerini Seç"))
        self.currency_settings_button.clicked.connect(self.open_currency_settings)

        self.update_button = QPushButton(tr("Güncelle"))
        self.update_button.clicked.connect(self.update)

        l1.addWidget(self.currency_cards_scroll)
        l1.addWidget(self.currency_settings_button)
        l1.addWidget(self.mode)
        l1.addWidget(self.last)
        l1.addWidget(self.update_button)
        l1.addStretch()

        # ---------------- OTHER TABS ----------------
        self.portfolio = Portfolio(
            extra_currency=str(self.settings.get("calculator_extra_currency", DEFAULT_EXTRA_CURRENCY))
        )
        self.portfolio.extra_currency_changed.connect(self._save_extra_currency)
        self.metals = Metals()
        self.bist_portfolio = BistPortfolioTab()
        self.bist_portfolio.storage_label.setText(
            tr("Veriler bu bilgisayarda saklanır · {0}").format(self.profile_names[self.settings['active_profile']])
        )

        self.tabs.addTab(self.tab1, tr("Döviz"))
        self.tabs.addTab(self.portfolio, tr("Portföy"))
        self.tabs.addTab(self.metals, tr("Metaller"))
        self.tabs.addTab(self.bist_portfolio, tr("BIST AI"))

        self.portfolio.investment_panel.portfolio_changed.connect(self.refresh_summary)
        self.metals.investment_panel.portfolio_changed.connect(self.refresh_summary)
        self.bist_portfolio.portfolio_changed.connect(self.refresh_summary)
        self.bist_portfolio.refresh_requested.connect(self.update)

        try:
            start_index = int(self.start_tab)
        except (TypeError, ValueError):
            start_index = 0
        self.tabs.setCurrentIndex(start_index if 0 <= start_index < self.tabs.count() else 0)

        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel(tr("Profil:")))
        self.profile_selector = QComboBox()
        self.profile_selector.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._refresh_profile_selector()
        self.profile_selector.currentIndexChanged.connect(self.switch_profile)
        toolbar.addWidget(self.profile_selector)
        self.rename_profile_button = QPushButton(tr("Profil Adını Değiştir"))
        self.rename_profile_button.clicked.connect(self.rename_current_profile)
        toolbar.addWidget(self.rename_profile_button)
        toolbar.addStretch(1)
        self.import_all_button = QPushButton(tr("Tüm Portföyü Excel'den İçe Aktar"))
        self.import_all_button.clicked.connect(self.import_complete_portfolio)
        toolbar.addWidget(self.import_all_button)
        self.export_all_button = QPushButton(tr("Tüm Portföyü Excel'e Aktar"))
        self.export_all_button.clicked.connect(self.export_complete_portfolio)
        toolbar.addWidget(self.export_all_button)
        self.settings_button = QPushButton(tr("Ayarlar ⚙️"))
        self.settings_button.setObjectName("globalSettingsButton")
        self.settings_button.setToolTip(tr("Uygulama ayarlarını aç"))
        self.settings_button.clicked.connect(self.open_settings)
        toolbar.addWidget(self.settings_button)
        layout.addLayout(toolbar)
        layout.addWidget(self.tabs)

        self.apply_theme()
        self.refresh_summary()
        self.update()
        # Startup update preference is asked only by the packaged Windows EXE.
        QTimer.singleShot(1400, self._startup_sequence)


    # ---------------- PROFILE MANAGEMENT ----------------
    @staticmethod
    def _profile_name(stored, number: int) -> str:
        """A profile still carrying a default name follows the current language."""
        defaults = {f"Profil {number}", f"Profile {number}"}
        name = str(stored or "").strip()
        markers = {1: tr_noop("Profil 1"), 2: tr_noop("Profil 2"), 3: tr_noop("Profil 3")}
        return tr(markers[number]) if (not name or name in defaults) else name

    def _initialize_profile_settings(self) -> None:
        names = self.settings.get("profile_names")
        if not isinstance(names, dict):
            names = {}
        self.profile_names = {
            "profile1": self._profile_name(names.get("profile1"), 1),
            "profile2": self._profile_name(names.get("profile2"), 2),
        }
        # Profile 3 is opt-in and appears only after the user selects "Profil Ekle".
        if names.get("profile3"):
            self.profile_names["profile3"] = self._profile_name(names.get("profile3"), 3)
        active = str(self.settings.get("active_profile", "profile1")).lower()
        if active not in self.profile_names:
            active = "profile1"
        self.settings["profile_names"] = self.profile_names
        self.settings["active_profile"] = active

        # Copy legacy 2.2.x data once to Profile 1; leave the original data folder
        # untouched as an additional recovery copy.
        legacy_data = app_data_directory() / "data"
        profile1_data = profile_directory("profile1") / "data"
        if legacy_data.is_dir() and not profile1_data.exists():
            if not migrate_legacy_data_to_profile1():
                QMessageBox.warning(
                    self,
                    tr("Eski portföy verileri kopyalanamadı"),
                    tr("Önceki sürümün veri klasörü değiştirilmedi. FinanceTerminal eski verilerinizi otomatik olarak Profile 1'e kopyalayamadı. Uygulamayı kapatın ve yedek klasörünüzü koruyun."),
                )
        set_active_profile(active)

        configured = self.settings.get("currency_codes", DEFAULT_CURRENCY_CODES)
        if not isinstance(configured, list):
            configured = DEFAULT_CURRENCY_CODES
        selected = sort_currency_codes(code for code in configured if code in CURRENCY_INFO)
        self.settings["currency_codes"] = selected or DEFAULT_CURRENCY_CODES.copy()
        save(self.settings)

    def _save_extra_currency(self, code: str) -> None:
        """Remember the calculator's freely chosen extra currency."""
        self.settings["calculator_extra_currency"] = str(code)
        save(self.settings)

    def _refresh_profile_selector(self) -> None:
        if not hasattr(self, "profile_selector"):
            return
        self.profile_selector.blockSignals(True)
        self.profile_selector.clear()
        for profile_id in ("profile1", "profile2", "profile3"):
            if profile_id not in self.profile_names:
                continue
            full_name = self.profile_names[profile_id]
            label = profile_selector_label(full_name)
            self.profile_selector.addItem(label, profile_id)
            self.profile_selector.setItemData(
                self.profile_selector.count() - 1, full_name, Qt.ItemDataRole.ToolTipRole
            )

        # Keep the add action visible even at the limit so the user gets an
        # explicit explanation instead of silently losing the option.
        self.profile_selector.addItem(tr("＋ Profil Ekle"), "__add_profile__")
        active_index = self.profile_selector.findData(self.settings.get("active_profile"))
        self.profile_selector.setCurrentIndex(active_index if active_index >= 0 else 0)

        # Grow with the profile name up to 20 visible characters. Longer names
        # are elided in the selector, while the full name remains in settings.
        metrics = self.profile_selector.fontMetrics()
        visible_names = [
            profile_selector_label(name)
            for name in self.profile_names.values()
        ]
        visible_width = max(
            (metrics.horizontalAdvance(name) for name in visible_names),
            default=metrics.horizontalAdvance("Profil 1"),
        )
        max_text_width = metrics.horizontalAdvance("M" * MAX_PROFILE_SELECTOR_CHARS + "...")
        self.profile_selector.setFixedWidth(min(visible_width, max_text_width) + 48)
        self.profile_selector.blockSignals(False)

    def add_profile(self) -> None:
        """Create the optional third profile and switch to its empty data store."""
        if "profile3" in self.profile_names:
            QMessageBox.information(
                self,
                tr("Maksimum profil sayısı"),
                tr("Maksimum profil limitine ulaşılmıştır. Ekstra profil için GitHub üzerinden Issue açınız."),
            )
            self._refresh_profile_selector()
            return

        self.profile_names["profile3"] = tr("Profil 3")
        self.settings["profile_names"] = self.profile_names
        try:
            save(self.settings)
        except Exception as exc:
            self.profile_names.pop("profile3", None)
            self.settings["profile_names"] = self.profile_names
            QMessageBox.warning(self, tr("Profil oluşturulamadı"), str(exc))
            self._refresh_profile_selector()
            return

        self._refresh_profile_selector()
        profile_index = self.profile_selector.findData("profile3")
        if profile_index >= 0:
            self.profile_selector.setCurrentIndex(profile_index)

    def switch_profile(self, index: int) -> None:
        if index < 0 or not hasattr(self, "portfolio"):
            return
        selected_data = self.profile_selector.itemData(index)
        if selected_data == "__add_profile__":
            self.add_profile()
            return
        profile_id = str(selected_data or "profile1")
        if profile_id not in self.profile_names:
            self._refresh_profile_selector()
            return
        if profile_id == self.settings.get("active_profile"):
            return
        previous_profile = str(self.settings.get("active_profile", "profile1"))
        previous_currency_store = self.portfolio.investment_panel.store
        previous_metals_store = self.metals.investment_panel.store
        previous_bist_database = self.bist_portfolio.database
        try:
            set_active_profile(profile_id)
            # Create all target repositories before swapping any live UI references.
            currency_store = InvestmentStore()
            metals_store = InvestmentStore()
            bist_database = BistDatabase()
            self.portfolio.investment_panel.store = currency_store
            self.metals.investment_panel.store = metals_store
            self.bist_portfolio.database = bist_database
            self.portfolio.investment_panel.refresh_table()
            self.metals.investment_panel.refresh_table()
            self.bist_portfolio.refresh_table()
            self.settings["active_profile"] = profile_id
            save(self.settings)
            self.bist_portfolio.storage_label.setText(
                tr("Veriler bu bilgisayarda saklanır · {0}").format(self.profile_names[profile_id])
            )
            self.refresh_summary()
        except Exception as exc:
            self.portfolio.investment_panel.store = previous_currency_store
            self.metals.investment_panel.store = previous_metals_store
            self.bist_portfolio.database = previous_bist_database
            set_active_profile(previous_profile)
            self.settings["active_profile"] = previous_profile
            try:
                save(self.settings)
            except Exception:
                pass
            self.portfolio.investment_panel.refresh_table()
            self.metals.investment_panel.refresh_table()
            self.bist_portfolio.refresh_table()
            QMessageBox.critical(self, tr("Profil değiştirilemedi"), str(exc))
            self._refresh_profile_selector()

    def rename_current_profile(self) -> None:
        profile_id = str(self.settings.get("active_profile", "profile1"))
        if profile_id not in self.profile_names:
            return
        old_name = self.profile_names[profile_id]
        dialog = QInputDialog(self)
        dialog.setWindowTitle(tr("Profil adını değiştir"))
        dialog.setLabelText(tr("Yeni profil adı:"))
        dialog.setInputMode(QInputDialog.InputMode.TextInput)
        dialog.setTextValue(old_name)
        dialog.setOkButtonText("Kaydet")
        dialog.setCancelButtonText(tr("Vazgeç"))
        # Do not truncate the entered value: the selector shows an ellipsis
        # after 20 visible characters, but Excel receives the full profile name.
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        new_name = str(dialog.textValue()).strip()
        if not new_name:
            QMessageBox.warning(self, tr("Geçersiz ad"), tr("Profil adı boş bırakılamaz."))
            return
        if any(
            other_id != profile_id and other_name.casefold() == new_name.casefold()
            for other_id, other_name in self.profile_names.items()
        ):
            QMessageBox.warning(self, tr("Profil adı kullanılıyor"), tr("Profillerin adı aynı olamaz."))
            return
        previous_name = self.profile_names[profile_id]
        self.profile_names[profile_id] = new_name
        self.settings["profile_names"] = self.profile_names
        try:
            save(self.settings)
        except Exception as exc:
            self.profile_names[profile_id] = previous_name
            self.settings["profile_names"] = self.profile_names
            QMessageBox.warning(self, tr("Profil adı kaydedilemedi"), str(exc))
            self._refresh_profile_selector()
            return
        self._refresh_profile_selector()
        self.bist_portfolio.storage_label.setText(
            tr("Veriler bu bilgisayarda saklanır · {0}").format(new_name)
        )

    # ---------------- CURRENCY DISPLAY OPTIONS ----------------
    def refresh_currency_cards(self) -> None:
        if not hasattr(self, "currency_cards_layout"):
            return
        while self.currency_cards_layout.count():
            item = self.currency_cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.currency_cards = {}
        codes = sort_currency_codes(
            code for code in self.settings.get("currency_codes", DEFAULT_CURRENCY_CODES)
            if code in CURRENCY_INFO
        ) or DEFAULT_CURRENCY_CODES
        for index, code in enumerate(codes):
            card = Card(f"{code}/TRY", currency_display_name(code))
            card.title.setToolTip(currency_display_name(code))
            card.value.setText("...")
            card.apply_theme(self.theme)
            self.currency_cards[code] = card
            self.currency_cards_layout.addWidget(card, index // 3, index % 3)
        if hasattr(self, "last_data"):
            self.on_data(self.last_data)

    def open_currency_settings(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("Görüntülenecek Para Birimleri"))
        dlg.setMinimumSize(360, 470)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel(
            tr("Döviz sekmesinde görmek istediğiniz para birimlerini seçin. Kur sağlayıcısında bulunmayan birimlerde güncel fiyat gösterilemez.")
        ))
        selection_actions = QHBoxLayout()
        select_all_button = QPushButton(tr("Tümünü Seç"))
        clear_selection_button = QPushButton(tr("Seçimi Temizle"))
        selection_actions.addWidget(select_all_button)
        selection_actions.addWidget(clear_selection_button)
        layout.addLayout(selection_actions)

        listing = QListWidget(dlg)
        current = set(self.settings.get("currency_codes", DEFAULT_CURRENCY_CODES))
        for code in CURRENCY_INFO:  # already in the shared global-usage order
            item = QListWidgetItem(f"{code} — {currency_display_name(code)}")
            item.setData(Qt.UserRole, code)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if code in current else Qt.Unchecked)
            listing.addItem(item)
        def set_all_currency_checks(state):
            for index in range(listing.count()):
                listing.item(index).setCheckState(state)

        select_all_button.clicked.connect(
            lambda _checked=False: set_all_currency_checks(Qt.Checked)
        )
        clear_selection_button.clicked.connect(
            lambda _checked=False: set_all_currency_checks(Qt.Unchecked)
        )
        layout.addWidget(listing)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        localize_dialog_buttons(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        if dlg.exec() != QDialog.Accepted:
            return
        selected = [
            listing.item(i).data(Qt.UserRole)
            for i in range(listing.count())
            if listing.item(i).checkState() == Qt.Checked
        ]
        if not selected:
            QMessageBox.warning(self, tr("Seçim gerekli"), tr("En az bir para birimi seçmelisiniz."))
            return
        self.settings["currency_codes"] = selected
        save(self.settings)
        self.refresh_currency_cards()

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
            bist_prices=self.bist_portfolio.price_map(),
        )

    # ---------------- COMBINED PORTFOLIO EXPORT ----------------
    def export_complete_portfolio(self):
        profile_id = str(self.settings.get("active_profile", "profile1"))
        profile_name = self.profile_names[profile_id]
        suggested_filename = profile_export_filename(profile_name, profile_id)
        mode = ask_export_mode(self, tr("Tüm portföy"))
        if mode == TEMPLATE:
            run_template_export(
                self,
                caption=tr("Tüm portföy örnek şablonunu kaydet"),
                default_name="FinanceTerminal_Tum_Portfoy_Ornek_Sablon.xlsx",
                writer=lambda target: write_combined_template(
                    target,
                    self.portfolio.investment_panel.assets,
                    self.metals.investment_panel.assets,
                ),
            )
            return
        if mode != EXPORT:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Tüm portföyü tek Excel dosyasına aktar"),
            str(Path.home() / suggested_filename),
            tr("Excel dosyaları (*.xlsx)"),
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
                bist_prices=self.bist_portfolio.price_map() or None,
                bist_price_notes=self.bist_portfolio.price_notes(),
                rates_updated_at=rates.get("fetched_at"),
                rates_status=rates.get("status"),
                profile_name=profile_name,
            )
            QMessageBox.information(
                self,
                tr("Dışa aktarma tamamlandı"),
                tr("Tüm portföy tek Excel dosyasına aktarıldı:\n{0}\n\nSummary, Döviz, Maden, Hisse Senedi ve Veri Bilgisi sayfaları oluşturuldu.").format(path),
            )
        except Exception as exc:
            QMessageBox.warning(self, tr("Dışa aktarma başarısız"), str(exc))

    # ---------------- COMBINED PORTFOLIO IMPORT ----------------
    def import_complete_portfolio(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Tüm portföyün bulunduğu Excel dosyasını seç"),
            str(Path.home()),
            tr("Excel dosyaları (*.xlsx)"),
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
            QMessageBox.warning(self, tr("Excel okunamadı"), str(exc))
            return

        currency_rows = imported_data["currency"]
        metal_rows = imported_data["metals"]
        bist_rows = imported_data["bist"]
        total_rows = len(currency_rows) + len(metal_rows) + len(bist_rows)
        if total_rows == 0:
            QMessageBox.information(
                self, tr("İçe aktarma"), tr("Dosyada içe aktarılabilecek portföy kaydı bulunamadı.")
            )
            return

        details = (
            tr("Döviz: {0} kayıt\nMaden: {1} kayıt\nHisse senedi: {2} kayıt\n\nAynı varlık veya hisse kodu mevcutsa miktar ve ortalama maliyet Excel dosyasındaki değerlerle güncellenecek; kayıtlar ikinci kez eklenmeyecek. Dosyada bulunmayan bölümlerdeki mevcut kayıtlar korunacak.\n\nDevam edilsin mi?").format(len(currency_rows), len(metal_rows), len(bist_rows))
        )
        answer = ask_question(
            self, tr("Tüm portföyü içe aktar"), details,
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
            tr("Toplu içe aktarma tamamlandı.\n\nDöviz: {0} kayıt\nMaden: {1} kayıt\nHisse senedi: {2} kayıt\nToplam: {3} kayıt").format(counts['currency'], counts['metals'], counts['bist'], sum(counts.values()))
        )
        if warnings:
            message += tr("\n\nAtlanan Excel satırları:\n") + "\n".join(warnings[:10])
        if errors:
            message += tr("\n\nKaydedilemeyen kayıtlar:\n") + "\n".join(errors[:10])
            QMessageBox.warning(self, tr("İçe aktarma tamamlandı"), message)
        elif warnings:
            QMessageBox.warning(self, tr("İçe aktarma tamamlandı"), message)
        else:
            QMessageBox.information(self, tr("İçe aktarma tamamlandı"), message)

    # ---------------- WINDOWS STARTUP ----------------
    def _startup_sequence(self) -> None:
        """First-run questions are asked one after another, never stacked."""
        self._startup_update_check()
        self._startup_autostart_prompt()

    def _apply_autostart_choice(self, enabled: bool, parent=None) -> bool:
        """Apply the Windows-startup choice; the saved setting mirrors the real state."""
        if not autostart.is_supported():
            return False
        if not autostart.set_enabled(enabled):
            QMessageBox.warning(
                parent or self,
                tr("Windows başlangıç ayarı"),
                tr("Windows başlangıç ayarı değiştirilemedi. Kayıt defterine yazma izni olmayabilir; ayarı daha sonra tekrar deneyebilirsiniz."),
            )
        actual = autostart.is_enabled()
        self.settings["start_with_windows"] = actual
        return actual

    def _startup_autostart_prompt(self) -> None:
        """Ask once (packaged Windows EXE only) whether to start with Windows."""
        if not autostart.is_supported():
            return
        choice = self.settings.get("start_with_windows", None)
        if choice is None:
            dialog = QMessageBox(self)
            dialog.setWindowTitle(tr("Windows ile başlat"))
            dialog.setIcon(QMessageBox.Icon.Question)
            dialog.setText(tr("Bilgisayar açıldığında FinanceTerminal otomatik başlasın mı?"))
            dialog.setInformativeText(
                tr("Evet derseniz Windows'a giriş yaptığınızda uygulama kendiliğinden açılır ve güncel fiyatları alır. Bu seçimi istediğiniz zaman Ayarlar'dan değiştirebilirsiniz.")
            )
            dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            localize_message_buttons(dialog)
            dialog.setDefaultButton(QMessageBox.StandardButton.No)
            enabled = dialog.exec() == QMessageBox.StandardButton.Yes
            self._apply_autostart_choice(enabled)
            save(self.settings)
        elif choice:
            # The EXE may have been moved or updated; keep the saved entry pointing at it.
            autostart.repair_command()

    def should_start_in_tray(self) -> bool:
        return bool(
            self.settings.get("start_in_tray", False)
            and self._tray_available
            and self._tray_icon is not None
        )

    def start_hidden_in_tray(self) -> None:
        """Used when Windows starts the app: no window, just the tray icon."""
        self._minimize_to_tray(notify=False)

    def retry_refresh_if_offline(self) -> None:
        """Right after sign-in the network may not be ready yet; try once more."""
        status = str((getattr(self, "last_data", None) or {}).get("status", ""))
        if status.startswith("Offline"):
            self.update()

    # ---------------- SOFTWARE UPDATES ----------------
    def _startup_update_check(self) -> None:
        """Ask once on the packaged EXE, then follow the saved preference."""
        if not getattr(sys, "frozen", False):
            return

        preference = self.settings.get("auto_update_check", None)
        if preference is None:
            dialog = QMessageBox(self)
            dialog.setWindowTitle(tr("Otomatik güncelleme kontrolü"))
            dialog.setIcon(QMessageBox.Icon.Question)
            dialog.setText(tr("FinanceTerminal açılışta güncellemeleri otomatik kontrol etsin mi?"))
            dialog.setInformativeText(
                tr("Yeni sürüm bulunursa indirme ve kurulumdan önce onayınız istenir. Kontrol için internet bağlantısı gerekir.")
            )
            dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            localize_message_buttons(dialog)
            dialog.setDefaultButton(QMessageBox.StandardButton.Yes)
            remember = QCheckBox(tr("Bu tercihi hatırla ve tekrar sorma"))
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
                QMessageBox.information(self, tr("Güncelleme"), tr("Güncelleme kontrolü zaten devam ediyor."))
            return
        if self._update_download_worker is not None and self._update_download_worker.isRunning():
            if not automatic:
                QMessageBox.information(self, tr("Güncelleme"), tr("Güncelleme dosyası şu anda indiriliyor."))
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
        payload = self._update_check_payload or {"release": None, "error": tr("Güncelleme kontrolü sonuç vermedi.")}
        automatic = self._update_check_automatic
        error = payload.get("error")
        if error:
            # Keep automatic startup checks silent.
            # Manual checks still display connection or server errors.
            if not automatic:
                QMessageBox.warning(
                    self, tr("Güncelleme kontrolü"), str(error)
                )
            return

        release = payload.get("release")
        if release is None:
            # No dialog when the application is already up to date.
            # Manual checks still show the current version.
            if not automatic:
                QMessageBox.information(
                    self,
                    "FinanceTerminal",
                    tr("Şu an güncelsiniz, {0} sürümünü kullanıyorsunuz.").format(self.VERSION)
                )
            return


        if not getattr(sys, "frozen", False):
            QMessageBox.information(
                self, tr("Yeni sürüm bulundu"),
                tr("FinanceTerminal {0} yayımlandı.\n\nKaynak kod modunda çalıştığınız için uygulama dosyası otomatik değiştirilemez. Windows EXE dosyasını buradan indirebilirsiniz:\n{1}").format(release.version, release.release_url)
            )
            return

        answer = ask_question(
            self, tr("FinanceTerminal güncellemesi bulundu"),
            tr("FinanceTerminal {0} sürümü bulundu.\n\nGüncelleme şimdi indirilsin ve uygulama yeniden başlatılarak kurulsun mu?\n\nPortföy kayıtlarınız ve ayarlarınız korunur. Güncelleme yalnızca uygulama EXE dosyasını değiştirir.").format(release.version),
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
            QMessageBox.warning(self, tr("Güncelleme yapılamıyor"), str(exc))
            return

        self._pending_update_release = release
        self._pending_update_automatic = automatic
        self._update_download_payload = None
        self._update_progress = QProgressDialog(self)
        self._update_progress.setWindowTitle(tr("FinanceTerminal güncellemesi indiriliyor"))
        self._update_progress.setLabelText(
            tr("FinanceTerminal {0} indiriliyor...\n0.0 MB / {1:.1f} MB  ·  %0.0\nOrtalama indirme hızı hesaplanıyor...").format(release.version, release.asset_size / 1_000_000)
        )
        self._update_progress.setRange(0, max(1, int(release.asset_size)))
        self._update_progress.setValue(0)
        self._update_progress.setCancelButton(None)
        self._update_progress.setMinimumDuration(0)
        self._update_progress.setAutoClose(False)
        self._update_progress.setAutoReset(False)
        self._update_progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._update_progress.setMinimumWidth(470)
        self._update_progress.resize(490, self._update_progress.sizeHint().height())
        self._update_progress.show()

        worker = UpdateDownloadWorker(release, self)
        self._update_download_worker = worker
        worker.progress.connect(self._on_update_download_progress)
        worker.completed.connect(self._store_update_download_result)
        worker.finished.connect(self._finish_update_download)
        worker.start()

    def _on_update_download_progress(self, received: int, total: int, speed_bps: float) -> None:
        """Show real byte progress and average download speed."""
        if self._update_progress is None:
            return
        total = max(1, int(total))
        received = max(0, min(int(received), total))
        percent = received * 100.0 / total
        received_mb = received / 1_000_000
        total_mb = total / 1_000_000
        speed_mbps = max(0.0, float(speed_bps)) / 1_000_000
        self._update_progress.setRange(0, total)
        self._update_progress.setValue(received)
        self._update_progress.setLabelText(
            tr("FinanceTerminal {0} indiriliyor...\n{1:.2f} MB / {2:.2f} MB  ·  %{3:.1f}\nOrtalama indirme hızı: {4:.2f} MB/sn").format(self._pending_update_release.version, received_mb, total_mb, percent, speed_mbps)
        )

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

        payload = self._update_download_payload or {"path": None, "error": tr("İndirme sonucu alınamadı.")}
        error = payload.get("error")
        if error:
            QMessageBox.warning(self, tr("Güncelleme indirilemedi"), str(error))
            return

        downloaded = Path(payload["path"])
        try:
            executable = current_executable_path()
            launch_windows_update_helper(
                downloaded,
                executable,
                expected_size=self._pending_update_release.asset_size,
            )
        except Exception as exc:
            try:
                downloaded.unlink(missing_ok=True)
            except OSError:
                pass
            QMessageBox.warning(self, tr("Güncelleme başlatılamadı"), str(exc))
            return

        QMessageBox.information(
            self, tr("Güncelleme hazır"),
            tr("FinanceTerminal {0} indirildi ve doğrulandı. Uygulama şimdi kapanacak. Güncelleyici eski EXE'yi yedekleyip yenisini kuracak; yeni sürüm açılmazsa eski sürüm otomatik geri yüklenecek.").format(self._pending_update_release.version)
        )
        self._force_exit = True
        self.close()

    # ---------------- FORMAT ----------------
    def fmt(self, v):
        if v is None:
            return "N/A"
        try:
            return format_localized(Decimal(str(v)), decimals=self.precision)
        except Exception:
            return "N/A"

    # ---------------- SYSTEM TRAY ----------------
    def _init_system_tray(self) -> None:
        """Prepare the tray icon and its menu; no background refresh is scheduled."""
        if not self._tray_available:
            return

        self._tray_icon = QSystemTrayIcon(
            QIcon(str(resource_path("assets/finance_terminal.png"))), self
        )
        self._tray_icon.setToolTip(tr("FinanceTerminal - Portföy takibi"))
        menu = QMenu(self)
        open_action = menu.addAction(tr("FinanceTerminal'ı Aç"))
        open_action.triggered.connect(self.restore_from_tray)
        menu.addSeparator()
        exit_action = menu.addAction(tr("Çıkış"))
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

    def _minimize_to_tray(self, notify: bool = True) -> None:
        if not self._tray_available or self._tray_icon is None:
            QMessageBox.information(
                self, tr("Sistem tepsisi kullanılamıyor"),
                tr("Bu Windows oturumunda sistem tepsisi kullanılamıyor. Uygulama kapatılacak.")
            )
            self._force_exit = True
            self.close()
            return

        self._in_tray = True
        self._tray_icon.show()
        self.hide()
        if not notify:
            return
        try:
            self._tray_icon.showMessage(
                tr("FinanceTerminal çalışıyor"),
                tr("FinanceTerminal sistem tepsisinde açık. Fiyatlar otomatik yenilenmez; güncelleme için uygulamayı açıp Güncelle'ye basın."),
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
        dialog.setWindowTitle(tr("FinanceTerminal açık kalsın mı?"))
        dialog.setIcon(QMessageBox.Icon.Question)
        dialog.setText(tr("Uygulamayı kapatmak yerine sistem tepsisine küçültmek ister misiniz?"))
        dialog.setInformativeText(
            tr("Evet seçerseniz uygulama arka planda açık kalır. Fiyatlar otomatik yenilenmez; yalnızca Güncelle düğmesine bastığınızda yenilenir.")
        )
        dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        localize_message_buttons(dialog)
        dialog.setDefaultButton(QMessageBox.StandardButton.Yes)
        remember = QCheckBox(tr("Bu tercihi hatırla ve tekrar sorma"))
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
                    self, tr("İşlem devam ediyor"),
                    tr("Güncelleme işlemi tamamlandıktan sonra uygulamayı kapatabilirsiniz.")
                )
                event.ignore()
                return

        worker = self.worker
        if worker is not None and worker.isRunning():
            self._close_after_update = True
            self.update_button.setEnabled(False)
            self.last.setText(tr("Güncelleme tamamlanınca uygulama kapanacak..."))
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

        try:
            bist_symbols = [
                str(row["symbol"]) for row in self.bist_portfolio.database.list_holdings()
            ]
        except Exception:
            # A database problem must never block currency/metal refresh.
            bist_symbols = []
        worker = Worker(self, bist_symbols=bist_symbols)
        self.worker = worker
        worker.result.connect(self.on_data)
        worker.finished.connect(self._on_update_finished)
        self.update_button.setEnabled(False)
        self.last.setText(tr("Güncelleniyor..."))
        if bist_symbols:
            self.bist_portfolio.set_refreshing(True)
        else:
            self.bist_portfolio.show_no_holdings()
        worker.start()

    def _on_update_finished(self):
        """Release the completed QThread safely on the GUI thread."""
        # Never leave the BIST button stuck on "Updating…", even if a provider failed.
        self.bist_portfolio.set_refreshing(False)
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

        for code, card in self.currency_cards.items():
            rate = d.get(code)
            if self.mode.currentData() == "reverse":
                card.title.setText(f"TRY/{code}")
                try:
                    inverse = 1 / float(rate) if rate is not None and float(rate) > 0 else None
                except (TypeError, ValueError, ZeroDivisionError):
                    inverse = None
                card.value.setText(self.fmt(inverse))
            else:
                card.title.setText(f"{code}/TRY")
                card.value.setText(self.fmt(rate))

        self.portfolio.set_rates(d)
        self.metals.set_rates(
            d.get("gold"),
            d.get("silver"),
            d.get("USD"),
            eur_try=d.get("EUR"),
            rates_updated_at=d.get("fetched_at"),
            rates_status=d.get("status"),
            rates=d,
        )
        self.bist_portfolio.rates_updated_at = d.get("fetched_at")
        self.bist_portfolio.rates_status = d.get("status")
        if "bist_quotes" in d:
            # Present only in the worker's second emission (after BIST prices
            # arrive); set_quotes also refreshes the summary.
            self.bist_portfolio.set_quotes(d.get("bist_quotes"))
        self.last.setText(d.get("status", "-"))
        self.refresh_summary()

    # ---------------- REFRESH ----------------
    def refresh(self):
        if hasattr(self, "last_data"):
            self.on_data(self.last_data)

    # ---------------- THEME ----------------
    def apply_theme(self):
        for card in getattr(self, "currency_cards", {}).values():
            card.apply_theme(self.theme)
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
                QGroupBox#investmentPanel { background:#ffffff; border:1px solid #cbd5e1; border-radius:10px; margin-top:14px; padding:14px 10px 10px 10px; }
                QGroupBox#investmentPanel::title { color:#172033; left:12px; padding:0 6px; font-weight:700; }
                QLabel#investmentInfo { color:#64748b; }
                QLabel#investmentLastUpdate { color:#475569; font-size:10px; }
                QTableWidget#investmentTable { background:#ffffff; alternate-background-color:#f5f7fb; color:#172033; border:0; gridline-color:transparent; selection-background-color:#dbeafe; selection-color:#172033; }
                QTableWidget#investmentTable::item { padding:6px 5px; border-bottom:1px solid #edf0f5; }
                QTableWidget#investmentTable QHeaderView::section { background:#e9eef6; color:#1e293b; border:0; border-bottom:2px solid #cbd5e1; padding:9px 6px; font-weight:700; }
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
                QGroupBox#investmentPanel { background:#142238; border:1px solid #35547e; border-radius:10px; margin-top:14px; padding:14px 10px 10px 10px; }
                QGroupBox#investmentPanel::title { color:#eef5ff; left:12px; padding:0 6px; font-weight:700; }
                QLabel#investmentInfo { color:#b6c8e2; }
                QLabel#investmentLastUpdate { color:#9fb6d5; font-size:10px; }
                QTableWidget#investmentTable { background:#17243a; alternate-background-color:#1c2c45; color:#f4f8ff; border:0; gridline-color:transparent; selection-background-color:#315b88; selection-color:#ffffff; }
                QTableWidget#investmentTable::item { padding:6px 5px; border-bottom:1px solid #263d5e; }
                QTableWidget#investmentTable QHeaderView::section { background:#223b61; color:#ffffff; border:0; border-bottom:2px solid #3a86ff; padding:9px 6px; font-weight:700; }
            """)
        elif self.theme in EXTRA_THEMES:
            self.setStyleSheet(build_stylesheet(EXTRA_THEMES[self.theme]))
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
                QGroupBox#investmentPanel { background:#191e26; border:1px solid #3b4553; border-radius:10px; margin-top:14px; padding:14px 10px 10px 10px; }
                QGroupBox#investmentPanel::title { color:#f4f6f8; left:12px; padding:0 6px; font-weight:700; }
                QLabel#investmentInfo { color:#b5becb; }
                QLabel#investmentLastUpdate { color:#a1aab7; font-size:10px; }
                QTableWidget#investmentTable { background:#1b1f25; alternate-background-color:#222832; color:#f4f6f8; border:0; gridline-color:transparent; selection-background-color:#315b88; selection-color:#ffffff; }
                QTableWidget#investmentTable::item { padding:6px 5px; border-bottom:1px solid #303844; }
                QTableWidget#investmentTable QHeaderView::section { background:#29313c; color:#f4f6f8; border:0; border-bottom:2px solid #60a5fa; padding:9px 6px; font-weight:700; }
            """)

    # ---------------- SETTINGS ----------------
    def open_settings(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("Ayarlar"))
        dlg.setMinimumWidth(320)

        layout = QVBoxLayout()
        version = QLabel(tr("Sürüm: {0}").format(self.VERSION))

        language = QComboBox()
        language.addItem("Türkçe", "tr")  # language names stay in their own language
        language.addItem("English", "en")
        language.setCurrentIndex(max(0, language.findData(get_language())))

        start_tab = QComboBox()
        start_tab.addItems([tr("Özet"), tr("Döviz"), tr("Portföy"), tr("Metaller"), tr("BIST AI")])
        start_tab.setCurrentIndex(self.tabs.currentIndex())

        precision = QComboBox()
        precision.addItems(["2", "3", "4"])
        precision.setCurrentText(str(self.precision))

        theme = QComboBox()
        theme.addItem(tr("Windows ayarını takip et"), "System")
        theme.addItem(tr("Açık tema"), "White")
        theme.addItem(tr("Koyu tema"), "Dark")
        theme.addItem(tr("Mavi tema"), "Blue")
        theme.addItem(tr("Gece yarısı teması (tam siyah)"), "Midnight")
        theme.addItem(tr("Zümrüt teması (yeşil)"), "Emerald")
        theme_index = theme.findData(self.theme_preference)
        theme.setCurrentIndex(theme_index if theme_index >= 0 else 0)

        btn = QPushButton(tr("Kaydet"))
        close_behavior = QComboBox()
        close_behavior.addItem(tr("Her kapatmada sor"), "ask")
        close_behavior.addItem(tr("Sistem tepsisine küçült"), "tray")
        close_behavior.addItem(tr("Uygulamayı tamamen kapat"), "exit")
        saved_close = self.settings.get("close_to_tray", None)
        close_key = "ask" if saved_close is None else ("tray" if bool(saved_close) else "exit")
        close_index = close_behavior.findData(close_key)
        close_behavior.setCurrentIndex(close_index if close_index >= 0 else 0)

        auto_update = QCheckBox(
            tr("Başlangıçta güncellemeleri kontrol et (yeni sürüm bulunursa önce sor)")
        )
        auto_update.setChecked(bool(self.settings.get("auto_update_check", False)))
        update_btn = QPushButton(tr("Güncellemeleri Kontrol Et"))

        autostart_supported = autostart.is_supported()
        autostart_box = QCheckBox(tr("Bilgisayar açıldığında FinanceTerminal otomatik başlasın"))
        start_in_tray = QCheckBox(tr("Otomatik başlarken pencere açılmasın, sistem tepsisinde başlasın"))
        if autostart_supported:
            autostart_box.setChecked(autostart.is_enabled())
        else:
            autostart_box.setEnabled(False)
            autostart_box.setToolTip(tr("Bu seçenek yalnızca Windows'ta kurulu (EXE) sürümde kullanılabilir."))
        start_in_tray.setChecked(bool(self.settings.get("start_in_tray", False)))
        tray_possible = bool(self._tray_available and autostart_supported)
        start_in_tray.setEnabled(tray_possible and autostart_box.isChecked())
        autostart_box.toggled.connect(lambda checked: start_in_tray.setEnabled(tray_possible and checked))

        help_btn = QPushButton(tr("Yardım / Kullanım Kılavuzu"))
        help_btn.clicked.connect(lambda: self.open_help(dlg))

        def save_all():
            self.precision = int(precision.currentText())
            self.tabs.setCurrentIndex(start_tab.currentIndex())
            self.theme_preference = str(theme.currentData() or "System")
            self.theme = resolve_theme(self.theme_preference)

            new_language = normalize_language(language.currentData())
            language_changed = new_language != get_language()
            self.settings["language"] = new_language
            self.settings["precision"] = self.precision
            self.settings["start_tab"] = self.tabs.currentIndex()
            self.settings["theme"] = self.theme_preference
            self.settings["summary_tab_migrated"] = True
            self.settings["auto_update_check"] = auto_update.isChecked()
            if autostart_supported:
                self._apply_autostart_choice(autostart_box.isChecked(), parent=dlg)
            self.settings["start_in_tray"] = start_in_tray.isChecked()
            close_choice = close_behavior.currentData()
            self.settings["close_to_tray"] = (
                None if close_choice == "ask" else close_choice == "tray"
            )
            self.apply_theme()
            save(self.settings)
            dlg.accept()
            if language_changed:
                # Texts are built once per window, so the new language applies after a restart.
                QTimer.singleShot(150, lambda: self._offer_restart_for_language(new_language))

        btn.clicked.connect(save_all)

        def manual_update_check():
            # Checking for updates must never apply settings the user has not saved:
            # close the dialog WITHOUT saving, then run the check.
            dlg.reject()
            QTimer.singleShot(0, lambda: self.check_for_updates(automatic=False))

        update_btn.clicked.connect(manual_update_check)
        layout.addWidget(version)
        layout.addWidget(QLabel(tr("Dil")))
        layout.addWidget(language)
        layout.addWidget(QLabel(tr("Başlangıç Sekmesi")))
        layout.addWidget(start_tab)
        layout.addWidget(QLabel(tr("Hassasiyet")))
        layout.addWidget(precision)
        layout.addWidget(QLabel(tr("Tema")))
        layout.addWidget(theme)
        layout.addWidget(QLabel(tr("Pencereyi X ile kapatınca")))
        layout.addWidget(close_behavior)
        layout.addWidget(auto_update)
        layout.addWidget(autostart_box)
        layout.addWidget(start_in_tray)
        layout.addWidget(QLabel(
            tr("Yeni sürüm bulunduğunda indirme ve kurulum için ayrıca onayınız istenir. Kişisel portföy verileri %APPDATA%\\FinanceTerminal altında saklanır.")
        ))
        layout.addWidget(btn)
        layout.addWidget(update_btn)
        layout.addWidget(help_btn)
        dlg.setLayout(layout)
        dlg.exec()

    # ---------------- LANGUAGE ----------------
    def _offer_restart_for_language(self, language: str) -> None:
        """Offer to restart now; the prompt is already written in the newly chosen language."""
        def t(text: str) -> str:
            return translate(text, language)

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Information)
        box.setWindowTitle(t(tr_noop("Dil değiştirildi")))
        box.setText(t(tr_noop("Dil değişikliği uygulama yeniden başlatılınca geçerli olur. Şimdi yeniden başlatılsın mı?")))
        restart_button = box.addButton(t(tr_noop("Şimdi Yeniden Başlat")), QMessageBox.ButtonRole.AcceptRole)
        box.addButton(t(tr_noop("Daha Sonra")), QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(restart_button)
        box.exec()
        if box.clickedButton() is restart_button and not self.restart_application():
            QMessageBox.warning(
                self, t(tr_noop("Dil değiştirildi")),
                t(tr_noop("Uygulama yeniden başlatılamadı. Lütfen FinanceTerminal'ı kapatıp elle yeniden açın.")),
            )

    def restart_application(self) -> bool:
        """Start a fresh copy, then close this one. Returns False if it could not restart."""
        from core.restart import restart_command, spawn_detached

        for update_worker in (self._update_check_worker, self._update_download_worker):
            if update_worker is not None and update_worker.isRunning():
                return False  # never interrupt an update
        single = getattr(self, "single_instance", None)
        if single is not None:
            single.close()  # release the lock so the new copy becomes the primary one
        program, arguments = restart_command()
        if not spawn_detached(program, arguments):
            return False
        self.exit_from_tray()
        return True

    def open_help(self, parent=None):
        """Show a concise, built-in guide for the application tabs."""
        dlg = QDialog(parent or self)
        dlg.setWindowTitle(tr("FinanceTerminal - Kullanım Kılavuzu"))
        dlg.resize(620, 560)

        layout = QVBoxLayout(dlg)
        browser = QTextBrowser(dlg)
        browser.setOpenExternalLinks(True)
        browser.setHtml(help_html())
        close_btn = QPushButton(tr("Kapat"), dlg)
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(browser)
        layout.addWidget(close_btn)
        dlg.exec()
