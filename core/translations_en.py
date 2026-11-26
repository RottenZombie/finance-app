"""English translations for every Turkish source text passed to tr()/tr_noop().

Keys are the exact Turkish source strings; ``{0}``-style placeholders must be
identical in both languages (a unit test checks this). Run
``python tools/i18n_keys.py`` to list texts that still lack an entry.
"""
from __future__ import annotations

EN: dict[str, str] = {
    'FinanceTerminal başlatılamadı':
        'FinanceTerminal could not start',
    'Tek uygulama örneği başlatılamadı. Bilgisayarınızı yeniden başlatıp tekrar deneyin.\n\n':
        'The single-instance lock could not be created. Restart your computer and try again.\n\n',
    'Online (TCMB yedek)':
        'Online (TCMB fallback)',
    'Geçersiz FinanceTerminal profili.':
        'Invalid FinanceTerminal profile.',
    'altın':
        'gold',
    'gümüş':
        'silver',
    'Offline (önbellek: {0})':
        'Offline (cache: {0})',
    '{0} · {1} önbellekten':
        '{0} · {1} from cache',
    'GitHub sürüm yanıtı beklenen biçimde değil.':
        'The GitHub release response is not in the expected format.',
    'GitHub sürüm etiketi bulunamadı.':
        'The GitHub release tag was not found.',
    'GitHub sürümünde indirilebilir dosya listesi bulunamadı.':
        'No downloadable file list was found in the GitHub release.',
    'Güncelleme bağlantısı beklenen GitHub depo adresinden gelmiyor.':
        'The update link does not come from the expected GitHub repository.',
    'Güncelleme dosyasının boyutu geçerli aralıkta değil.':
        'The update file size is outside the valid range.',
    'Bu sürümde SHA-256 özeti bulunmadığı için dosya doğrulanamadı ve otomatik kurulum yapılmadı. Güncellemeyi GitHub sürüm sayfasından elle indirebilirsiniz.':
        'This release has no SHA-256 digest, so the file could not be verified and automatic installation was not performed. You can download the update manually from the GitHub release page.',
    'Otomatik kurulum yalnızca yayımlanmış Windows EXE sürümünde kullanılabilir.':
        'Automatic installation is only available in the published Windows EXE.',
    'Çalışan FinanceTerminal.exe yolu belirlenemedi.':
        'The path of the running FinanceTerminal.exe could not be determined.',
    "Otomatik EXE değiştirme yalnızca Windows'ta kullanılabilir.":
        'Automatic EXE replacement is only available on Windows.',
    'Güncelleme sunucusuna ulaşılamadı. İnternet bağlantınızı kontrol edin.':
        'The update server could not be reached. Check your internet connection.',
    "GitHub'dan gelen sürüm bilgisi okunamadı.":
        'The release information from GitHub could not be read.',
    'İndirilen dosyanın SHA-256 doğrulaması başarısız.':
        'SHA-256 verification of the downloaded file failed.',
    "Uygulamanın bulunduğu klasöre yazma izni yok. EXE'yi yazma izniniz olan bir klasöre taşıyın veya güncellemeyi GitHub'dan elle indirin.":
        "There is no write permission for the application's folder. Move the EXE to a folder you can write to, or download the update manually from GitHub.",
    'Geçersiz sürüm numarası: {0}':
        'Invalid version number: {0}',
    'Yeni sürüm {0} bulundu ancak {1} dosyası eklenmemiş.':
        'New version {0} was found, but the {1} file is not attached.',
    'İndirilen dosya geçerli bir Windows EXE dosyası değil.':
        'The downloaded file is not a valid Windows EXE.',
    'Güncelleme yardımcısı başlatıldı ancak hemen kapandı. Ayrıntılı günlük: {0}':
        'The updater helper started but closed immediately. Detailed log: {0}',
    'GitHub güncelleme kontrolü başarısız (HTTP {0}).':
        'The GitHub update check failed (HTTP {0}).',
    'İndirilen dosyanın boyutu uyuşmuyor (beklenen {0}, gelen {1}).':
        'The downloaded file size does not match (expected {0}, received {1}).',
    'PowerShell yardımcısı başlatılamadı: {0}':
        'The PowerShell helper could not be started: {0}',
    'Güncelleme yardımcısı başlatılamadı: {0}':
        'The update helper could not be started: {0}',
    'İndirilen dosya beklenen boyutu aşıyor.':
        'The downloaded file exceeds the expected size.',
    'Ortalama maliyet':
        'Average cost',
    'Adet sıfırdan büyük olmalıdır.':
        'Quantity must be greater than zero.',
    'Ortalama maliyet negatif olamaz.':
        'Average cost cannot be negative.',
    'Düzenlenecek kayıt bulunamadı: {0}':
        'The record to edit was not found: {0}',
    '{0} koduyla başka bir kayıt zaten mevcut. Mevcut kaydı ezmemek için değişiklik yapılmadı.':
        'Another record with the code {0} already exists. No change was made so the existing record is not overwritten.',
    'Satır {0}: {1}':
        'Row {0}: {1}',
    'BIST Portföy':
        'BIST Portfolio',
    'Hisse Kodu':
        'Symbol',
    'Şirket Adı':
        'Company',
    'Adet':
        'Quantity',
    'Ortalama Maliyet (TL)':
        'Average Cost (TRY)',
    'Toplam Maliyet (TL)':
        'Total Cost (TRY)',
    'Sektör':
        'Sector',
    'Notlar':
        'Notes',
    'Toplam Maliyet':
        'Total Cost',
    'Hesaplama zamanı':
        'Calculated at',
    'Güncel Fiyat (TL)':
        'Current Price (TRY)',
    'Güncel Değer (TL)':
        'Current Value (TRY)',
    'Kâr / Zarar (TL)':
        'Profit / Loss (TRY)',
    'Kâr / Zarar (%)':
        'Profit / Loss (%)',
    'Fiyat Kaynağı / Zamanı':
        'Price Source / Time',
    'Güncel Değer (fiyatı alınan hisseler)':
        'Current Value (shares with a price)',
    'Ortalama Maliyet':
        'Average Cost',
    ' (kâr/zarar yalnızca fiyatı alınan hisseleri kapsar)':
        ' (profit/loss covers only the shares that have a price)',
    'Gerekli BIST sütunlarını içeren sayfa bulunamadı: ':
        'No sheet containing the required BIST columns was found: ',
    '⚠ Fiyatı alınamayan hisseler: ':
        '⚠ Shares whose price could not be fetched: ',
    'Fiyat alınamadı':
        'Price unavailable',
    'Hisse':
        'Stock',
    'Şirket':
        'Company',
    'Ort. maliyet':
        'Avg. cost',
    'Toplam maliyet':
        'Total cost',
    'Güncel fiyat':
        'Current price',
    'Piyasa değeri':
        'Market value',
    'K/Z (TL)':
        'P/L (TRY)',
    'K/Z %':
        'P/L %',
    'Not':
        'Note',
    'Son güncelleme':
        'Last updated',
    'Fiyatlar gecikmeli ve resmi olmayan kaynaklardan alınır; yatırım tavsiyesi değildir. KAP taraması ve yapay zekâ analizleri sonraki aşamada eklenecek.':
        'Prices are delayed and come from unofficial sources; this is not investment advice. KAP scanning and AI analysis will be added in a later stage.',
    'BIST AI · Portföy':
        'BIST AI · Portfolio',
    'Hisselerini kaydet, maliyetini takip et ve analiz modüllerine hazırla.':
        'Record your shares, track their cost and get ready for the analysis modules.',
    'Veriler bu bilgisayarda saklanır':
        'Data is stored on this computer',
    'Hisse sayısı':
        'Number of shares',
    'Fiyat yok':
        'No price',
    'Veri yok':
        'No data',
    'Hisse kaydı':
        'Add a stock',
    'Örn. ASELS':
        'e.g. ASELS',
    'Şirket adı (isteğe bağlı)':
        'Company name (optional)',
    'Örn. 250':
        'e.g. 250',
    'Örn. 74,50':
        'e.g. 74.50',
    'Örn. Savunma':
        'e.g. Defense',
    'İsteğe bağlı not':
        'Optional note',
    'Ekle / Güncelle':
        'Add / Update',
    'Formu Temizle':
        'Clear Form',
    'Seçili Kayıtları Sil':
        'Delete Selected',
    'Tüm Kayıtları Sil':
        'Delete All',
    'Fiyatları Güncelle':
        'Update Prices',
    "Excel'den İçe Aktar":
        'Import from Excel',
    "Excel'e Aktar":
        'Export to Excel',
    'Şirket adı':
        'Company name',
    'Hisse kodu *':
        'Symbol *',
    'Ortalama maliyet (TL) *':
        'Average cost (TRY) *',
    'Hisse kodu dâhil tüm giriş alanlarını bu pencereden değiştirebilirsiniz.':
        'You can change every field, including the symbol, in this window.',
    'Değişiklikleri Kaydet':
        'Save Changes',
    'Seçili kayıtları sil':
        'Delete selected records',
    'Tüm BIST kayıtlarını sil':
        'Delete all BIST records',
    'Portföy Excel dosyasını seç':
        'Select the portfolio Excel file',
    'Excel dosyaları (*.xlsx)':
        'Excel files (*.xlsx)',
    'BIST portföyü':
        'BIST portfolio',
    'Portföyü Excel olarak kaydet':
        'Save portfolio as Excel',
    'Adet *':
        'Quantity *',
    ' (kısmi)':
        ' (partial)',
    'Önce tablodan bir veya daha fazla hisse seç.':
        'First select one or more shares in the table.',
    'Tüm kayıtları sil':
        'Delete all records',
    'BIST portföyünde silinecek kayıt yok.':
        'There are no records to delete in the BIST portfolio.',
    'Dışa aktarılacak kayıt bulunmuyor.':
        'There are no records to export.',
    'Dışa aktarma tamamlandı':
        'Export completed',
    'Güncel fiyatlar için "Fiyatları Güncelle" düğmesini kullanın. ':
        'Use the "Update Prices" button to fetch current prices. ',
    'fiyat alınamayan: ':
        'price unavailable: ',
    'Kayıt yapılamadı':
        'Could not save the record',
    '{0} kaydını düzenle':
        'Edit {0}',
    'Kayıt güncellenemedi':
        'Could not update the record',
    '{0} seçili hisse kaydı silinecek:\n{1}\n\nDevam edilsin mi?':
        '{0} selected stock records will be deleted:\n{1}\n\nDo you want to continue?',
    '{0} hisse kaydının tamamı kalıcı olarak silinecek.\n\nBu işlem geri alınamaz. Devam edilsin mi?':
        'All {0} stock records will be deleted permanently.\n\nThis cannot be undone. Do you want to continue?',
    '{0} kayıt içe aktarıldı.':
        '{0} records imported.',
    '\n\nAtlanan satırlar:\n':
        '\n\nSkipped rows:\n',
    'İçe aktarma tamamlandı':
        'Import completed',
    'Excel okunamadı':
        'The Excel file could not be read',
    'BIST portföyü örnek şablonunu kaydet':
        'Save the BIST portfolio sample template',
    'BIST_Portfoy.xlsx':
        'BIST_Portfolio.xlsx',
    'Excel kaydedilemedi':
        'The Excel file could not be saved',
    '{0} hisse güncel':
        '{0} shares up to date',
    '{0} hisse önbellekten (eski fiyat)':
        '{0} shares from cache (old price)',
    '{0} kaydı kaydedildi.':
        '{0} was saved.',
    '{0} kaydı güncellendi.':
        '{0} was updated.',
    'Dosya kaydedildi:\n{0}':
        'File saved:\n{0}',
    '{0} ₺ (kısmi: {1}/{2})':
        '{0} ₺ (partial: {1}/{2})',
    '\n... ve {0} hata daha.':
        '\n... and {0} more errors.',
    'Kaynak: {0}\nFiyat zamanı: {1}':
        'Source: {0}\nPrice time: {1}',
    ' (eski fiyat)':
        ' (old price)',
    'Değer':
        'Value',
    'Hisse kodu 2–12 karakterli harf/rakam içermelidir.':
        'The symbol must be 2–12 characters of letters/digits.',
    '{0} sonlu bir sayı olmalı.':
        '{0} must be a finite number.',
    '{0} boş bırakılamaz.':
        '{0} cannot be empty.',
    '{0} geçerli bir sayı değil: {1}':
        '{0} is not a valid number: {1}',
    'Dosyada tanınan portföy sayfası bulunamadı. Beklenen sayfalar: Döviz, Maden ve Hisse Senedi.':
        'No recognised portfolio sheet was found in the file. Expected sheets: Currency, Metals and Stocks.',
    'Altın':
        'Gold',
    'Gümüş':
        'Silver',
    'Verilerimi Aktar: kayıtlarınız ve dışa aktarma anındaki fiyat / kâr-zarar değerleri.\nÖrnek Şablon İndir: aynı düzende, her sayfada tek örnek satır içeren dosya. Örneği kendi verinizle değiştirip içe aktarabilirsiniz.':
        'Export My Data: your records with the prices and profit/loss at the time of export.\nDownload Sample Template: a file in the same layout with one example row per sheet. You can replace the example with your own data and import it.',
    'Verilerimi Aktar':
        'Export My Data',
    'Örnek Şablon İndir':
        'Download Sample Template',
    'İptal':
        'Cancel',
    'Örnek şablon kaydedildi':
        'Sample template saved',
    '{0} için ne yapmak istersiniz?':
        'What would you like to do for {0}?',
    'Şablon kaydedilemedi':
        'The template could not be saved',
    'Dosya kaydedildi:\n{0}\n\nÖrnek satırı kendi verinizle değiştirip "Excel\'den İçe Aktar" ile yükleyebilirsiniz.':
        'File saved:\n{0}\n\nReplace the example row with your own data and load it with "Import from Excel".',
    'Veri Bilgisi':
        'Data Info',
    'FinanceTerminal | Dışa Aktarım Bilgileri':
        'FinanceTerminal | Export Information',
    'Excel oluşturulma zamanı':
        'Excel created at',
    'Uygulamada son veri güncelleme zamanı':
        'Last data refresh in the application',
    'Döviz veri bağlantı durumu':
        'Currency data connection status',
    'Döviz kuru kaynağı':
        'Currency rate source',
    'ExchangeRate-API | USD bazlı TRY, EUR ve HUF kurları (ulaşılamazsa yedek: TCMB günlük kurları)':
        'ExchangeRate-API | USD-based TRY, EUR and HUF rates (fallback if unreachable: TCMB daily rates)',
    'Döviz sağlayıcı sitesi':
        'Currency provider website',
    'Altın fiyat kaynağı':
        'Gold price source',
    'Gold API | XAU (USD / troy ons)':
        'Gold API | XAU (USD / troy ounce)',
    'Altın sağlayıcı sitesi':
        'Gold provider website',
    'Gümüş fiyat kaynağı':
        'Silver price source',
    'Gold API | XAG (USD / troy ons)':
        'Gold API | XAG (USD / troy ounce)',
    'Gümüş sağlayıcı sitesi':
        'Silver provider website',
    'Fiyatlar dışa aktarım sırasında uygulamada bulunan son veri değerleridir; bu dosya fiyat geçmişi oluşturmaz.':
        'Prices are the latest values held in the application at export time; this file does not build a price history.',
    'Hisse fiyat bilgisi':
        'Share price information',
    'BIST hisse fiyatları gecikmeli ve resmi olmayan kaynaklardan (Yahoo Finance, yedek: İş Yatırım) alınır. Fiyatı alınamayan hisseler kayıtlı alış maliyetiyle gösterilir ve kâr/zarara dahil edilmez.':
        'BIST share prices are delayed and come from unofficial sources (Yahoo Finance, fallback: İş Yatırım). Shares whose price could not be fetched are shown at their recorded purchase cost and are excluded from profit/loss.',
    'Bu dosyanın ait olduğu profil':
        'Profile this file belongs to',
    'Örnek şablon (gerçek veri değildir)':
        'Sample template (not real data)',
    'Savunma':
        'Defense',
    'Örnek kayıt - kendi verinizle değiştirin':
        'Sample record - replace with your own data',
    'Döviz Portföyü':
        'Currency Portfolio',
    'Metal Portföyü':
        'Metals Portfolio',
    'Geçersiz portföy türü.':
        'Invalid portfolio type.',
    'Örnek fiyat':
        'Sample price',
    'Hisse Senedi':
        'Stocks',
    'Kayıtlı alış maliyeti (kayıt yok)':
        'Recorded purchase cost (no records)',
    'EUR ve USD karşılıkları dışa aktarma anındaki döviz kurlarıyla çevrilmiştir.':
        'EUR and USD equivalents were converted using the exchange rates at the time of export.',
    'İlgili fiyat veya kur verisi yoksa grup ve genel toplam değerleri eksik hesaplanmaması için boş bırakılır.':
        'If the related price or rate is missing, group and grand totals are left blank so they are not calculated incompletely.',
    'Varlık':
        'Asset',
    'Ortalama Alış Fiyatı (₺)':
        'Average Purchase Price (TRY)',
    'Toplam Maliyet (₺)':
        'Total Cost (TRY)',
    'Güncel Birim Fiyat (₺)':
        'Current Unit Price (TRY)',
    'Güncel Değer (₺)':
        'Current Value (TRY)',
    'FinanceTerminal | Portföy Özeti':
        'FinanceTerminal | Portfolio Summary',
    'Anlık kayıt özeti. Döviz, maden ve fiyatı alınabilen hisseler güncel fiyatla; fiyatı alınamayan hisseler kayıtlı alış maliyetiyle hesaplanır. Kâr/zarar dışa aktarma anındaki fiyatlara göredir.':
        'Snapshot of your records. Currencies, metals and shares with an available price use the current price; shares without a price use their recorded purchase cost. Profit/loss is based on the prices at the time of export.',
    'Portföy':
        'Portfolio',
    'Hesaplama Esası':
        'Basis',
    'Döviz':
        'Currency',
    'Ortalama Maliyet (₺)':
        'Average Cost (TRY)',
    'Kayıtlı Maliyet (₺)':
        'Recorded Cost (TRY)',
    'Güncel Fiyat (₺)':
        'Current Price (TRY)',
    'Güncel piyasa değeri':
        'Current market value',
    'GENEL TOPLAM':
        'GRAND TOTAL',
    'Döviz + maden + hisse (hisse: güncel fiyat varsa piyasa değeri, yoksa maliyet)':
        'Currency + metals + stocks (stocks: market value if a price exists, otherwise cost)',
    'Hisse fiyatları gecikmeli ve resmi olmayan kaynaklardan alınır. Genel toplam, tüm grupların değerleri mevcutsa hesaplanır.':
        'Share prices are delayed and come from unofficial sources. The grand total is calculated only if the values of all groups are available.',
    'Uygun portföy sayfası veya gerekli sütunlar bulunamadı.':
        'No suitable portfolio sheet or required columns were found.',
    'Bu dosya şu profile aittir':
        'This file belongs to the profile',
    'Kısmen güncel değer (fiyatı alınamayanlar alış maliyetiyle)':
        'Partly current value (shares without a price at purchase cost)',
    'Kayıtlı alış maliyeti (güncel fiyat alınamadı)':
        'Recorded purchase cost (no current price available)',
    '. Bu hisseler alış maliyetiyle toplandı ve kâr/zarara dahil edilmedi.':
        '. These shares were added at purchase cost and excluded from profit/loss.',
    'İçe aktarılabilir kayıt bulunamadı.\n':
        'No importable records were found.\n',
    '⚠ Şu hisse senetlerinin fiyatı alınamadı: ':
        '⚠ Shares whose price could not be fetched: ',
    'Ortalama alış fiyatı':
        'Average purchase price',
    'Miktar ve ortalama alış fiyatı sıfırdan büyük olmalıdır.':
        'Quantity and average purchase price must be greater than zero.',
    'Satır {0}: Bu bölümde desteklenmeyen varlık kodu: {1}':
        'Row {0}: Unsupported asset code in this section: {1}',
    'Miktar':
        'Quantity',
    'Ort. Alış (₺)':
        'Avg. Purchase (TRY)',
    'Kâr / Zarar (₺)':
        'Profit / Loss (TRY)',
    'Örn. 10':
        'e.g. 10',
    'Örn. 32,50':
        'e.g. 32.50',
    'Alımı Kaydet':
        'Save Purchase',
    'Aynı varlığa yapılan yeni alımlar miktara eklenir ve ağırlıklı ortalama maliyet güncellenir.':
        'New purchases of the same asset are added to the quantity and the weighted average cost is updated.',
    'Son güncelleme: Henüz veri alınmadı':
        'Last updated: no data received yet',
    'Henüz veri alınmadı':
        'No data received yet',
    'Örn. 10,5':
        'e.g. 10.5',
    'Örn. 3.250,00':
        'e.g. 3,250.00',
    'Ortalama alış birim fiyatı (₺)':
        'Average purchase unit price (TRY)',
    'Döviz portföyü':
        'Currency portfolio',
    'Metal portföyü':
        'Metals portfolio',
    'Alış birim fiyatı (₺)':
        'Purchase unit price (TRY)',
    'Kayıt başarılı':
        'Saved',
    'Kayıt bulunamadı':
        'Record not found',
    'Düzenlenecek kayıt artık mevcut değil.':
        'The record to edit no longer exists.',
    'Kayıt güncellendi':
        'Record updated',
    'Kayıt sil':
        'Delete records',
    'Önce tablodan bir veya daha fazla kayıt seç.':
        'First select one or more records in the table.',
    '\n\nDevam edilsin mi?':
        '\n\nDo you want to continue?',
    'Bu bölümde silinecek kayıt yok.':
        'There are no records to delete in this section.',
    'İçe aktarmayı onayla':
        'Confirm import',
    'Dışa aktarma':
        'Export',
    'Son güncelleme: {0}  |  Veri durumu: {1}':
        'Last updated: {0}  |  Data status: {1}',
    'Alış birim fiyatı':
        'Purchase unit price',
    '{0} {1} kaydının tamamı kalıcı olarak silinecek.\n\nBu işlem geri alınamaz. Devam edilsin mi?':
        'All {0} {1} records will be deleted permanently.\n\nThis cannot be undone. Do you want to continue?',
    'İçe aktarma':
        'Import',
    'İçe aktarılacak kayıt bulunamadı.':
        'No records to import were found.',
    'Dışa aktarma başarısız':
        'Export failed',
    '{0} alımı kaydedildi.\nYeni alımlar mevcut miktara eklenir.':
        '{0} purchase was saved.\nNew purchases are added to the existing quantity.',
    '{0} miktarı ve ortalama maliyeti güncellendi.':
        'The quantity and average cost of {0} were updated.',
    '{0} varlık kaydı içe aktarılacak. Aynı varlık varsa mevcut miktar ve ortalama maliyet dosyadaki değerlerle değiştirilecek.\n\nDevam edilsin mi?':
        '{0} asset records will be imported. If the asset already exists, the current quantity and average cost will be replaced with the values in the file.\n\nDo you want to continue?',
    '\nAtlanan satırlar:\n':
        '\nSkipped rows:\n',
    '\nKaydedilemeyen kayıtlar:\n':
        '\nRecords that could not be saved:\n',
    '{0} seçili kayıt silinecek:\n':
        '{0} selected records will be deleted:\n',
    '{0} örnek şablonunu kaydet':
        'Save the {0} sample template',
    'Geçersiz varlık türü veya kodu.':
        'Invalid asset type or code.',
    'Miktar sıfırdan büyük olmalıdır.':
        'Quantity must be greater than zero.',
    'Alış birim fiyatı sıfırdan büyük olmalıdır.':
        'Purchase unit price must be greater than zero.',
    'Silinecek varlık kodu geçersiz.':
        'The asset code to delete is invalid.',
    'Örn. 1.250,5000':
        'e.g. 1,250.5000',
    'Örn. 10.000,0000':
        'e.g. 10,000.0000',
    'Sonuç: -':
        'Result: -',
    'Hesapla':
        'Calculate',
    'Altın (gram)':
        'Gold (grams)',
    'Gümüş (gram)':
        'Silver (grams)',
    'Çıktı':
        'Output',
    'Miktar (gr)':
        'Quantity (g)',
    'Altın / Gümüş Alım Kayıtları':
        'Gold / Silver Purchase Records',
    'FinanceTerminal_Metal_Portfoyu.xlsx':
        'FinanceTerminal_Metals_Portfolio.xlsx',
    '{0} TRY | {1}: Kur yok':
        '{0} TRY | {1}: no rate',
    'Hata: {0}':
        'Error: {0}',
    'Örn. 1.250,00':
        'e.g. 1,250.00',
    'Örn. 500,00':
        'e.g. 500.00',
    'Örn. 25.000,00':
        'e.g. 25,000.00',
    'Örn. 100.000,00':
        'e.g. 100,000.00',
    'Ek para birimi (listeden değiştirebilirsiniz)':
        'Extra currency (you can change it from the list)',
    'Çıktı Para Birimi':
        'Output Currency',
    'Döviz Alım Kayıtları':
        'Currency Purchase Records',
    'FinanceTerminal_Doviz_Portfoyu.xlsx':
        'FinanceTerminal_Currency_Portfolio.xlsx',
    'Kur bilgisi yok: {0}':
        'No rate available for: {0}',
    'Portföy Özeti':
        'Portfolio Summary',
    'Döviz ve maden güncel piyasa değeriyle gösterilir. BIST hisseleri güncel fiyat alındığında piyasa değeriyle, alınamadığında kayıtlı alış maliyetiyle gösterilir.':
        'Currencies and metals are shown at their current market value. BIST shares are shown at market value when a current price is available, otherwise at their recorded purchase cost.',
    'K/Z sütunu gerçekleşmemiş kâr/zararı TL olarak gösterir. BIST hisselerinin kâr/zararı güncel fiyatı alınabilen hisseleri kapsar; fiyatı alınamayan hisseler uyarıda belirtilir, kayıtlı alış maliyetiyle toplanır ve kâr/zarara dahil edilmez. Hisse fiyatları gecikmeli ve resmi olmayan kaynaklardan gelir. Döviz veya maden grubunda bir varlığın güncel fiyatı eksikse o grubun toplamı ve K/Z değeri eksik gösterilir; eksik fiyat varsayılarak kâr hesaplanmaz.':
        "The P/L column shows unrealised profit/loss in TRY. For BIST shares it covers the shares whose current price could be fetched; shares without a price are named in the warning, added at purchase cost and excluded from profit/loss. Share prices are delayed and come from unofficial sources. If the current price of an asset in the currency or metal group is missing, that group's total and P/L are shown as incomplete; no profit is calculated from a missing price.",
    'Toplam Döviz':
        'Total Currency',
    'Toplam Maden':
        'Total Metals',
    'Toplam Hisse Senedi (maliyet)':
        'Total Stocks (cost)',
    'GENEL TOPLAM*':
        'GRAND TOTAL*',
    'Canlı fiyat yok':
        'No live price',
    '⚠ Şu hisse senetlerinin fiyatı alınamıyor: {0}. Bu hisseler kayıtlı alış maliyetiyle toplandı; BIST kâr/zararı yalnızca fiyatı alınan hisseleri kapsar.':
        '⚠ The price of these shares cannot be fetched: {0}. They were added at their recorded purchase cost; BIST profit/loss covers only the shares that have a price.',
    '⚠ Hiçbir hisse için güncel fiyat alınamadı ({0}). Hisseler kayıtlı alış maliyetiyle gösteriliyor; kâr/zarar hesaplanamadı.':
        '⚠ No current price could be fetched for any share ({0}). Shares are shown at their recorded purchase cost; profit/loss could not be calculated.',
    '{0} (kısmi)':
        '{0} (partial)',
    'Toplam Hisse Senedi (güncel)':
        'Total Stocks (current)',
    'Toplam Hisse Senedi (kısmen güncel)':
        'Total Stocks (partly current)',
    'Kur yok':
        'No rate',
    'Özet':
        'Summary',
    'Normal':
        'Normal',
    'Ters':
        'Inverse',
    'Görüntülenecek Para Birimlerini Seç':
        'Choose Currencies to Display',
    'Güncelle':
        'Update',
    'Metaller':
        'Metals',
    'BIST AI':
        'BIST AI',
    'Profil Adını Değiştir':
        'Rename Profile',
    "Tüm Portföyü Excel'den İçe Aktar":
        'Import Whole Portfolio from Excel',
    "Tüm Portföyü Excel'e Aktar":
        'Export Whole Portfolio to Excel',
    'Ayarlar ⚙️':
        'Settings ⚙️',
    'Uygulama ayarlarını aç':
        'Open application settings',
    '＋ Profil Ekle':
        '＋ Add Profile',
    'Profil adını değiştir':
        'Rename profile',
    'Yeni profil adı:':
        'New profile name:',
    'Vazgeç':
        'Cancel',
    'Görüntülenecek Para Birimleri':
        'Currencies to Display',
    'Tümünü Seç':
        'Select All',
    'Seçimi Temizle':
        'Clear Selection',
    'Tüm portföy':
        'Whole portfolio',
    'Tüm portföyü tek Excel dosyasına aktar':
        'Export the whole portfolio to a single Excel file',
    'Tüm portföyün bulunduğu Excel dosyasını seç':
        'Select the Excel file containing the whole portfolio',
    'Tüm portföyü içe aktar':
        'Import whole portfolio',
    'FinanceTerminal güncellemesi bulundu':
        'A FinanceTerminal update was found',
    'FinanceTerminal güncellemesi indiriliyor':
        'Downloading the FinanceTerminal update',
    'Güncelleme hazır':
        'Update ready',
    'FinanceTerminal - Portföy takibi':
        'FinanceTerminal - Portfolio tracking',
    "FinanceTerminal'ı Aç":
        'Open FinanceTerminal',
    'Çıkış':
        'Exit',
    'FinanceTerminal açık kalsın mı?':
        'Keep FinanceTerminal running?',
    'Uygulamayı kapatmak yerine sistem tepsisine küçültmek ister misiniz?':
        'Would you like to minimise to the system tray instead of closing the application?',
    'Evet seçerseniz uygulama arka planda açık kalır. Fiyatlar otomatik yenilenmez; yalnızca Güncelle düğmesine bastığınızda yenilenir.':
        'If you choose Yes, the application stays open in the background. Prices are not refreshed automatically; they refresh only when you press Update.',
    'Bu tercihi hatırla ve tekrar sorma':
        'Remember this choice and do not ask again',
    'Güncelleniyor...':
        'Updating...',
    'Ayarlar':
        'Settings',
    'Windows ayarını takip et':
        'Follow the Windows setting',
    'Açık tema':
        'Light theme',
    'Koyu tema':
        'Dark theme',
    'Mavi tema':
        'Blue theme',
    'Kaydet':
        'Save',
    'Her kapatmada sor':
        'Ask every time I close',
    'Sistem tepsisine küçült':
        'Minimise to the system tray',
    'Uygulamayı tamamen kapat':
        'Close the application completely',
    'Başlangıçta güncellemeleri kontrol et (yeni sürüm bulunursa önce sor)':
        'Check for updates at startup (ask first if a new version is found)',
    'Güncellemeleri Kontrol Et':
        'Check for Updates',
    'Bilgisayar açıldığında FinanceTerminal otomatik başlasın':
        'Start FinanceTerminal automatically when the computer starts',
    'Otomatik başlarken pencere açılmasın, sistem tepsisinde başlasın':
        'When starting automatically, do not open the window; start in the system tray',
    'Yardım / Kullanım Kılavuzu':
        'Help / User Guide',
    'FinanceTerminal - Kullanım Kılavuzu':
        'FinanceTerminal - User Guide',
    'Kapat':
        'Close',
    'Profil:':
        'Profile:',
    'Maksimum profil sayısı':
        'Maximum number of profiles',
    'Maksimum profil limitine ulaşılmıştır. Ekstra profil için GitHub üzerinden Issue açınız.':
        'The maximum number of profiles has been reached. To request an extra profile, open an Issue on GitHub.',
    'Geçersiz ad':
        'Invalid name',
    'Profil adı boş bırakılamaz.':
        'The profile name cannot be empty.',
    'Profil adı kullanılıyor':
        'Profile name already in use',
    'Profillerin adı aynı olamaz.':
        'Profiles cannot have the same name.',
    'Döviz sekmesinde görmek istediğiniz para birimlerini seçin. Kur sağlayıcısında bulunmayan birimlerde güncel fiyat gösterilemez.':
        'Choose the currencies you want to see on the Currency tab. A current price cannot be shown for currencies the rate provider does not supply.',
    'Seçim gerekli':
        'Selection required',
    'En az bir para birimi seçmelisiniz.':
        'You must select at least one currency.',
    'Dosyada içe aktarılabilecek portföy kaydı bulunamadı.':
        'No importable portfolio records were found in the file.',
    'Döviz: {0} kayıt\nMaden: {1} kayıt\nHisse senedi: {2} kayıt\n\nAynı varlık veya hisse kodu mevcutsa miktar ve ortalama maliyet Excel dosyasındaki değerlerle güncellenecek; kayıtlar ikinci kez eklenmeyecek. Dosyada bulunmayan bölümlerdeki mevcut kayıtlar korunacak.\n\nDevam edilsin mi?':
        'Currency: {0} records\nMetals: {1} records\nStocks: {2} records\n\nIf the same asset or stock symbol exists, its quantity and average cost will be updated with the values in the Excel file; records will not be added a second time. Existing records in sections missing from the file will be kept.\n\nDo you want to continue?',
    'Toplu içe aktarma tamamlandı.\n\nDöviz: {0} kayıt\nMaden: {1} kayıt\nHisse senedi: {2} kayıt\nToplam: {3} kayıt':
        'Bulk import completed.\n\nCurrency: {0} records\nMetals: {1} records\nStocks: {2} records\nTotal: {3} records',
    '\n\nAtlanan Excel satırları:\n':
        '\n\nSkipped Excel rows:\n',
    '\n\nKaydedilemeyen kayıtlar:\n':
        '\n\nRecords that could not be saved:\n',
    'Windows başlangıç ayarı':
        'Windows startup setting',
    'Windows başlangıç ayarı değiştirilemedi. Kayıt defterine yazma izni olmayabilir; ayarı daha sonra tekrar deneyebilirsiniz.':
        'The Windows startup setting could not be changed. You may not have permission to write to the registry; you can try again later.',
    'Windows ile başlat':
        'Start with Windows',
    'Bilgisayar açıldığında FinanceTerminal otomatik başlasın mı?':
        'Should FinanceTerminal start automatically when the computer starts?',
    "Evet derseniz Windows'a giriş yaptığınızda uygulama kendiliğinden açılır ve güncel fiyatları alır. Bu seçimi istediğiniz zaman Ayarlar'dan değiştirebilirsiniz.":
        'If you choose Yes, the application opens by itself when you sign in to Windows and fetches current prices. You can change this choice at any time in Settings.',
    'Otomatik güncelleme kontrolü':
        'Automatic update check',
    'FinanceTerminal açılışta güncellemeleri otomatik kontrol etsin mi?':
        'Should FinanceTerminal check for updates automatically at startup?',
    'Yeni sürüm bulunursa indirme ve kurulumdan önce onayınız istenir. Kontrol için internet bağlantısı gerekir.':
        'If a new version is found, you will be asked before it is downloaded and installed. An internet connection is required for the check.',
    'Güncelleme kontrolü sonuç vermedi.':
        'The update check returned no result.',
    'Yeni sürüm bulundu':
        'New version found',
    'İndirme sonucu alınamadı.':
        'The download result could not be obtained.',
    'Güncelleme indirilemedi':
        'The update could not be downloaded',
    'Sistem tepsisi kullanılamıyor':
        'System tray unavailable',
    'Bu Windows oturumunda sistem tepsisi kullanılamıyor. Uygulama kapatılacak.':
        'The system tray is not available in this Windows session. The application will be closed.',
    'FinanceTerminal çalışıyor':
        'FinanceTerminal is running',
    "FinanceTerminal sistem tepsisinde açık. Fiyatlar otomatik yenilenmez; güncelleme için uygulamayı açıp Güncelle'ye basın.":
        'FinanceTerminal is open in the system tray. Prices are not refreshed automatically; open the application and press Update to refresh.',
    'Güncelleme tamamlanınca uygulama kapanacak...':
        'The application will close when the update finishes...',
    "Bu seçenek yalnızca Windows'ta kurulu (EXE) sürümde kullanılabilir.":
        'This option is only available in the installed (EXE) version on Windows.',
    'Başlangıç Sekmesi':
        'Start Tab',
    'Hassasiyet':
        'Precision',
    'Tema':
        'Theme',
    'Pencereyi X ile kapatınca':
        'When the window is closed with X',
    'Yeni sürüm bulunduğunda indirme ve kurulum için ayrıca onayınız istenir. Kişisel portföy verileri %APPDATA%\\FinanceTerminal altında saklanır.':
        'When a new version is found, your approval is requested separately for download and installation. Your personal portfolio data is stored under %APPDATA%\\FinanceTerminal.',
    'Veriler bu bilgisayarda saklanır · {0}':
        'Data is stored on this computer · {0}',
    'Eski portföy verileri kopyalanamadı':
        'Old portfolio data could not be copied',
    "Önceki sürümün veri klasörü değiştirilmedi. FinanceTerminal eski verilerinizi otomatik olarak Profile 1'e kopyalayamadı. Uygulamayı kapatın ve yedek klasörünüzü koruyun.":
        "The previous version's data folder was not modified. FinanceTerminal could not automatically copy your old data to Profile 1. Close the application and keep your backup folder.",
    'Profil oluşturulamadı':
        'The profile could not be created',
    'Profil değiştirilemedi':
        'The profile could not be switched',
    'Profil adı kaydedilemedi':
        'The profile name could not be saved',
    'Tüm portföy örnek şablonunu kaydet':
        'Save the whole-portfolio sample template',
    'Güncelleme':
        'Update',
    'Güncelleme kontrolü zaten devam ediyor.':
        'An update check is already in progress.',
    'Güncelleme dosyası şu anda indiriliyor.':
        'The update file is being downloaded right now.',
    'Güncelleme kontrolü':
        'Update check',
    'FinanceTerminal {0} sürümü bulundu.\n\nGüncelleme şimdi indirilsin ve uygulama yeniden başlatılarak kurulsun mu?\n\nPortföy kayıtlarınız ve ayarlarınız korunur. Güncelleme yalnızca uygulama EXE dosyasını değiştirir.':
        'FinanceTerminal {0} was found.\n\nShould the update be downloaded now and installed by restarting the application?\n\nYour portfolio records and settings are preserved. The update only replaces the application EXE file.',
    'Güncelleme yapılamıyor':
        'The update cannot be performed',
    'FinanceTerminal {0} indiriliyor...\n0.0 MB / {1:.1f} MB  ·  %0.0\nOrtalama indirme hızı hesaplanıyor...':
        'Downloading FinanceTerminal {0}...\n0.0 MB / {1:.1f} MB  ·  0.0%\nCalculating average download speed...',
    'FinanceTerminal {0} indiriliyor...\n{1:.2f} MB / {2:.2f} MB  ·  %{3:.1f}\nOrtalama indirme hızı: {4:.2f} MB/sn':
        'Downloading FinanceTerminal {0}...\n{1:.2f} MB / {2:.2f} MB  ·  {3:.1f}%\nAverage download speed: {4:.2f} MB/s',
    'Güncelleme başlatılamadı':
        'The update could not be started',
    "FinanceTerminal {0} indirildi ve doğrulandı. Uygulama şimdi kapanacak. Güncelleyici eski EXE'yi yedekleyip yenisini kuracak; yeni sürüm açılmazsa eski sürüm otomatik geri yüklenecek.":
        'FinanceTerminal {0} was downloaded and verified. The application will now close. The updater will back up the old EXE and install the new one; if the new version does not start, the old version is restored automatically.',
    'İşlem devam ediyor':
        'Operation in progress',
    'Güncelleme işlemi tamamlandıktan sonra uygulamayı kapatabilirsiniz.':
        'You can close the application after the update process is complete.',
    'Sürüm: {0}':
        'Version: {0}',
    'Tüm portföy tek Excel dosyasına aktarıldı:\n{0}\n\nSummary, Döviz, Maden, Hisse Senedi ve Veri Bilgisi sayfaları oluşturuldu.':
        'The whole portfolio was exported to a single Excel file:\n{0}\n\nThe Summary, Currency, Metals, Stocks and Data Info sheets were created.',
    'FinanceTerminal {0} yayımlandı.\n\nKaynak kod modunda çalıştığınız için uygulama dosyası otomatik değiştirilemez. Windows EXE dosyasını buradan indirebilirsiniz:\n{1}':
        'FinanceTerminal {0} has been released.\n\nBecause you are running from source code, the application file cannot be replaced automatically. You can download the Windows EXE here:\n{1}',
    'Şu an güncelsiniz, {0} sürümünü kullanıyorsunuz.':
        'You are up to date; you are using version {0}.',
}


