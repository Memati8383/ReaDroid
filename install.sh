#!/data/data/com.termux/files/usr/bin/bash
# ReaDroid - instalador (uma linha só, no Termux)
#
#   bash -c "$(curl -fsSL https://raw.githubusercontent.com/Memati8383/ReaDroid/main/install.sh)"
#
# O script é idempotente: rodar de novo atualiza em vez de reinstalar.
# Funciona tanto copiado para um checkout já baixado quanto via curl | bash,
# porque não depende de $0 quando não há checkout local.

set -eu

REPO_URL="${READROID_REPO:-https://github.com/Memati8383/ReaDroid.git}"
REPO_DIR="${READROID_DIR:-$HOME/ReaDroid}"
BRANCH="${READROID_BRANCH:-main}"
ASSUME_YES=0
SKIP_DEPS=0
CHECK_ONLY=0
LANG_OVERRIDE="${READROID_LANG:-}"

usage() {
  cat <<'USO'
ReaDroid - instalador

  bash install.sh [opções]

Opções:
  -y, --yes         não perguntar nada (útil em scripts)
      --dir CAMINHO  onde instalar (padrão: ~/ReaDroid)
      --repo URL     repositório de origem
      --branch NOME  branch (padrão: main)
      --lang tr|pt   idioma das mensagens do instalador
      --no-deps      não instalar pacotes do Termux
      --check        só rodar o autoteste, não instala nada
  -h, --help        esta ajuda

Variáveis de ambiente equivalentes: READROID_REPO, READROID_DIR,
READROID_BRANCH, READROID_LANG.
USO
}

# ---------------------------------------------------------------- idioma
case "${LANG_OVERRIDE:-${LC_ALL:-${LC_MESSAGES:-${LANG:-tr}}}}" in
  pt|pt_*|pt.*|pt@*) MSG_LANG=pt ;;
  *)                 MSG_LANG=tr ;;
esac

say() {
  if [ "$MSG_LANG" = pt ]; then
    printf '%s\n' "$1"
  else
    printf '%s\n' "$2"
  fi
}

# ---------------------------------------------------------------- argumentos
while [ $# -gt 0 ]; do
  case "$1" in
    -y|--yes)       ASSUME_YES=1 ;;
    --no-deps)      SKIP_DEPS=1 ;;
    --check)        CHECK_ONLY=1 ;;
    --dir)          [ $# -ge 2 ] || { say "Falta o valor de --dir." "--dir precisa de um caminho."; exit 2; }
                    REPO_DIR="$2"; shift ;;
    --repo)         [ $# -ge 2 ] || { say "Falta o valor de --repo." "--repo precisa de uma URL."; exit 2; }
                    REPO_URL="$2"; shift ;;
    --branch)       [ $# -ge 2 ] || { say "Falta o valor de --branch." "--branch precisa de um nome."; exit 2; }
                    BRANCH="$2"; shift ;;
    --lang)         [ $# -ge 2 ] || { say "Falta o valor de --lang." "--lang precisa de tr ou pt."; exit 2; }
                    MSG_LANG="$2"; shift ;;
    -h|--help)      usage; exit 0 ;;
    *)              say "Opção desconhecida: $1" "Opção desconhecida: $1"; usage; exit 2 ;;
  esac
  shift
done

have() { command -v "$1" >/dev/null 2>&1; }

# "s" é sim em português; "e" é sim na letra de teclado turca (evet).
is_yes() {
  case "$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')" in
    s|sim|yes|y|e|evet) return 0 ;;
    *)                 return 1 ;;
  esac
}

PYTHON=""
for candidate in python python3; do
  if have "$candidate"; then PYTHON="$candidate"; break; fi
done

