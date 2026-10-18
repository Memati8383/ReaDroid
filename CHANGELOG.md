# Changelog

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

### Bilinen sınırlar
- Statik analiz ve yeniden derleme akışının tamamı cihazda doğrulanmadı; çeviri katmanı masaüstünde
  iki dilde test edildi, `apktool`/`zipalign`/`apksigner` zinciri Termux'ta denenmeli.
- Sadece Türkçe ve Portekizce katalogları var. `locales/` altına başka bir dil eklemek için
  `locales/<lang>.json` + `readroid/i18n.py`'deki `detect()` eşiği yeterli.

## 0.1.0 - 2026-10-16
- Primeira versão pública planejada para Termux sem root.
- Menu interativo com marca d'água discreta OffensiveTec.
- Inspeção de APK, hash SHA-256, scanner de strings e relatórios JSON.
- Integração opcional com JADX e Apktool.
- Documentação, instalador opcional e testes básicos.

## 0.2.0
- Corrigido o caminho-base: relatórios e saídas ficam junto da cópia do projeto em execução.
- JADX agora informa sucesso completo, parcial ou falha com base nos arquivos gerados.
- Adicionado explorador interativo para navegar e abrir arquivos decompilados e relatórios pelo menu.
- Melhorada a busca automática por APKs na pasta Download do Termux/Android.

## 0.3.0 - 2026-10-18
- **Leitor de AndroidManifest.xml binário (AXML) nativo, sem dependências.** Antes, o manifesto só
  era lido quando vinha como XML textual (quase nenhum APK real); agora o formato binário que todo
  APK de verdade usa é decodificado em Python puro. JADX/Apktool/aapt2 viraram um reforço para os
  raros casos em que o parser próprio falha, não mais o caminho principal.
- **Reconstrução e compilação automatizada (novo menu 11).** `apktool b` + `zipalign` + assinatura
  (`apksigner`, com `jarsigner` como alternativa) em um fluxo só: decodifique com a opção 5, edite,
  rode a 11 e saia com um APK alinhado e assinado, pronto para instalar - sem decorar comandos.
- **Edições rápidas no manifesto (novo menu 10):** debuggable, allowBackup, tráfego em texto puro e
  permissão de INTERNET, aplicadas direto na pasta decodificada antes da reconstrução.
- **Gerenciamento de chave de assinatura (novo menu 12):** a keystore é criada automaticamente na
  primeira reconstrução e reaproveitada depois.
- Corrigido falso-positivo do scanner de strings: nomes de classes Android/Kotlin (`android.content.pm...`)
  não aparecem mais como "domínio"; a lista de domínios agora usa TLDs reais.
- O relatório do scanner agora avisa quando uma categoria (URLs/domínios/IPs) bateu no limite de itens
  e pode estar incompleta, em vez de descartar o excedente silenciosamente.
- Extensão do arquivo não é mais motivo de recusa (`.xapk`, `.apks` ou qualquer outra são aceitos se o
  conteúdo for um ZIP válido); uma extensão incomum agora só gera um aviso no relatório.
- Corrigido traceback ao fechar o terminal ou pressionar Ctrl+D/Ctrl+C: o menu agora encerra
  normalmente em vez de travar com erro.
- Corrigida a exibição de arquivos no explorador: strings e nomes de arquivo vindos do APK são
  sanitizados antes de aparecer no terminal (remoção de sequências de escape ANSI e caracteres de
  controle), e o `less -R` foi trocado por modo sem interpretação de códigos de escape.
- Corrigido o número de versão reportado pela inspeção de APK (estava fixo em "0.1.0").
- Corrigido o `install.sh`: o caminho final mostrado agora é o caminho real do projeto, não o texto
  literal `$SCRIPT_DIR`.
- Adicionados `.gitignore` e `LICENSE` (MIT).

## 0.3.1
- **Renomear o pacote (applicationId)**, direto na pasta decodificada (opção 10, ou dentro da opção 11
  antes de compilar): atualiza o `package=` do manifesto, move as pastas `smali`/`smali_classesN` do
  caminho antigo para o novo e troca as referências de classe nos arquivos `.smali` (forma com ponto e
  forma `Lcom/pacote/Classe;`). É melhor esforço - reflection, nomes montados em runtime ou ofuscação
  pesada podem escapar da substituição, por isso o ReaDroid avisa pra testar o APK reconstruído antes
  de confiar nele. Nomes de pacote parecidos (`com.x.app` vs `com.x.app2`) não são confundidos entre si.
