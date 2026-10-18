# Changelog

> **Bu dosyanın yapısı:** önce bu fork'a ait değişiklikler (Türkçe), sonra upstream'in sürüm
> geçmişi. Upstream `5dc6f75` commit'iyle belgelerini Portekizceden İngilizceye çevirdi; o çeviri
> `README.en.md` olarak korunuyor, Portekizce orijinaller `README.pt.md`'de. Upstream'in sürüm
> geçmişi İngilizce bırakıldı — kendi içeriği, kendi dilinde.

## Upstream senkronizasyonu

- **`5baa288` birleştirildi** (`MriBoyd` PR #1, "translate documentation files to English").
  Değişen dosyalar: `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`.
  **Kodda değişiklik yok** — `readroid/`, `tests/`, `install.sh` hiç dokunulmadı.
- **Çakışma çözümü:** dört dosyanın da bu fork'un sürümü korundu, çünkü arayüz Türkçe kalmalı.
  Upstream'in İngilizce README'si kaybolmasın diye **`README.en.md` eklendi**; fork'ın ekledikleri
  (tek komut kurulum, selfcheck, Türkçe varsayılan) anlatılarak üzerine yazıldı.
- **Upstream Portekizce `README.md`'yi üzerine yazarak silmişti** — `README.en.md` eklememişlerdi.
  `README.pt.md`, o orijinalin artık tek çalışma ağacı kopyası.
- `CHANGELOG.md` çakışmadan otomatik birleşti: TR bölümü üstte kaldı, sürüm geçmişi
  upstream'in İngilizcesi olarak güncellendi.

## TR - Türkçe Çeviri (bu depo)
- **Arayüz metinlerinin tamamı Türkçeleştirildi** (`readroid/i18n.py` + `locales/tr.json`, 160 anahtar).
  Orijinal Portekizce metinler `locales/pt.json` içinde korunuyor.
- Dil seçimi: `READROID_LANG` > `LC_ALL` > `LC_MESSAGES` > `LANG`. Açık bir `READROID_LANG=pt`
  değeri ortam diline yenik düşer; hiçbiri yoksa fork kendi dilinde (Türkçe) açılır.
- **Evet/hayır artık iki konvansiyonu da kabul ediyor.** Türkçe `[e/H]` yazısına `e` (evet) yazan
  kullanıcı, önceki `== "s"` karşılaştırması yüzünden yanlışlıkla "hayır" alıyordu. `i18n.is_yes()`
  `s/sim/yes/e/evet` tanır.
- `[P]` (Portekizce "outro caminho") yazısı `[Y]` (yol) oldu; eski `p` yanıtı da çalışmaya devam ediyor.
- **Banner kutusu artık sabit 42 karakter değil, içeriğin genişliğinden ölçülüyor.** Türkçe alt
  başlıklar Portekizceden daha uzun ve eski hesap dar terminalde kutuyu taşırıyordu.
- `install.sh` de aynı mekanizmayla iki dilli: Türkçe varsayılan, `READROID_LANG=pt` ile Portekizce.
- JSON raporlarında **anahtarlar İngilizce kaldı** (makine tarafından okunuyor); `note`, `warning`,
  `message`, `security_note` ve `decoded_by` gibi **değerler** etkin dilde yazılıyor.
- **Rapor dosyası adı artık dilden bağımsız.** Önceden arayüz başlığından türetiliyordu
  (`app_inspeção_apk_...`); şimdi sabit bir ASCII tanımlayıcı kullanılıyor (`app_inspection_...`).
  Eski rapor adlarıyla çakışma yaşanabilir.
- `QUICK_EDITS` sözlüğü `QUICK_EDIT_KEYS` + `t()` etiketlerine dönüştü; etiketler artık çalışma
  zamanında çözülüyor.
- `tools/extract_strings.py` bir migrasyon aracı olmaktan çıktı, `t()` sarmalamayı unutan metinleri
  bulan bir linter oldu. `tools/ui_smoke.py` arayüzü APK olmadan render eder.
- `tests/test_i18n.py` eklendi (18 test): katalog anahtar kümesi eşitliği, `{placeholder}` eşleşmesi,
  boş çeviri yokluğu, kodda kullanılan her anahtarın katalogda olması, iki evet/hayır konvansiyonu,
  dil algılama önceliği.
- `tests/test_analyzer.py` metinlere karşı doğrulama yaptığı için Portekizceye sabitlendi; artık
  `LANG=tr` bir terminalde de yeşil.
- Dokümanlar Türkçeleştirildi. Orijinal Portekizce README `README.pt.md` olarak duruyor.

### Tek komut kurulum
- **`install.sh` artık tek başına her şeyi kuruyor.** Tek satır:
  `bash -c "$(curl -fsSL https://raw.githubusercontent.com/.../install.sh)"`.
  Klonlar (veya mevcut checkout'u bulur), `pkg` ile paketleri kurar, otomatik testi
  çalıştırır ve sonraki adımları yazdırır.
- **İdempotent.** Tekrar çalıştırmak yeniden kurmaz; `origin/main`'den `merge --ff-only` dener.
  Yerelde değişiklik varsa üstüne yazmaz, uyarır ve devam eder.
- **Argümanlar:** `-y/--yes`, `--dir`, `--repo`, `--branch`, `--lang tr|pt`, `--no-deps`, `--check`.
  Ortam değişkenleri: `READROID_REPO`, `READROID_DIR`, `READROID_BRANCH`, `READROID_LANG`.
- `curl | bash` ile çalıştırıldığında `$0` bir dosya olmadığı için betik kendi konumunu
  `$HOME/ReaDroid` olarak varsayıyor; ZIP ile indirilip klasör içinden çalıştırıldığında
  bulunduğu klasörü kullanıyor.
- Depo URL'si placeholder olarak kaldıysa ve yerel checkout yoksa, betik ne yapılması
  gerektiğini söyleyip duruyor (sessizce yanlış yere klonlamıyor).
- **`tools/set_repo.py`** placeholder'ı tek komutla dolduruyor: `install.sh`, `README.md`,
  `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md` içindeki `Memati8383` ve ham
  `raw.githubusercontent.com` adreslerini tek seferde güncelliyor. `--check` modu boş çıktı
  verir, CI da bunu adım olarak çalıştırıyor.
- **`tools/selfcheck.py`** kurulum sonrası otomatik çalışıyor: Python sürümü, import,
  iki katalogun bütünlüğü, kodda kullanılan anahtarların varlığı, banner'ın 32/40/50/72
  kolonda sığması, sahte APK üzerinde analiz ve JSON rapor yazımı, harici araç listesi.
  Çıkış kodu CI'a gider.

### Düzeltilen hatalar
- **Banner dar terminalde taşıyordu.** Kutu sabit 42 karakterden geliyordu; Türkçe alt
  başlık 41 karakter, terminaller 32–40 kolona inince sağ kenar bozuluyordu. Artık kutu
  içeriğin genişliğinden ölçülüyor ve sığmayan metin `…` ile kırpılıyor. `tools/selfcheck.py`
  bu koşulu dört genişlikte test ediyor.
- **`ask_decoded_dir()` çökebiliyordu.** `stat()` sıralama anahtarı içindeydi; menü açıkken
  `output/` silinirse `FileNotFoundError` traceback basıyordu. Artık `OSError` yutuluyor.
- **Kod dışı bir kod sayfasında UnicodeEncodeError.** `readroid.py` ve `python -m readroid`
  artık çıktı akışını UTF-8'e zorluyor (`errors="replace"`); `tools/` betikleri de aynı
  korumayı alıyor.
- Bağımlılık listesine `jarsigner`, `less` ve `termux-open` eklendi — gezgin bunları
  fiilen kullanıyor, ama listede yoktu.

### Cihazda doğrulama (Android 16 / SDK 36 / arm64-v8a, Termux, Python 3.14.6)
Tam zincir gerçek bir cihazda çalıştırıldı: probe APK üretimi → 1/2/3 → 5 → 10 → 11 → 12 →
`apksigner verify`. Yeniden derlenen APK, taşınan paket adını (`com.sondurum.probe`) ve izni
kendi içinde korudu. Bu turda çıkan üç gerçek hata:

- **Varsayılan dil hiç devreye girmiyordu.** `detect()` `LANG`'e bakıp `tr` değilse `pt`
  döndürüyordu. Termux'ta `LANG` Android varsayılanı olarak `en_US.UTF-8` geldiği için Türkçe
  kullanıcı, `READROID_LANG=tr` yazmadıkça **Portekizce** görüyordu. Artık `LANG=en_US.UTF-8`
  Türkçe açar; Portekizce için açıkça `READROID_LANG=pt` gerekir. Regresyon testi eklendi.
- **İmza şeması uyduruluyordu.** `sign_apk` her `apksigner` imzası için `"v1 + v2 + v3"`
  yazıyordu; cihazdaki doğrulama `v1: false, v2: true, v3: true` gösterdi — `apksigner` v1'i
  ancak APK'nın minSdk'sı istediğinde uyguluyor. Artık şema beyan edilmiyor, `verify_apk`
  `apksigner verify --verbose` çıktısını ayrıştırıp **gerçekten uygulanan** şemaları raporluyor.
- **`tools/selfcheck.py` Termux'u yanlış algılıyordu.** `pkg --version` Termux'ta geçerli bir
  komut değil (`Unknown command`) ve hep 1 dönüyordu, yani otomatik test her cihazda hata
  veriyordu. Algılama artık `PREFIX` ve `pkg` varlığına bakıyor.

### Cihazda bulunan, ReaDroid'a ait olmayan kırılma
Termux'un `aapt2 16.0.0.4-3` paketi, kurulu `libprotobuf 2:35.1` ile uyumsuzdu
(`cannot locate symbol ...google8protobuf8internal8TcParser15MpUnknownFields`); `aapt2 version`
bile çalışmıyordu. apktool 3 kaynak derlemek için `aapt2`'yi çağırdığı için **menü 11 tamamen
ölüydü**. `pkg upgrade -y protobuf libprotobuf` ile düzeldi. Artık `selfcheck.py` bu kırılmayı
yakalayıp tek komutu söylüyor ve README'ye "Sorun giderme" bölümü eklendi.

### Bilinen sınırlar
- Statik analiz ve yeniden derleme akışının tamamı cihazda doğrulanmadı; çeviri katmanı masaüstünde
  iki dilde test edildi, `apktool`/`zipalign`/`apksigner` zinciri Termux'ta denenmeli.
- Sadece Türkçe ve Portekizce katalogları var. `locales/` altına başka bir dil eklemek için
  `locales/<lang>.json` + `readroid/i18n.py`'deki `detect()` eşiği yeterli.

## 0.1.0 - 2026-10-16
- Initial public release designed for non-root Termux.
- Interactive menu featuring a subtle OffensiveTec watermark.
- APK inspection, SHA-256 hash calculation, string scanner, and JSON reports.
- Optional JADX and Apktool integrations.
- Documentation, optional installer script, and basic tests.

## 0.2.0
- Fixed base path resolution: reports and outputs are stored alongside the running project clone.
- JADX now reports full success, partial output, or failure based on generated files.
- Added interactive file explorer to navigate and open decompiled files and reports from the menu.
- Improved automatic APK discovery in the Termux/Android Download directory.

## 0.3.0 - 2026-10-18
- **Native binary AndroidManifest.xml (AXML) parser with zero dependencies.** Previously, manifests
  were only parsed when present as plain text XML (almost no real-world APKs); the binary format used by
  real APKs is now decoded in pure Python. JADX/Apktool/aapt2 serve as fallbacks for
  rare parser failures rather than the primary path.
- **Automated rebuilding and compilation (new menu option 11).** `apktool b` + `zipalign` + signing
  (`apksigner`, with `jarsigner` fallback) in a single workflow: decode with option 5, edit,
  run option 11, and obtain an aligned, signed, install-ready APK — without memorizing commands.
- **Quick manifest edits (new menu option 10):** debuggable, allowBackup, cleartext traffic, and
  INTERNET permission, applied directly to the decoded directory before rebuilding.
- **Signing key management (new menu option 12):** the keystore is automatically created during the
  first rebuild and reused for subsequent builds.
- Fixed string scanner false positives: Android/Kotlin class names (`android.content.pm...`)
  no longer match as "domains"; domain matching now verifies against real TLDs.
- Scanner reports now indicate when a category (URLs/domains/IPs) hits item limits
  and may be truncated, rather than discarding items silently.
- File extensions are no longer rejected (`.xapk`, `.apks`, or any extension are accepted as long as the
  file is a valid ZIP archive); unusual extensions now generate an informational notice in the report.
- Fixed traceback on terminal close or Ctrl+D/Ctrl+C: the menu now exits cleanly
  instead of crashing with an unhandled exception.
- Fixed file viewing in the explorer: strings and filenames from APKs are
  sanitized before display (stripping ANSI escape sequences and control characters),
  and `less -R` was replaced with safe raw display mode.
- Fixed version number reported during APK inspection (previously hardcoded to "0.1.0").
- Fixed `install.sh`: the final path displayed now shows the actual project directory rather than
  literal `$SCRIPT_DIR`.
- Added `.gitignore` and `LICENSE` (MIT).

## 0.3.1
- **Package renaming (applicationId)** directly in the decoded directory (option 10, or within option 11
  prior to building): updates manifest `package=`, moves `smali`/`smali_classesN` directories from
  the old path to the new path, and rewrites class references across `.smali` files (both dotted format and
  `Lcom/package/Class;` format). This is best-effort — reflection, dynamically assembled strings, or heavy
  obfuscation may not be replaced, so ReaDroid prompts you to test the rebuilt APK before
  relying on it. Similar package names (e.g., `com.x.app` vs `com.x.app2`) are not conflated.
