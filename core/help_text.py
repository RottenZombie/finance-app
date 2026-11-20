"""Built-in user guide (HTML) in Turkish and English."""
from __future__ import annotations

from core.i18n import get_language

HELP_TR = r"""
<h2>FinanceTerminal Kullanım Kılavuzu</h2>
<p>FinanceTerminal; döviz, yatırım amaçlı döviz birikimi, değerli maden ve
BIST portföy kayıtlarını tek uygulamada takip etmenizi sağlar.</p>

<h3>Özet</h3>
<p>Döviz, maden ve hisse senedi portföylerinizin toplam değerini TRY, EUR
ve USD cinsinden özetler. Fiyatlar yenilendiğinde ve portföy kayıtları
değiştiğinde özet otomatik güncellenir. Bir hissenin fiyatı alınamazsa o hisse
uyarıda adıyla belirtilir; kalan hisselerin kâr/zararı gösterilmeye devam eder.</p>

<h3>Döviz</h3>
<p>Seçtiğiniz para birimlerinin TL karşılığını kartlar halinde gösterir.
<b>Görüntülenecek Para Birimlerini Seç</b> düğmesiyle kartları kişiselleştirebilirsiniz.
<b>Normal</b> görünümde dövizin TL karşılığını, <b>Ters</b> görünümde TL'nin döviz
karşılığını gösterir. Para birimi listeleri her yerde aynı sıradadır: dünya döviz
işlem hacmine göre (USD, EUR, JPY, GBP, CNY, CHF, …).</p>

<h3>Portföy</h3>
<p>Üstteki hesaplayıcıda <b>USD, EUR ve TRY</b> alanları sabittir; bunların altındaki
<b>ek para birimi</b> listesinden istediğiniz herhangi bir para birimini seçip tutarını girebilirsiniz
(seçiminiz hatırlanır). Çıktı para birimi de aynı listeden seçilir. Bir tutarın kuru yoksa sonuç
sessizce sıfır saymak yerine hangi kurun eksik olduğunu bildirir.</p>
<p>Hesaplama TL üzerinden yapılır: her tutar önce güncel TL kuruyla TL'ye çevrilir, toplam
seçtiğiniz çıktı biriminin TL kuruna bölünür. Kurlar tek bir USD tablosundan türetildiği için bu,
doğrudan çapraz kurla aynı sonucu verir.</p>
<p>Alt bölümde döviz alımlarınızı miktar ve alış birim fiyatıyla kaydedin. Aynı dövizden tekrar alım
yaptığınızda miktar birleştirilir ve ağırlıklı ortalama maliyet hesaplanır. Kayıt üzerinde çift
tıklayarak miktarı ve ortalama maliyeti düzenleyebilirsiniz.</p>

<h3>Metaller</h3>
<p>Altın ve gümüş alımlarınızı gram miktarı ve alış fiyatıyla kaydedin. Hesaplayıcının çıktısı
desteklenen tüm para birimlerinde (TRY dahil) gösterilebilir. Güncel değerler spot fiyatlara
dayanır; işçilik ve alış-satış farklarını içermez.</p>

<h3>BIST AI</h3>
<p>Hisse kodu, şirket adı, adet ve ortalama alış maliyetinizi kaydedin. Uygulama açıldığında ve
<b>Fiyatları Güncelle</b> düğmesiyle güncel (gecikmeli) hisse fiyatları alınır; piyasa değeri ve
kâr/zarar hesaplanır. Fiyatlar resmi olmayan ücretsiz kaynaklardan gelir ve yatırım tavsiyesi
değildir. İnternet yoksa son alınan fiyat (en çok 7 gün eski) "eski" işaretiyle gösterilir.
Yapay zekâ analizi henüz bulunmamaktadır.</p>

<h3>Excel'e aktarma ve şablon</h3>
<p>Her <b>Excel'e Aktar</b> düğmesi önce ne yapmak istediğinizi sorar: <b>Verilerimi Aktar</b>
kayıtlarınızı, dışa aktarma anındaki fiyat ve kâr/zarar değerleriyle birlikte kaydeder;
<b>Örnek Şablon İndir</b> aynı düzende, her sayfada tek örnek satırı olan bir dosya verir. Örneği kendi
verinizle değiştirip ilgili içe aktarma düğmesiyle yükleyebilirsiniz. Excel dosyaları seçili uygulama
dilinde yazılır; içe aktarma her iki dildeki başlıkları da tanır. Üstteki <b>Tüm Portföyü Excel'e
Aktar</b> düğmesi tüm bölümleri tek dosyada toplar.</p>

<h3>Kayıt silme</h3>
<p>Tablolarda birden fazla satır seçmek için Ctrl veya Shift tuşunu kullanabilirsiniz.
<b>Seçili Kayıtları Sil</b> yalnızca seçtiklerinizi kaldırır. <b>Tüm Kayıtları Sil</b> ilgili
bölümün bütün kayıtlarını temizler ve ayrıca onay ister. Silme işlemi geri alınamaz; gerekirse
önce Excel dışa aktarımıyla yedek alın.</p>

<h3>Profiller</h3>
<p>Üst bölümdeki Profil menüsünden en fazla üç profil kullanabilirsiniz. Her profilin döviz, maden
ve BIST kayıtları ayrıdır. Profil adları uzun olabilir; menüde 20 karakterden sonrası kısaltılır,
Excel dışa aktarımında tam profil adı korunur. Üçüncü profilden sonra yeni profil eklemek için
GitHub üzerinden Issue açmanız gerekir.</p>

<h3>Ayarlar</h3>
<p><b>Dil:</b> Türkçe veya English seçebilirsiniz; değişiklik uygulama yeniden başlatılınca geçerli olur
(Ayarlar size hemen yeniden başlatmayı önerir). <b>Tema:</b> Windows ayarını takip eden otomatik seçeneğin
yanında Açık, Koyu, Mavi, Gece Yarısı (tam siyah) ve Zümrüt (yeşil) temaları vardır. Ayrıca başlangıç
sekmesini, sayı hassasiyetini, pencereyi kapatma davranışını ve güncelleme kontrolünü ayarlayabilirsiniz.</p>
<p><b>Bilgisayar açıldığında başlat:</b> Kurulu (EXE) sürümde, Windows'a giriş yaptığınızda uygulama
kendiliğinden açılabilir; isterseniz pencere açmadan sistem tepsisinde başlar. Bu seçim Windows
Görev Yöneticisi'ndeki "Başlangıç uygulamaları" listesinde de görünür.</p>

<h3>Güncellemeler</h3>
<p>Güncellemeleri Kontrol Et düğmesi GitHub üzerindeki en son kararlı sürümü denetler. Otomatik
kontrol açık ise uygulama açılışta kontrol yapar. Yeni sürüm bulunduğunda indirme ve kurulum için
mutlaka onayınız istenir; dosyanın SHA-256 özeti doğrulanamazsa otomatik kurulum yapılmaz.
Güncelleme yalnızca EXE dosyasını değiştirir; %APPDATA%\FinanceTerminal altında saklanan portföy
verileriniz ve ayarlarınız korunur.</p>

<h3>Uygulama verileri</h3>
<p>Ayarlar, portföy verileri, son başarılı fiyatların önbelleği ve hata günlüğü
%APPDATA%\FinanceTerminal klasöründe saklanır. FinanceTerminal zaten açıksa EXE'yi yeniden
başlatmak yeni pencere oluşturmaz; açık pencereyi öne getirir.</p>

<p><i>Not: Uygulamadaki fiyatlar bilgilendirme ve portföy takibi içindir. Gerçek işlem öncesinde
bankanızın, aracı kurumunuzun veya kuyumcunuzun alış-satış fiyatlarını kontrol edin.</i></p>
"""

