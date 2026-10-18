# ReaDroid'a katkı

Katkıda bulunduğunuz için teşekkürler. Küçük değişikliklerde, pull request göndermeden önce sorunu
anlatan bir issue açın.

## Genel kurallar

- Mümkün olduğunca çekirdeği harici Python bağımlılıklarından arındırın.
- Telemetri veya APK'ların otomatik yüklenmesini eklemeyin.
- APK'ları güvenilmeyen girdi olarak ele alın, içeriklerini çalıştırmaktan kaçının.
- Bir APK'nın içinden gelen herhangi bir metni (adlar, dizeler, araç çıktısı) ekrana yazmadan
  önce `app.sanitize()` kullanın — bu, ANSI kaçış dizilerini ve kontrol karakterlerini temizler.
- Kod yorumları ve docstring'ler için Portekizce tercih edilir (upstream konvansiyonu; orijinalle
  farkın küçük kalmasını sağlar). Kullanıcıya görünen metinler ise `t()` üzerinden verilir.
- Değişiklik göndermeden önce `python -m unittest discover -s tests -v` çalıştırın.
- Sorun bildirirken cihaz, Android sürümü, mimari, Termux sürümü ve harici araçlarını belirtin.

## Metin değiştirmek (çeviri işi)

Yeni bir arayüz metni eklerken:

1. `readroid/i18n.py` içindeki `t("anahtar.alan")` ile çağırın. Anahtarı **anlamsal** seçin
   (`menu.inspect`, `analyzer.note.scan`); metnin kendisini anahtar yapmayın — upstream metni
   değiştirdiğinde anahtarınız yerinde kalsın.
2. Anahtarı hem `locales/tr.json` hem `locales/pt.json` içine ekleyin.
3. `{placeholder}` kullanıyorsanız iki katalogda de aynı isimle yazın; `tests/test_i18n.py` bunu
   zaten doğruluyor.
4. `python tools/extract_strings.py --stats` çalıştırıp `t()` sarmalamayı unuttuğunuz metin
   kalmadığını görün.
5. `READROID_LANG=pt python -m unittest discover -s tests` ile iki dilde de yeşil olduğunu doğrulayın.

Menüde evet/hayır sorusu soruyorsanız `[e/H]` yazın ve yanıtı `i18n.is_yes()` ile okuyun — bu,
Türkçe (`e`) ve Portekizce (`s`) tuş takımlarının ikisini de kabul eder.