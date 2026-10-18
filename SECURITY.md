# Güvenlik politikası

ReaDroid'da bir hata bildirmek için özel APK'lar, anahtarlar, token'lar veya kişisel veri
eklemeden bir issue açın. Etkisini açıklayın ve hassas olmayan en küçük örneği verin.

ReaDroid statik analiz aracıdır. Bilinmeyen APK'lar güvenilmeyen dosyalar olarak
değerlendirilmelidir; araç tarafından incelenmiş olmaları tek başına çalıştırılmaları için
gerekçe değildir.

## APK'ların yeniden derlenmesi ve imzalanması hakkında

0.3.0 sürümünden itibaren ReaDroid APK'ları yeniden derleyip imzalar da (apktool + zipalign +
apksigner/jarsigner). Bu özelliği yalnızca kendi uygulamalarınızda veya açık izin verdiğiniz
uygulamalarda kullanın:

- Bir APK'yı yeniden imzalamak orijinal geliştiricinin kimliğini değiştirir. Sonuç mağazadaki
  uygulamanın güncellemesi değildir ve Android onu farklı bir uygulama olarak ele alır.
- Başkasının değiştirilmiş APK'sını izin olmadan dağıtmak, özgün uygulamanın lisansını ve kullanım
  koşullarını ihlal edebilir.
- ReaDroid DRM korumalarını, lisans doğrulamasını veya obfuscation'ı aşmaz; yalnızca Android
  ekosistemunun standart derleme akışını otomatikleştirir (Android Open Source Project'ın
  belgelediği `apktool`/`zipalign`/`apksigner` dizisi).

## Bu çeviri hakkında

Arayüz metinleri `locales/tr.json` içindedir ve bir çalışma zamanı hatası değil, kullanıcı
girdisi olarak değerlendirilmelidir: APK'ların içinden gelen metinler `app.sanitize()` ile
temizlenmeden asla ekrana yazılmaz. Bir çeviri hatası bildirmek için README'deki dil seçimi
bölümüne bakın ve `READROID_LANG=pt` ile karşılaştırın.