# ---------------------------------------------------------------- checkout local
# Se este script está rodando de dentro de um checkout do ReaDroid, instalamos
# os pacotes aqui em vez de clonar de novo.
SELF_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  CANDIDATE_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)" || CANDIDATE_DIR=""
  if [ -n "$CANDIDATE_DIR" ] && [ -f "$CANDIDATE_DIR/readroid.py" ] && [ -d "$CANDIDATE_DIR/readroid" ]; then
    SELF_DIR="$CANDIDATE_DIR"
    REPO_DIR="$CANDIDATE_DIR"
  fi
fi

# ---------------------------------------------------------------- repositório
ensure_repo() {
  if [ -n "$SELF_DIR" ]; then
    say "Checkout local encontrado: $REPO_DIR" "Checkout local encontrado: $REPO_DIR"
    update_checkout || return 1
    return 0
  fi

  if [ -d "$REPO_DIR/.git" ] && have git; then
    say "Atualizando $REPO_DIR ..." "Atualizando $REPO_DIR ..."
    update_checkout || return 1
    return 0
  fi

  if [ -f "$REPO_DIR/readroid.py" ] && [ -d "$REPO_DIR/readroid" ]; then
    say "Usando a pasta já baixada: $REPO_DIR" "Usando a pasta já baixada: $REPO_DIR"
    return 0
  fi

  case "$REPO_URL" in
    *'<'*|*'>'*)
      say "A URL do repositório ainda tem o placeholder." "A URL do repositório ainda tem o placeholder."
      say "Defina READROID_REPO e rode de novo:" "Defina READROID_REPO e rode de novo:"
      say "  READROID_REPO=https://github.com/Memati8383/ReaDroid bash install.sh" \
          "  READROID_REPO=https://github.com/Memati8383/ReaDroid bash install.sh"
      return 1
      ;;
  esac

  if ! have git; then
    say "git não encontrado. Rode: pkg install -y git" "git não encontrado. Rode: pkg install -y git"
    return 1
  fi

  say "Clonando $REPO_URL ..." "Clonando $REPO_URL ..."
  mkdir -p "$(dirname "$REPO_DIR")"
  git clone --depth 1 -b "$BRANCH" "$REPO_URL" "$REPO_DIR"
}

# Traz o upstream sem jogar fora edições locais: se não der para avançar rápido,
# avisamos e seguimos com o código que já está na pasta.
update_checkout() {
  [ -d "$REPO_DIR/.git" ] || return 0
  have git || return 0
  git -C "$REPO_DIR" fetch --depth 1 origin "$BRANCH" >/dev/null 2>&1 || return 0
  if git -C "$REPO_DIR" merge --ff-only "origin/$BRANCH" >/dev/null 2>&1; then
    say "Atualizado para origin/$BRANCH." "Atualizado para origin/$BRANCH."
  else
    say "Aviso: há alterações locais em $REPO_DIR; não foi sobrescrito nada." \
        "Aviso: há alterações locais em $REPO_DIR; não foi sobrescrito nada."
    say "Use --dir para instalar numa pasta limpa se quiser o upstream puro." \
        "Use --dir para instalar numa pasta limpa se quiser o upstream puro."
  fi
  return 0
}

# ---------------------------------------------------------------- pacotes
install_deps() {
  if ! have pkg; then
    say "Este instalador foi feito para o Termux (comando 'pkg' não encontrado)." \
        "Este instalador foi feito para o Termux (comando 'pkg' não encontrado)."
    say "Abra o Termux no Android e rode de novo." "Abra o Termux no Android e rode de novo."
    return 1
  fi

  say "" ""
  say "Atualizando a lista de pacotes ..." "Atualizando a lista de pacotes ..."
  pkg update -y >/dev/null 2>&1 || pkg update >/dev/null 2>&1 || true

  say "Instalando Python, Java, JADX, Apktool, aapt e git ..." \
      "Instalando Python, Java, JADX, Apktool, aapt e git ..."
  pkg install -y python openjdk-21 jadx apktool aapt unzip git || true

  # apksigner é opcional por cima do opcional: sem ele, o ReaDroid usa o jarsigner
  # do openjdk (assinatura v1 apenas) para reconstruir e assinar o APK.
  if ! pkg install -y apksigner; then
    say "apksigner indisponível neste repositório; seguindo sem ele (jarsigner cobre o básico)." \
        "apksigner indisponível neste repositório; seguindo sem ele (jarsigner cobre o básico)."
  fi

  if [ -z "$PYTHON" ]; then
    PYTHON="$(command -v python || command -v python3 || true)"
  fi
  if [ -z "$PYTHON" ]; then
    say "ERRO: o Python não ficou disponível. Rode 'pkg install -y python' e tente de novo." \
        "ERRO: o Python não ficou disponível. Rode 'pkg install -y python' e tente de novo."
    return 1
  fi
  return 0
}

