# ReaDroid

**Android Reverse Engineering Toolkit** — análise estática e reconstrução de APKs para Android 12–16, projetada para rodar no Termux sem root e sem inteligência artificial.

> **OffensiveTec** é uma marca d'água discreta na interface do terminal.

## Recursos

- Inspeção da estrutura ZIP do APK, hashes SHA-256, arquivos DEX e bibliotecas nativas.
- **Leitor de AndroidManifest.xml binário (AXML) nativo**, em Python puro - decodifica o manifesto de
  qualquer APK real sem precisar de JADX, Apktool ou aapt2. Essas ferramentas continuam disponíveis
  como reforço para os raros casos em que o parser próprio não dá conta.
- Busca estática de URLs, domínios (com lista de TLDs reais, pra não confundir nome de classe com domínio)
  e candidatos a endereços IPv4.
- Integração opcional com JADX para decompilar DEX em código Java aproximado.
- Integração opcional com Apktool para extrair recursos e smali.
- **Reconstrução, alinhamento e assinatura automatizados**: depois de editar o smali/recursos extraídos,
  um único fluxo (`apktool b` + `zipalign` + `apksigner`/`jarsigner`) gera um APK pronto para instalar.
- **Edições rápidas** no manifesto decodificado (debuggable, allowBackup, tráfego em texto puro, permissão
  de INTERNET) antes de reconstruir.
- **Renomear o pacote (applicationId)**: move as pastas smali e atualiza as referências de classe,
  além do manifesto - melhor esforço, pensado pra reempacotar seu próprio app com outro nome de pacote.
- Relatórios JSON locais, sem serviços externos ou telemetria.
- Menu de terminal pensado para telas de celular, com saída sanitizada (sem risco de um APK malicioso
  injetar códigos de escape no seu terminal).
- Explorador interativo para navegar e abrir arquivos Java, Kotlin, Smali, XML, JSON, relatórios e os
  APKs reconstruídos diretamente pelo menu.
- Resultado de JADX identificado como sucesso, parcial ou falha conforme o código de saída e os arquivos realmente gerados.
- Saídas salvas na pasta da cópia do projeto em uso, evitando confusão com outra pasta `~/ReaDroid`.

## Compatibilidade

O ReaDroid usa Python e biblioteca padrão para seu núcleo (incluindo a leitura do manifesto). Foi escrito visando Termux ARM64 e Android 12–16, mas não foi possível testar em todos os aparelhos/versões. As ferramentas externas opcionais dependem dos pacotes e da arquitetura disponíveis no repositório Termux do usuário. Compatível com Python 3.9 ou mais novo.

O JADX requer Java compatível; a documentação upstream informa Java 11 ou posterior. O pacote JADX do Termux normalmente depende do OpenJDK empacotado no Termux. Apktool em Android tem incompatibilidades oficiais conhecidas em algumas configurações, portanto o recurso é opcional e deve ser validado no aparelho.

## Instalação no Termux

Atualize os pacotes:

```bash
pkg update && pkg upgrade
pkg install python openjdk-21 jadx apktool aapt unzip git
pkg install apksigner   # opcional, mas recomendado - veja "Reconstrução" abaixo
```

`aapt` já inclui o `zipalign`. Se `openjdk-21`, `jadx`, `apktool` ou `apksigner` não estiverem disponíveis no repositório configurado, instale os pacotes disponíveis e consulte a documentação oficial/README do Termux. O ReaDroid não baixa binários executáveis de terceiros automaticamente.

Clone o repositório (substitua pela URL do seu repositório depois de criá-lo):

```bash
git clone https://github.com/Mcsd7/ReaDroid.git
cd ReaDroid
python readroid.py
```

Ou, se você já baixou os arquivos, execute `bash install.sh` e depois `python readroid.py`.

Para escolher APKs na pasta Download, habilite o acesso ao armazenamento quando o Termux pedir:

```bash
termux-setup-storage
```

Caminho de exemplo: `~/storage/shared/Download/app.apk`.

## Como usar

1. Abra `python readroid.py`.
2. Selecione a análise no menu.
3. Cole o caminho do APK quando solicitado (ou escolha um dos encontrados automaticamente na pasta Download).
4. Consulte relatórios em `reports/` e arquivos exportados em `output/`, dentro da pasta do projeto que você está executando. Use a opção **9 — Explorar e abrir arquivos gerados** para navegar pelas pastas e abrir os arquivos.