HELP_EN = r"""
<h2>FinanceTerminal User Guide</h2>
<p>FinanceTerminal lets you track currencies, foreign-currency savings, precious metals
and your BIST share portfolio in a single application.</p>

<h3>Summary</h3>
<p>Summarises the total value of your currency, metals and stock portfolios in TRY, EUR and USD.
The summary updates automatically when prices refresh and when portfolio records change. If the
price of a share cannot be fetched, the warning names that share and the profit/loss of the other
shares is still shown.</p>

<h3>Currency</h3>
<p>Shows the TRY value of the currencies you choose as cards. Use <b>Choose Currencies to Display</b>
to personalise the cards. <b>Normal</b> view shows the TRY value of a currency, <b>Inverse</b> view
shows how much of the currency one TRY buys. Currency lists are in the same order everywhere, by
share of global foreign-exchange turnover (USD, EUR, JPY, GBP, CNY, CHF, …).</p>

<h3>Portfolio</h3>
<p>In the calculator at the top, the <b>USD, EUR and TRY</b> fields are fixed; below them the
<b>extra currency</b> list lets you pick any other currency and enter an amount (your choice is
remembered). The output currency is chosen from the same list. If an amount has no exchange rate,
the result says which rate is missing instead of silently counting it as zero.</p>
<p>The calculation goes through TRY: each amount is converted to TRY at the current TRY rate, and
the total is divided by the TRY rate of the output currency. Because all rates are derived from one
USD table, this gives the same result as a direct cross rate.</p>
<p>In the lower section, record your currency purchases with quantity and purchase unit price.
Buying the same currency again merges the quantity and recalculates the weighted average cost.
Double-click a record to edit its quantity and average cost.</p>

<h3>Metals</h3>
<p>Record gold and silver purchases with gram quantity and purchase price. The calculator output can
be shown in any supported currency (including TRY). Current values are based on spot prices and do
not include workmanship or buy/sell spreads.</p>

<h3>BIST AI</h3>
<p>Record the stock symbol, company name, quantity and average purchase cost. When the application
starts, and with the <b>Update Prices</b> button, current (delayed) share prices are fetched; market
value and profit/loss are calculated. Prices come from unofficial free sources and are not
investment advice. Without an internet connection the last fetched price (at most 7 days old) is
shown marked "old". AI analysis is not available yet.</p>

<h3>Excel export and template</h3>
<p>Every <b>Export to Excel</b> button first asks what you want to do: <b>Export My Data</b> saves
your records together with the prices and profit/loss at the time of export; <b>Download Sample
Template</b> gives you a file in the same layout with one example row per sheet. Replace the example
with your own data and load it with the matching import button. Excel files are written in the
selected application language; import recognises headers in both languages. The <b>Export Whole
Portfolio to Excel</b> button at the top combines all sections into one file.</p>

<h3>Deleting records</h3>
<p>Use Ctrl or Shift to select several rows in the tables. <b>Delete Selected</b> removes only what
you selected. <b>Delete All</b> clears every record of that section and asks for confirmation
first. Deleting cannot be undone; take an Excel export first if you need a backup.</p>

<h3>Profiles</h3>
<p>You can use up to three profiles from the Profile menu at the top. Each profile has its own
currency, metals and BIST records. Profile names can be long; the menu shortens them after 20
characters, and the full name is kept in Excel exports. To add more than three profiles, open an
Issue on GitHub.</p>

<h3>Settings</h3>
<p><b>Language:</b> choose Türkçe or English; the change takes effect when the application restarts
(Settings offers to restart right away). <b>Theme:</b> besides the automatic option that follows the
Windows setting there are Light, Dark, Blue, Midnight (true black) and Emerald (green) themes. You can
also set the start tab, number precision, what closing the window does and update checking.</p>
<p><b>Start with Windows:</b> in the installed (EXE) version the application can open automatically
when you sign in to Windows; optionally it starts hidden in the system tray. The choice also appears
in Windows Task Manager under "Startup apps".</p>

<h3>Updates</h3>
<p>The Check for Updates button checks the latest stable release on GitHub. If automatic checking is
on, the application checks at startup. When a new version is found you are always asked before it is
downloaded and installed; if the file's SHA-256 digest cannot be verified, automatic installation is
not performed. An update only replaces the EXE file; your portfolio data and settings stored under
%APPDATA%\FinanceTerminal are preserved.</p>

<h3>Application data</h3>
<p>Settings, portfolio data, the cache of the last successful prices and the error log are stored in
the %APPDATA%\FinanceTerminal folder. If FinanceTerminal is already running, starting the EXE again
does not create a new window; it brings the open window to the front.</p>

<p><i>Note: Prices in the application are for information and portfolio tracking. Before a real
transaction, check the buy/sell prices of your bank, broker or jeweller.</i></p>
"""


def help_html(language: str | None = None) -> str:
    return HELP_EN if (language or get_language()) == "en" else HELP_TR