# ---------------------------------------------------------------- autoteste
run_selfcheck() {
  if [ -z "$PYTHON" ] || [ ! -f "$REPO_DIR/tools/selfcheck.py" ]; then
    say "Autoteste indisponível (tools/selfcheck.py não encontrado em $REPO_DIR)." \
        "Autoteste indisponível (tools/selfcheck.py não encontrado em $REPO_DIR)."
    return 0
  fi
  say "" ""
  say "Rodando o autoteste ..." "Rodando o autoteste ..."
  if "$PYTHON" "$REPO_DIR/tools/selfcheck.py"; then
    return 0
  fi
  say "O autoteste apontou problemas acima; o menu ainda abre, mas confira a lista." \
      "O autoteste apontou problemas acima; o menu ainda abre, mas confira a lista."
  return 0
}

# ---------------------------------------------------------------- estrutura
make_dirs() {
  mkdir -p "$REPO_DIR/reports" "$REPO_DIR/output" "$REPO_DIR/builds"
}

print_next() {
  say "" ""
  say "Pronto. Estrutura em: $REPO_DIR" "Pronto. Estrutura em: $REPO_DIR"
  say "" ""
  say "  cd \"$REPO_DIR\"" "  cd \"$REPO_DIR\""
  say "  python readroid.py" "  python readroid.py"
  say "" ""
  say "Para escolher APKs da pasta compartilhada, execute uma vez:" \
      "Para escolher APKs da pasta compartilhada, execute uma vez:"
  say "  termux-setup-storage" "  termux-setup-storage"
  say "e use um caminho como:" "e use um caminho como:"
  say "  ~/storage/shared/Download/app.apk" "  ~/storage/shared/Download/app.apk"
  say "" ""
  say "Atualizar depois:   bash \"$REPO_DIR/install.sh\"" "Atualizar depois:   bash \"$REPO_DIR/install.sh\""
  say "Só o autoteste:     bash \"$REPO_DIR/install.sh\" --check" \
      "Só o autoteste:     bash \"$REPO_DIR/install.sh\" --check"
  say "Portekizce/Türkçe:  READROID_LANG=pt python readroid.py" \
      "Portekizce/Türkçe:  READROID_LANG=pt python readroid.py"
}

# ---------------------------------------------------------------- main
if [ "$CHECK_ONLY" = 1 ]; then
  run_selfcheck
  exit $?
fi

if [ "$SKIP_DEPS" = 0 ]; then
  if [ "$ASSUME_YES" = 0 ] && [ -t 0 ]; then
    say "ReaDroid vai ser instalado em: $REPO_DIR" "ReaDroid será instalado em: $REPO_DIR"
    say "Os pacotes opcionais do Termux (Python, Java, JADX, Apktool, aapt, apksigner) serão instalados." \
        "Os pacotes opcionais do Termux (Python, Java, JADX, Apktool, aapt, apksigner) serão instalados."
    printf 'Continuar? [e/H]: '
    read -r reply || reply=""
    if ! is_yes "$reply"; then
      say "Cancelado." "Cancelado."
      exit 0
    fi
  fi
  install_deps
fi

ensure_repo
make_dirs
run_selfcheck
print_next