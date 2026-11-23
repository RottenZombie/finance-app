from __future__ import annotations

from datetime import datetime

from core.timefmt import format_local
import re
import unicodedata

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from core.i18n import tr

CURRENCY_SOURCE_URL = "https://www.exchangerate-api.com/"
GOLD_SOURCE_URL = "https://gold-api.com/"
SILVER_SOURCE_URL = "https://gold-api.com/"


def local_timestamp() -> str:
    return format_local(datetime.now())


def profile_export_filename(profile_name: str, profile_id: str | None = None) -> str:
    """Return a filesystem-safe, profile-specific combined workbook name."""
    raw = str(profile_name or "Profil").strip() or "Profil"
    raw = raw.translate(str.maketrans({"ı": "i", "İ": "I"}))
    folded = unicodedata.normalize("NFKD", raw)
    ascii_name = "".join(char for char in folded if not unicodedata.combining(char))
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", ascii_name).strip("_") or "Profil"
    identity = str(profile_id or "").strip().lower()
    prefix = f"{identity.title()}_" if identity in {"profile1", "profile2", "profile3"} else ""
    return f"FinanceTerminal_{prefix}{slug}_Tum_Portfoy.xlsx"


def add_export_metadata_sheet(
    workbook: Workbook,
    *,
    rates_updated_at: str | None = None,
    rates_status: str | None = None,
    include_bist_note: bool = True,
    profile_name: str | None = None,
) -> None:
    """Append a human-readable provenance sheet without changing import headers."""
    sheet = workbook.create_sheet(tr("Veri Bilgisi"))
    sheet.append([tr("FinanceTerminal | Dışa Aktarım Bilgileri"), ""])
    sheet.append([tr("Excel oluşturulma zamanı"), local_timestamp()])
    sheet.append([tr("Uygulamada son veri güncelleme zamanı"), rates_updated_at or "Bilinmiyor"])
    sheet.append([tr("Döviz veri bağlantı durumu"), rates_status or "Bilinmiyor"])
    sheet.append([tr("Döviz kuru kaynağı"), tr("ExchangeRate-API | USD bazlı TRY, EUR ve HUF kurları (ulaşılamazsa yedek: TCMB günlük kurları)")])
    sheet.append([tr("Döviz sağlayıcı sitesi"), CURRENCY_SOURCE_URL])
    sheet.append([tr("Altın fiyat kaynağı"), tr("Gold API | XAU (USD / troy ons)")])
    sheet.append([tr("Altın sağlayıcı sitesi"), GOLD_SOURCE_URL])
    sheet.append([tr("Gümüş fiyat kaynağı"), tr("Gold API | XAG (USD / troy ons)")])
    sheet.append([tr("Gümüş sağlayıcı sitesi"), SILVER_SOURCE_URL])
    if include_bist_note:
        sheet.append([tr("Hisse fiyat bilgisi"), tr("BIST hisse fiyatları gecikmeli ve resmi olmayan kaynaklardan (Yahoo Finance, yedek: İş Yatırım) alınır. Fiyatı alınamayan hisseler kayıtlı alış maliyetiyle gösterilir ve kâr/zarara dahil edilmez.")])
    sheet.append(["Not", tr("Fiyatlar dışa aktarım sırasında uygulamada bulunan son veri değerleridir; bu dosya fiyat geçmişi oluşturmaz.")])
    if profile_name:
        sheet.append([tr("Bu dosyanın ait olduğu profil"), profile_name])

    sheet.merge_cells("A1:B1")
    sheet["A1"].font = Font(size=15, bold=True, color="FFFFFF")
    sheet["A1"].fill = PatternFill("solid", fgColor="203864")
    sheet["A1"].alignment = Alignment(vertical="center")
    sheet.row_dimensions[1].height = 25
    for row in range(2, sheet.max_row + 1):
        sheet.cell(row, 1).font = Font(bold=True, color="203864")
        sheet.cell(row, 1).alignment = Alignment(vertical="top", wrap_text=True)
        sheet.cell(row, 2).alignment = Alignment(vertical="top", wrap_text=True)
    for cell_ref in ("B6", "B8", "B10"):
        cell = sheet[cell_ref]
        if cell.value:
            cell.hyperlink = str(cell.value)
            cell.style = "Hyperlink"
    sheet.column_dimensions[get_column_letter(1)].width = 38
    sheet.column_dimensions[get_column_letter(2)].width = 88
    sheet.sheet_view.showGridLines = False
    sheet.freeze_panes = "A2"
