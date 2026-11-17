# FinanceTerminal 2.3.0-dev

- Added independent Profile 1 and Profile 2 data stores. Profile labels are editable and the last selected profile is remembered.
- Copied existing 2.2.x `%APPDATA%\FinanceTerminal\data` contents into Profile 1 on first launch without deleting the original folder.
- Added a selectable Currency tab card list with an expanded currency catalog, including CHF and CZK. Rates are calculated from the provider's latest USD-base response and converted to TRY.
- Expanded Currency portfolio holdings to accept all currencies in the supported catalog.
- Added double-click editing for existing Currency and Metals holdings. Editing replaces quantity and average cost; it does not create another purchase.
- Improved Portfolio and Metals calculator input and output formatting with Turkish thousands and decimal separators.
- Changed Metals EUR conversion to use the live EUR/TRY quote instead of the previous fixed 0.92 approximation.
- Clarified Summary calculation basis: Currency and Metals use current values; BIST is shown at acquisition cost and is excluded from unrealized K/Z until live quotes are supported.
- Added unit tests for expanded currency rates, profile paths/migration, replace-style holding edits, and multi-asset Summary calculations.

## Kullanıcı testinden gelen iyileştirmeler
- Currency kartlarında para biriminin Türkçe adı küçük açıklama olarak gösterilir; kod ve kur başlığı daha belirgin hâle getirildi.
- Para birimi seçme penceresine Tümünü Seç ve Seçimi Temizle kontrolleri eklendi.
- Birleşik Excel dışa aktarımında dosya adı profil adına göre oluşturulur; Summary ve Veri Bilgisi sayfalarında dosyanın ait olduğu profil yazılır.
- BIST satırları çift tıklanınca ayrı düzenleme penceresi açılır. Hisse kodu, şirket, adet, ortalama maliyet, sektör ve not alanlarının tamamı düzenlenebilir. Mevcut başka bir hisse koduyla çakışan değişiklikler engellenir.

- Profil sistemi üç profille sınırlandırıldı: Profil 1 ve Profil 2 varsayılan olarak bulunur; Profil 3 yalnızca Profil Ekle seçeneğiyle oluşturulur. Üçüncü profil sonrası ekleme denemesinde maksimum profil mesajı gösterilir.
- Profil seçicisi isim uzunluğuna göre otomatik genişler; en fazla 20 karakter gösterir ve uzun adları üç nokta ile kısaltır. Profilin tam adı ayarlarda ve Excel sayfalarında korunur.
- Profil 3 için ayrı veri deposu ve profile özgü Excel dosya adı desteği eklendi.

## Güncelleme sistemi iyileştirmeleri
- İndirme penceresi indirilen/toplam MB, yüzde ve ortalama MB/sn hızını gerçek zamanlı gösterir.
- İndirme worker'ı parça parça ilerleme sinyali gönderir; indirme boyutu ve varsa GitHub SHA-256 özeti doğrulanır.
- Güncelleme yardımcısı PyInstaller `--onefile` yapısındaki Python sürecini ve bootloader ana sürecini birlikte bekler.
- Yeni EXE hedef klasörde geçici dosyaya kopyalanıp boyut ve Windows EXE imzası bakımından kontrol edildikten sonra yerleştirilir.
- Önceki EXE yedeklenir; yeni sürüm başlatılamazsa eski EXE geri yüklenmeye çalışılır.
- Güncelleme yardımcısı günlükleri `%APPDATA%\FinanceTerminal\logs\updater.log` dosyasına yazar.
