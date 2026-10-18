#!/data/data/com.termux/files/usr/bin/bash
# Instalador opcional: mostra o que será instalado e pede confirmação.
# Idioma: READROID_LANG=tr (padrão), READROID_LANG=pt, ou o LANG do Termux.
set -eu
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

case "${READROID_LANG:-${LC_ALL:-${LC_MESSAGES:-${LANG:-tr}}}}" in
  pt|pt_*|pt.*|pt@*) MSG_LANG=pt ;;
  *)                 MSG_LANG=tr ;;
esac

# "s" é sim no português; "e" é sim na letra de teclado turca (evet).
is_yes() {
  case "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" in
    s|sim|yes|e|evet) return 0 ;;
    *)                return 1 ;;
  esac
}

if [ -z "${PREFIX:-}" ] || [ ! -d "$PREFIX" ]; then
  if [ "$MSG_LANG" = pt ]; then
    echo "Este instalador foi feito para Termux. Abra o Termux e tente novamente."
  else
    echo "Bu kurulum betiği Termux için yazıldı. Lütfen Termux'u açıp tekrar deneyin."
  fi
  exit 1
fi

if [ "$MSG_LANG" = pt ]; then
  cat <<'BANNER'

ReaDroid - configuração inicial
O núcleo usa apenas a biblioteca padrão do Python.
JADX, Apktool, aapt (zipalign) e apksigner são opcionais, para decompilação,
extração avançada e para reconstruir/assinar um APK já pronto para instalar.
BANNER
  read -r -p 'Instalar/atualizar Python, Java, JADX, Apktool, aapt e apksigner via pkg? [s/N] ' answer
else
  cat <<'BANNER'

ReaDroid - ilk kurulum
Çekirdek yalnızca Python standart kütüphanesini kullanır.
JADX, Apktool, aapt (zipalign) ve apksigner isteğe bağlıdır: çözümleme,
gelişmiş çıkarma ve kuruluma hazır bir APK'yi yeniden derleyip imzalama için.
BANNER
  read -r -p 'Python, Java, JADX, Apktool, aapt ve apksigner pkg ile kurulsun/güncellensin mi? [e/H] ' answer
fi

if is_yes "$answer"; then
  pkg update
  pkg install python openjdk-21 jadx apktool aapt unzip -y
  # apksigner é opcional por cima do opcional: sem ele, o ReaDroid usa o jarsigner
  # do openjdk (assinatura v1 apenas) para reconstruir e assinar o APK.
  if ! pkg install apksigner -y; then
    if [ "$MSG_LANG" = pt ]; then
      echo "apksigner indisponível neste repositório; seguindo sem ele (jarsigner cobre o básico)."
    else
      echo "apksigner bu depoda bulunamadı; onsuz devam ediliyor (jarsigner temel ihtiyacı karşılar)."
    fi
  fi
else
  if [ "$MSG_LANG" = pt ]; then
    echo "Pulando instalação de pacotes. O menu básico ainda pode ser usado."
  else
    echo "Paket kurulumu atlanıyor. Temel menü yine de kullanılabilir."
  fi
fi

mkdir -p "$SCRIPT_DIR/reports" "$SCRIPT_DIR/output" "$SCRIPT_DIR/builds"

if [ "$MSG_LANG" = pt ]; then
cat <<MSG

Estrutura preparada em: $SCRIPT_DIR
Para iniciar, execute:
  cd "$SCRIPT_DIR"
  python readroid.py

Se quiser escolher APKs da pasta compartilhada, execute uma vez:
  termux-setup-storage
E use um caminho como:
  ~/storage/shared/Download/aplicativo.apk

A opção 11 do menu (reconstruir, alinhar e assinar) gera uma chave de
assinatura própria na primeira vez que você usar, em:
  $SCRIPT_DIR/.readroid-keystore.jks
MSG
else
cat <<MSG

Klasör yapısı hazırlandı: $SCRIPT_DIR
Başlatmak için:
  cd "$SCRIPT_DIR"
  python readroid.py

Paylaşılan klasörden APK seçmek isterseniz bir kez şunu çalıştırın:
  termux-setup-storage
ve şu tür bir yol kullanın:
  ~/storage/shared/Download/uygulama.apk

Menüdeki 11. seçenek (yeniden derle, hizala, imzala) ilk kullanımda kendi
imzalama anahtarınızı üretir; anahtar şu konumda durur:
  $SCRIPT_DIR/.readroid-keystore.jks
MSG
fi