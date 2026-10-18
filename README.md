# ReaDroid — Türkçe

**Android Tersine Mühendislik Araç Kutusu** — Android 12–16 için statik APK analizi ve yeniden derleme. Termux üzerinde root'suz ve yapay zekâsız çalışmak için tasarlandı.

> Bu depo, [Memati8383/ReaDroid](https://github.com/Memati8383/ReaDroid) projesinin **Türkçe çevirisidir**. Kod, çekirdek mantık ve araç zinciri orijinaline aittir; bu çalışma yalnızca arayüz metinlerini ve belgeleri Türkçeleştirir.

## Dil seçimi

Arayüz dili **Türkçedir**; Portekizce isteyen tek yol açıkça söylemektir:

```bash
python readroid.py                     # Türkçe (varsayılan)
READROID_LANG=tr python readroid.py    # Türkçe (açık)
READROID_LANG=pt python readroid.py    # Orijinal Portekizce metinler
```

Metinler `locales/tr.json` ve `locales/pt.json` içinde, anlamsal anahtarlarla tutulur. Bir metni değiştirmek için kodu değil, kataloğu düzenleyin.

Sıra `READROID_LANG` > `LC_ALL` > `LC_MESSAGES` > `LANG`. Açık bir `READROID_LANG` her zaman kazanır: `tr_TR.UTF-8` olan bir makinede bile `READROID_LANG=pt` Portekizce açar.

> `LANG=en_US.UTF-8` (Android'de fabrika ayarı) **Portekizce anlamına gelmez** — Türkçe açar. Bu bilinçli bir tercih: depo Türkçe konuşanlar için var, sistem dilini yanlışlıkla Portekizce'ye çevirmek istemiyoruz.

---

## Bu çeviri hakkında

- **Varsayılan dil Türkçedir.** Orijinal davranış `READROID_LANG=pt` ile bir düğme kadar uzakta.
- Evet/hayır soruları her iki alışkanlığı da kabul eder: `[e/H]` yazısını görüp `e` yazan kullanıcı da, `[s/N]` görüp `s` yazan kullanıcı da doğru davranır.
- Menüdeki `[Y]` (yol) seçeneği, Portekizcedeki `[P]` karşılığıdır; eski `p` yanıtı da çalışır.
- JSON raporlarının **anahtarları** İngilizce kalır (makine tarafından okunur); `note`, `warning`, `message` gibi **değerler** etkin dilde yazılır.
- Rapor dosyası adları dilden bağımsızdır: `app_inspection_20261018_120000.json`. Önceki sürümlerde dosya adı arayüz başlığından türetiliyordu, bu yüzden eski raporlarla isim çakışması olabilir.
- Kod içindeki yorumlar ve docstring'ler bilinçli olarak Portekizce bırakıldı — upstream'in konvansiyonu bu ve orijinalle farkın küçük kalmasını sağlıyor.

---

## Özellikler

- APK'nın ZIP yapısını inceleme, SHA-256 özetleri, DEX dosyaları ve yerel kütüphaneler.
- **Saf Python ile yazılmış, yerel ikili (AXML) `AndroidManifest.xml` okuyucu.** Gerçek bir APK'nın
  manifestini JADX, Apktool veya aapt2 olmadan çözer. Bu araçlar, kendi ayrıştırıcısının yetmediği
  enderka durumlar için yedek olarak duruyor.
- Statik URL, alan adı (sınıf adını alan adıyla karıştırmamak için gerçek TLD listesiyle) ve
  aday IPv4 adresi arama.
- DEX'i yaklaşık Java koduna çözmek için isteğe bağlı JADX entegrasyonu.
- Kaynakları ve smali'yi çıkarmak için isteğe bağlı Apktool entegrasyonu.
- **Otomatik yeniden derleme, hizalama ve imzalama**: çıkarılan smali/kaynakları düzenledikten sonra
  tek akış (`apktool b` + `zipalign` + `apksigner`/`jarsigner`) kuruluma hazır bir APK üretir.
- Çözülmüş manifest üzerinde **hızlı düzenlemeler** (debuggable, allowBackup, düz metin trafiği,
  INTERNET izni) — yeniden derlemeden önce.
- **Paketi (applicationId) yeniden adlandırma**: smali klasörlerini taşır ve sınıf referanslarını
  günceller; kendi uygulamanızı farklı bir paket adıyla yeniden paketlemek için tasarlandı.
- Yalnızca yerel JSON raporları; dış servis veya telemetri yok.
- Telefon ekranı için tasarlanmış terminal menüsü, temizlenmiş çıktı ile (kötü amaçlı bir APK
  terminalinize kaçış kodu enjekte edemez).
- Java, Kotlin, Smali, XML, JSON, raporlar ve yeniden derlenmiş APK'lar üretilen dosyalar için
  menüden gezilebilir etkileşimli dosya gezgini.
- JADX sonucu, çıkış koduna ve gerçekten üretilen dosyalara göre başarılı / kısmi / başarısız
  olarak ayrılır.
- Çıktılar, çalıştırdığınız proje kopyasının içine kaydedilir — diğer bir `~/ReaDroid` klasörüyle
  karışmaz.

## Uyumluluk

ReaDroid çekirdeği için (manifest okuma dahil) yalnızca Python ve standart kütüphanesini kullanır.
Termux ARM64 ve Android 12–16 hedeflenerek yazıldı, ancak her cihaz/sürümde test edilemedi. İsteğe
bağlı harici araçlar, kullanıcının Termux deposunda bulunan paketlere ve mimariye bağlıdır.
Python 3.9 ve üzeri gerekir.

JADX uyumlu bir Java ister; upstream dokümantasyonuna göre Java 11 veya sonrası. Termux'taki JADX
paketi genellikle Termux ile gelen OpenJDK'ya bağımlıdır. Apktool'ın Android'de bazı yapılandırmalarda
bilinen resmî uyumsuzlukları var; bu yüzden özellik isteğe bağlıdır ve cihazda doğrulanmalıdır.

## Termux'a kurulum

### Tek komut

Termux'u açıp şu tek satırı yapıştırın — klonlar, paketleri kurar, otomatik testi
çalıştırır ve size ne yapacağınızı söyler:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/<KULLANICI-ADIN>/ReaDroid-TR/main/install.sh)"
```

İlk seferde onay ister (`[e/H]`). Onaylamadan kurmak için:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/<KULLANICI-ADIN>/ReaDroid-TR/main/install.sh)" -- -y
```

Farklı klasöre kurmak, paket kurmadan çalıştırmak, başka kaynak kullanmak veya sadece test etmek:

```bash
bash install.sh --dir ~/ReaDroid                          # farklı klasör
bash install.sh --check                                  # sadece otomatik test, hiçbir şey kurmaz
bash install.sh --repo https://github.com/KULLANICI/ReaDroid-TR.git   # başka kaynak
bash install.sh --lang pt                                # Portekizce mesajlar
```

`install.sh` **idempotenttir**: tekrar çalıştırmak yeniden kurmaz, `origin/main`'den günceller.
Yerelde yaptığınız değişiklikler varsa üstüne yazılmaz, uyarı verir.

Kurulumdan sonra:

```bash
cd ~/ReaDroid
python readroid.py
```

### Elle kurulum

```bash
pkg update && pkg upgrade
pkg install python openjdk-21 jadx apktool aapt unzip git
pkg install apksigner   # isteğe bağlı ama önerilir - aşağıdaki "Yeniden derleme" bölümüne bakın
```

`aapt` paketi `zipalign` aracını zaten içerir. `openjdk-21`, `jadx`, `apktool` veya `apksigner`
yapılandırılmış depoda yoksa, bulunan paketleri kurun ve Termux'in resmî dokümantasyonuna başvurun.
ReaDroid üçüncü taraf çalıştırılabilir dosyalarını kendiliğinden indirmez.

Depoyu elle kopyalayın:

```bash
git clone https://github.com/<KULLANICI-ADIN>/ReaDroid-TR.git
cd ReaDroid-TR
bash install.sh --check     # kurmadan önce doğrula
python readroid.py
```

Dosyaları ZIP olarak indirdiyseniz aynı şekilde: klasörün içinde `bash install.sh`.

Download klasöründen APK seçebilmek için Termux istediğinde depolama iznini verin:

```bash
termux-setup-storage
```

Örnek yol: `~/storage/shared/Download/uygulama.apk`.

### Terminal genişliği

Menü çerçevesi terminalin genişliğine göre kendini ayarlar; 32 kolonluk dar ekranda bile taşmaz.
Yine de ReaDroid'ı `tmux` veya `screen` içinde çalıştırmak en rahat deneyimdir.

### Otomatik test

Kurulumdan sonra, ya da istediğiniz zaman eksik olanı görmek için:

```bash
python tools/selfcheck.py
```

İmporter, katalog bütünlüğü, 32/40/50/72 kolonluk çerçeve sığması, sahte bir APK üzerinde
analiz ve JSON rapor yazımı kontrol edilir; harici araçlardan hangisinin bulunduğunu listeler.

### Sorun giderme

**11. seçenek "Building resources with aapt2" adımında kırılıyor.**
Termux'un `aapt2` paketi bazen kurulu `libprotobuf`'dan yeni bir ABI'ye bağlanmış olur ve
`cannot locate symbol ...TcParser15MpUnknownFields` hatası verir — `aapt2 version` bile
çalışmaz. Bu ReaDroid'ın hatası değildir; apktool 3 kaynakları derlemek için `aapt2`'yi çağırır.
Çözüm kütüphaneyi yükseltmektir:

```bash
pkg upgrade -y protobuf libprotobuf
```

**Menü Portekizce açıyor.**
`READROID_LANG=pt` verilmiş demektir. `echo $READROID_LANG` ile bakın; temizlemek için
`unset READROID_LANG`.

**JADX "JAVA_HOME is not set and no 'java' command could be found" diyor.**
Genelde `jadx` sarmalayıcısının `PATH`'i görememesinden olur. Etkileşimli bir Termux oturumunda
çalışır, ssh/CI gibi sıfır `PATH`'li bir bağlamda çalışmaz. `pkg install openjdk-21` sonrası
tekrar deneyin.

**Download klasöründeki APK'lar listede çıkmıyor.**
Bir kez `termux-setup-storage` çalıştırın; Android depolama izni ister.

**Türkçe karakterler bozuk görünüyor.**
`tmux`/`screen` içinde `LANG` ayarlanmamış olabilir. `locale` çıktısında UTF-8 yoksa
`export LANG=C.UTF-8` deneyin.

## Nasıl kullanılır

1. `python readroid.py` çalıştırın.
2. Menüden analizi seçin.
3. İstendiğinde APK yolunu girin (ya da Download klasöründe otomatik bulunanlardan birini seçin).
4. Raporları `reports/`, dışa aktarılan dosyaları `output/` içinde, çalıştırdığınız proje klasöründe
   bulun. Klasörlerde gezinmek ve dosyaları açmak için **9 — Üretilen dosyalara göz at ve aç**
   seçeneğini kullanın.

APK yolu mutlak veya bulunduğunuz dizine göreli olabilir. JADX seçeneğinde program bellek baskısını
azaltmak için en fazla dört iş parçacığı kullanır (varsayılan iki). Büyük APK'lar hâlâ bol RAM ve
depolama isteyebilir.

## Yeniden derleme, hizalama ve imzalama (5, 10, 11, 12 numaralı seçenekler)

Bu akış, `apktool`/`zipalign`/`apksigner` komutlarını ezberlemeden kuruluma hazır bir APK üretir:

1. **5. seçenek** APK'yı Apktool ile çözer (okunabilir smali + kaynaklar).
2. Üretilen klasördeki (`output/<app>_apktool/`) dosyaları telefondaki herhangi bir metin editörüyle
   düzenleyin. Elle uğraşmak istemediğiniz sıradan ayarlar için **10. seçeneği** (manifest üzerinde
   hızlı düzenlemeler) kullanın.
3. Yine **10. seçenekte** (ya da doğrudan 11'de, derlemeden önce) **paketi yeniden adlandırabilirsiniz**
   (applicationId). Bu işlem `smali`/`smali_classesN` klasörlerini eski paketten yenisine taşır ve
   `.smali` dosyaları ile manifestteki sınıf referanslarını değiştirir. En iyi çaba yöntemidir:
   paket adını reflection veya çalışma zamanında oluşturan kod kapsanamayabilir — güvenmeden önce
   yeniden derlenmiş APK'yı test edin.
4. **11. seçenek** sırasıyla yeniden derler (`apktool b`), hizalar (`zipalign`) ve imzalar
   (`apksigner`; apksigner kurulu değilse `jarsigner` alternatifi). Son APK `builds/` içine düşer ve
   depolama izni verilmişse bir kopyası `Downloads/ReaDroid/` klasörüne de gider.
5. **12. seçenek** kullanılan imzalama anahtarını gösterir veya yeniden oluşturur (ilk yeniden
   derlemede otomatik oluşturulur).

`apksigner` yoksa ReaDroid, Java'nın kendi `jarsigner` aracını kullanır (yalnızca v1/JAR imzası). Bu
genellikle çalışır, ancak `targetSdkVersion` değeri 24 veya üzeri olan uygulamalar v2 imzası olmadan
Android 7+ yükleyicisi tarafından reddedilebilir. Tam imza (v1+v2+v3) için `pkg install apksigner`
çalıştırın.

**Önemli:** bunu yalnızca kendi APK'larınızda veya değiştirmeye yetkili olduğunuz APK'larda kullanın.
Bir uygulamayı yeniden imzalamak orijinal geliştiricinin kimliğini değiştirir — sonuç mağazadaki
uygulamanın yerini almaz ve başkasının değiştirilmiş APK'sını izin olmadan dağıtmak onun lisansını
ihlal edebilir. `SECURITY.md` bölümüne bakın.

## Önemli sınırlar

- ReaDroid statik analiz yapar. APK'yı çalıştırmaz, davranışını gerçek zamanlı izlemez.
- Yerel AXML okuyucu, çoğu analizin ihtiyaç duyduğu alanı kapsar (paket, sürüm, izinler, bileşenler,
  `<application>` bayrakları); alışılmadık yapılara sahip manifestlerde araç yine de
  JADX/Apktool/aapt2'yi yedek olarak dener.
- JADX özgün kodun tamamını kusursuz geri getirmez; adlar bulanıklaştırılmış olabilir, özgün
  yorumlar ve adlar kaybolmuş olabilir.
- URL'ler, alan adları, IP'ler ve izinler elle inceleme ipuçlarıdır — kötü amaçlı yazılım kanıtı değildir.
- Tarayıcı, aşırı bellek tüketimini önlemek için boyut ve kategori başına öğe sınırı uygular;
  bir liste eksik olabilecekse rapor `truncated_categories` alanında uyarır.
- Yeniden derleme, `apktool`/`zipalign`/`apksigner` (ya da `jarsigner`) kurulu olmasına bağlıdır;
  bunlar yokken her adım eksik olanı açıkça söyler.
- ReaDroid orijinal APK'yı değiştirmez ve imzalamaz — her yeniden derleme `builds/` içinde yeni bir
  dosya üretir.

## Güvenlik ve sorumlu kullanım

Kendi, test amaçlı veya değiştirmeye yetkili olduğunuz uygulamaları inceleyin. APK'lar güvenilmeyen
dosyalardır; çalıştırmaktan kaçının. Araç JADX/Apktool/zipalign/apksigner'ı ayrı argümanlarla çağırır
(shell üzerinden değil) ve APK'ları internete göndermez. Araç çıktıları yerel olarak kaydedilir.
Yeniden derleme ve imzalamaya özel hususlar için `SECURITY.md` dosyasına bakın.

## Testler

```bash
python -m unittest discover -s tests -v
```

Testler dilden bağımsız çalışır. Metinlere doğrulama yapan `tests/test_analyzer.py` Portekizce'yi
sabitler; `tests/test_i18n.py` iki katalogun anahtar kümesinin aynı olduğunu, `{placeholder}` eşleşmelerini,
boş çevirilerin olmadığını ve iki evet/hayır konvansiyonunun da tanındığını doğrular.

Yeni bir metin eklerken:

```bash
python tools/extract_strings.py --stats   # t() sarmalaymayı unuttuğun metinleri listeler
```

## Lisans

MIT. `LICENSE` dosyasına bakın.

## Krediler

ReaDroid, isteğe bağlı üçüncü taraf araçları bütünleştiren özgün bir arayüz/otomasyondur. Orijinal
proje [Memati8383/ReaDroid](https://github.com/Memati8383/ReaDroid) — telif hakkı OffensiveTec'e
aittir. JADX, Apktool ve apksigner kendi projeleri, lisansları ve koşullarıyla ayrıdır:

- JADX: https://github.com/skylot/jadx
- Apktool: https://github.com/iBotPeaches/Apktool
- apksigner (Termux): https://github.com/termux/termux-packages
- Termux: https://github.com/termux/termux-app

Türkçe çeviri, `locales/tr.json` ve bu dokümantasyon bu depoya özeldir.