EN.update({
    "Kâr / Zarar": "Profit / Loss",
    "bilinmiyor": "unknown",
    "Evet": "Yes",
    "Hayır": "No",
    "Tamam": "OK",
    "Not:": "Note:",
    "Maden": "Metals",
    "Profil 1": "Profile 1",
    "Profil 2": "Profile 2",
    "Profil 3": "Profile 3",
    "Gece yarısı teması (tam siyah)": "Midnight theme (true black)",
    "Zümrüt teması (yeşil)": "Emerald theme (green)",
    "Dil": "Language",
    "Dil değiştirildi": "Language changed",
    "Dil değişikliği uygulama yeniden başlatılınca geçerli olur. Şimdi yeniden başlatılsın mı?":
        "The language change takes effect when the application restarts. Restart now?",
    "Şimdi Yeniden Başlat": "Restart Now",
    "Daha Sonra": "Later",
    "Uygulama yeniden başlatılamadı. Lütfen FinanceTerminal'ı kapatıp elle yeniden açın.":
        "The application could not be restarted. Please close FinanceTerminal and open it again manually.",
    "Ana uygulamaya uyandırma sinyali gönderilemedi: {0}":
        "The wake-up signal could not be sent to the running application: {0}",
    "Tek uygulama kilidi alınamadı: {0}":
        "The single-instance lock could not be acquired: {0}",
    "Fiyat alınacak hisse yok. Önce bir hisse ekleyin.": "There are no shares to fetch prices for. Add a share first.",
    "Fiyatlar henüz alınmadı.": "Prices have not been fetched yet.",
    "Güncelleniyor…": "Updating…",
    "Fiyatlar alınıyor…": "Fetching prices…",
    "Önceki fiyat: {0}": "Previous price: {0}",
    "Fiyatlar aynı kaldı: piyasa kapalıysa veya son işlem fiyatı değişmediyse bu normaldir.":
        "Prices are unchanged: this is normal if the market is closed or the last traded price has not moved.",
    "Son güncelleme: {0}": "Last update: {0}",
    "İnternet bağlantınızı kontrol edin; son bilinen fiyatlar gösteriliyor.":
        "Check your internet connection; the last known prices are shown.",
    "{0} fiyat değişti, {1} aynı kaldı": "{0} changed, {1} unchanged",
    "Son işlem zamanı: {0}": "Latest trade time: {0}",
    "Fiyat alınamadı. İnternet bağlantınızı kontrol edin.": "No price could be fetched. Check your internet connection.",
    "{0} saniye içinde otomatik olarak devam edilecek.": "Continuing automatically in {0} seconds.",
    "Bu dosya bir FinanceTerminal yedeği değil.": "This file is not a FinanceTerminal backup.",
    "Yedek dosyası bozuk.": "The backup file is damaged.",
    "Bu yedek FinanceTerminal'in daha yeni bir sürümüyle oluşturulmuş. Uygulamayı güncelleyip tekrar deneyin.":
        "This backup was created by a newer version of FinanceTerminal. Update the application and try again.",
    "Yedek dosyasındaki veri beklenen biçimde değil.": "The data in the backup file is not in the expected format.",
    "Şifre en az {0} karakter olmalıdır.": "The password must be at least {0} characters long.",
    "Şifreleme bileşeni bulunamadı; şifreli yedek bu kurulumda kullanılamıyor.":
        "The encryption component was not found; encrypted backups are not available in this installation.",
    "Yedek dosyası bozuk (sağlama toplamı uyuşmuyor).": "The backup file is damaged (checksum mismatch).",
    "Bu yedek şifreli; şifreyi girin.": "This backup is encrypted; enter the password.",
    "satır okunamadı": "row could not be read",
    "geçersiz miktar": "invalid quantity",
    "geçersiz ortalama maliyet": "invalid average cost",
    "Şifre yanlış ya da dosya bozulmuş.": "The password is wrong or the file is damaged.",
    "{0} / {1}: bir satır atlandı — {2}": "{0} / {1}: a row was skipped — {2}",
    "çok fazla kayıt (en çok {0})": "too many records (at most {0})",
    "aynı kod birden fazla kez geçiyor: {0}": "the same code appears more than once: {0}",
    "desteklenmeyen kod: {0}": "unsupported code: {0}",
    "Mevcut verilerin güvenlik yedeği alınamadı: {0}": "A safety backup of the current data could not be created: {0}",
    "Yedek geri yüklenirken bir hata oluştu: {0}\n\nGeri yüklemeden önceki verileriniz şu dosyada saklandı: {1}":
        "An error occurred while restoring the backup: {0}\n\nYour data from before the restore was saved in this file: {1}",
    "FinanceTerminal yedeği (*.ftbackup)": "FinanceTerminal backup (*.ftbackup)",
    "Yedek şifresi": "Backup password",
    "Yedek Al": "Create Backup",
    "Yedek dosyası şifrelensin mi?": "Should the backup file be encrypted?",
    "Şifreli Yedek": "Encrypted Backup",
    "Şifresiz Yedek": "Unencrypted Backup",
    "Yedeği kaydet": "Save the backup",
    "Yedek alındı": "Backup created",
    "Yedekten Geri Yükle": "Restore from Backup",
    "Birleştir": "Merge",
    "Üzerine Yaz": "Overwrite",
    "Yedek dosyasını seçin": "Select the backup file",
    "Geri yükleme tamamlandı": "Restore completed",
    "Şifreyi tekrar girin:": "Enter the password again:",
    "Şifresiz yedek, finansal verilerinizi dosyayı açan herkesin okuyabileceği biçimde içerir; güvenli bir yerde saklayın.":
        "An unencrypted backup contains your financial data in a form anyone who opens the file can read; keep it somewhere safe.",
    "Yedek": "Backup",
    "Yedek kaydedildi:\n{0}\n\nProfil: {1}, döviz: {2}, maden: {3}, hisse: {4} kayıt.":
        "Backup saved:\n{0}\n\nProfiles: {1}, currency: {2}, metals: {3}, stocks: {4} records.",
    "Dosya şifrelidir. Şifreyi unutursanız verileriniz kurtarılamaz.":
        "The file is encrypted. If you forget the password your data cannot be recovered.",
    "Dosya şifresizdir ve finansal verilerinizi içerir; güvenli bir yerde saklayın.":
        "The file is not encrypted and contains your financial data; keep it somewhere safe.",
    "Yedekte {0} profil, {1} döviz, {2} maden ve {3} hisse kaydı var.\nOluşturulma: {4} (FinanceTerminal {5})":
        "The backup contains {0} profiles, {1} currency, {2} metals and {3} stock records.\nCreated: {4} (FinanceTerminal {5})",
    "Her iki durumda mevcut verileriniz önce otomatik olarak yedeklenir.":
        "In both cases your current data is backed up automatically first.",
    "Üzerine yazılsın mı?": "Overwrite?",
    "Dosyadaki profillerin mevcut kayıtları silinecek ve yedektekilerle değiştirilecek. Devam edilsin mi?":
        "The current records of the profiles in the file will be deleted and replaced with those in the backup. Do you want to continue?",
    "Yedekte geri yüklenecek kayıt bulunamadı.": "No records to restore were found in the backup.",
    "{0} kayıt geri yüklendi.": "{0} records were restored.",
    "Şifreler aynı değil.": "The passwords do not match.",
    "Şifreli yedekte şifreyi unutursanız verileriniz kurtarılamaz; şifre hiçbir yerde saklanmaz.":
        "If you forget the password of an encrypted backup your data cannot be recovered; the password is not stored anywhere.",
    "Yedek alınamadı": "The backup could not be created",
    "Yedek okunamadı": "The backup could not be read",
    "Geri yükleme başarısız": "Restore failed",
    "Atlanan satırlar:\n": "Skipped rows:\n",
    "Yedek şifresi (en az {0} karakter):": "Backup password (at least {0} characters):",
    "{0} satır okunamadığı için atlanacak.": "{0} rows will be skipped because they could not be read.",
    "Üzerine Yaz: dosyadaki profillerin kayıtları silinip dosyadakilerle değiştirilir; ortak tercihler de dosyadan alınır.":
        "Overwrite: the records of the profiles in the file are deleted and replaced with those in the file; shared preferences are also taken from the file.",
    "Önceki verileriniz şu dosyada saklandı:\n{0}": "Your previous data was saved in this file:\n{0}",
    "Birleştir: dosyadaki kayıtlar eklenir ya da güncellenir; sizde olup dosyada olmayan kayıtlar korunur.":
        "Merge: records in the file are added or updated; records you have that are not in the file are kept.",
    "... ve {0} satır daha.": "... and {0} more rows.",
    "Veri ve Yedekleme": "Data and Backup",
    "Yedek dosyası (.ftbackup) tüm profillerinizi ve ortak tercihlerinizi içerir; tema ve dil gibi kişisel ayarlar yedeğe dahil değildir.":
        "The backup file (.ftbackup) contains all your profiles and shared preferences; personal settings such as theme and language are not included.",
    "Yedek Al…": "Create Backup…",
    "Yedekten Geri Yükle…": "Restore from Backup…",
    "Değişikliklerin görünmesi için uygulamanın yeniden başlatılması gerekir. Şimdi yeniden başlatılsın mı?":
        "The application has to restart for the changes to appear. Restart now?",
})