O caminho do APK pode ser absoluto ou relativo ao diretório atual. Para a opção JADX, o programa usa no máximo quatro threads (padrão de duas) para reduzir pressão de memória. APKs grandes podem continuar exigindo muita RAM e armazenamento.

## Reconstrução, alinhamento e assinatura (opções 5, 10, 11, 12)

Esse fluxo deixa um APK pronto para instalar sem você precisar decorar `apktool`/`zipalign`/`apksigner`:

1. **Opção 5** decodifica o APK com o Apktool (smali + recursos legíveis).
2. Edite os arquivos dentro da pasta gerada (`output/<app>_apktool/`) com qualquer editor de texto no celular.
   Para ajustes comuns sem editar nada à mão, use a **opção 10** (edições rápidas no manifesto).
3. Ainda na **opção 10** (ou direto na 11, antes de compilar), você pode **renomear o pacote**
   (applicationId). Isso move as pastas `smali`/`smali_classesN` do pacote antigo para o novo e troca
   as referências de classe encontradas nos arquivos `.smali` e no manifesto. É melhor esforço: código
   que monta o nome do pacote via reflection ou em runtime pode não ser coberto - teste o APK reconstruído
   antes de confiar nele.
4. **Opção 11** reconstrói (`apktool b`), alinha (`zipalign`) e assina (`apksigner`, com `jarsigner` como
   alternativa se o apksigner não estiver instalado) em sequência. O APK final fica em `builds/` e,
   se o armazenamento estiver liberado, uma cópia também vai para `Downloads/ReaDroid/`.
5. **Opção 12** mostra ou recria a chave de assinatura usada (gerada automaticamente na primeira
   reconstrução).

Sem o `apksigner`, o ReaDroid usa o `jarsigner` do próprio Java (assinatura v1/JAR apenas). Isso costuma
funcionar, mas apps com `targetSdkVersion` 24 ou mais podem ser recusados pelo instalador do Android 7+
sem a assinatura v2. Instale `pkg install apksigner` para assinatura completa (v1+v2+v3).

**Importante:** use isso só em APKs seus ou que você tem autorização para modificar. Reassinar um app
troca a identidade do desenvolvedor original - o resultado não substitui o app da loja, e redistribuir
o APK modificado de outra pessoa sem permissão pode violar a licença dela. Veja `SECURITY.md`.

## Limitações importantes

- ReaDroid faz análise estática. Não executa o APK nem monitora seu comportamento em tempo real.
- O leitor nativo de AXML cobre o que a maioria das análises precisa (pacote, versão, permissões,
  componentes, flags do `<application>`); para manifestos com estruturas incomuns, a ferramenta ainda
  tenta JADX/Apktool/aapt2 como reforço.
- JADX não recupera perfeitamente todo o código original; nomes podem estar ofuscados e comentários/nomes originais podem ter sido perdidos.
- URLs, domínios, IPs e permissões são pistas para revisão manual, não provas de malware.
- O scanner tem limites de tamanho e de itens por categoria para evitar consumo excessivo de memória; o
  relatório avisa em `truncated_categories` quando uma lista pode estar incompleta.
- A reconstrução depende de `apktool`/`zipalign`/`apksigner` (ou `jarsigner`) estarem instalados; sem
  eles, cada etapa informa exatamente o que falta.
- O ReaDroid não modifica nem assina o APK original - toda reconstrução gera um arquivo novo em `builds/`.

## Segurança e uso responsável

Analise aplicativos próprios, de teste ou para os quais você tem autorização. APKs são arquivos não confiáveis; evite executá-los. A ferramenta chama JADX/Apktool/zipalign/apksigner com argumentos separados (sem shell) e não envia os APKs para a internet. A saída das ferramentas é salva localmente. Veja `SECURITY.md` para as considerações específicas sobre reconstrução e assinatura.

## Testes

Execute:

```bash
python -m unittest discover -s tests -v
```

## Licença

MIT. Consulte `LICENSE`.

## Créditos

ReaDroid é uma interface/automação original que integra ferramentas de terceiros opcionais. JADX, Apktool e apksigner mantêm seus próprios projetos, licenças e termos; veja os links abaixo.

- JADX: https://github.com/skylot/jadx
- Apktool: https://github.com/iBotPeaches/Apktool
- apksigner (Termux): https://github.com/termux/termux-packages
- Termux: https://github.com/termux/termux-app
