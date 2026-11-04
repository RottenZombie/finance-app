# FinanceTerminal 2.2.8-dev

## Güncelleme sistemi
- GitHub Releases üzerinden en son kararlı sürüm kontrolü.
- İlk açılışta otomatik güncelleme kontrolü tercihi sorulur ve istenirse hatırlanır.
- Ayarlar bölümüne manuel güncelleme kontrolü eklendi.
- Yeni Windows EXE indirilirken dosya boyutu, MZ imzası ve GitHub SHA-256 özeti (sunuluyorsa) doğrulanır.
- Çalışan EXE doğrudan üzerine yazılmaz; geçici PowerShell güncelleyicisi uygulama kapandıktan sonra dosyayı değiştirip yeniden başlatır.
- Kaynak kod modunda uygulama kendisini değiştirmez; yeni sürüm bağlantısını bildirir.

## Teknik notlar
- Güncelleme kaynağı: https://github.com/RottenZombie/finance-app/releases/latest
- Beklenen varlık: FinanceTerminal.exe
- Otomatik güncelleme yalnızca yayımlanmış Windows EXE paketinde çalışır.
