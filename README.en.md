# ReaDroid — English

**Android Reverse Engineering Toolkit** — static analysis and APK rebuilding for Android 12–16,
designed to run on Termux without root and without AI.

> **The interface is Turkish by default.** This file documents the same tool in English.
> Turkish: [README.md](README.md) · Original Portuguese (upstream): [README.pt.md](README.pt.md)

> **This repository is the Turkish-localized fork of [Mcsd7/ReaDroid](https://github.com/Mcsd7/ReaDroid)**
> (MIT, © OffensiveTec). The upstream documentation was translated into English by
> [MriBoyd](https://github.com/MriBoyd) (PR #1) and is preserved here, updated with what this fork adds:
> the localization layer, the one-command installer and the automated self-check.
> Upstream's Portuguese originals were overwritten in PR #1; this fork keeps them in `README.pt.md`.

> **OffensiveTec** is a subtle watermark in the terminal interface.

---

## Language selection

The interface language is resolved in this order:

```
READROID_LANG > LC_ALL > LC_MESSAGES > LANG
```

- **Turkish is the default.** A foreign locale such as `LANG=en_US.UTF-8` (Android's factory value)
  opens Turkish, not Portuguese.
- `READROID_LANG=pt python readroid.py` → Portuguese
- `READROID_LANG=tr python readroid.py` → Turkish (explicit)

Yes/no questions accept both conventions: typing `e` (evet) at a `[e/H]` prompt and typing `s` at a
`[s/N]` prompt both work. The `[Y]` (yol / path) shortcut also still accepts `p`.

---

## Features

- Inspection of APK ZIP structure, SHA-256 hashes, DEX files, and native libraries.
- **Native binary AndroidManifest.xml (AXML) parser**, in pure Python — decodes the manifest of
  any real-world APK without requiring JADX, Apktool, or aapt2. These tools remain available
  as fallbacks for the rare cases where the built-in parser cannot handle the structure.
- Static extraction of URLs, domains (validated against a list of real TLDs to avoid mistaking
  class names for domains), and IPv4 address candidates.
- Optional JADX integration to decompile DEX into approximate Java code.
- Optional Apktool integration to extract resources and smali.
- **Automated rebuilding, alignment, and signing**: after editing extracted smali/resources,
  a single workflow (`apktool b` + `zipalign` + `apksigner`/`jarsigner`) outputs an install-ready APK.
- **Quick edits** to the decoded manifest (debuggable, allowBackup, cleartext traffic, INTERNET
  permission) before rebuilding.
- **Package renaming (applicationId)**: moves smali folders and updates class references as well as
  the manifest — best-effort, intended for repackaging your own app under a different package name.
- Local JSON reports, no external services and no telemetry.
- A terminal menu sized for phone screens, with sanitized output (a malicious APK cannot inject
  escape codes into your terminal).
- Interactive file explorer to browse and view Java, Kotlin, Smali, XML, JSON files, reports, and
  rebuilt APKs directly from the menu.
- JADX results classified as success, partial, or failure based on the exit code and generated files.
- Outputs saved in the active project directory, avoiding confusion with another `~/ReaDroid` path.
- **This fork:** Turkish interface with Portuguese available on request, a one-command installer,
  and `tools/selfcheck.py` which verifies the whole setup after installation.

---

## Compatibility

ReaDroid relies on Python and the standard library for its core functionality (including manifest
parsing) — there is nothing to `pip install`. It was written targeting Termux ARM64 and Android
12–16. Optional external tools depend on the packages available in the user's Termux repository.
Compatible with Python 3.9 or newer.

The full chain has been exercised on a real device:

| Component | Required | Verified on device |
|---|---|---|
| Python | 3.9+ | 3.14.6 |
| Android | 12–16 | **16 (SDK 36)** |
| Termux | ARM64 | arm64-v8a, kernel 6.6 |
| JDK | 11+ | openjdk-21 (21.0.12) |
| apktool | 2.x or 3.x | **3.0.3** |
| jadx | — | 1.5.6 |
| aapt / aapt2 | — | 16.0.0.4 (aapt2 2.20) |
| zipalign | ships with the `aapt` package | working |
| apksigner | recommended | Termux 37.0.0 — **v2 + v3 signature verified** |

JADX requires a compatible Java runtime; upstream documentation specifies Java 11 or later.
Apktool on Android has known official incompatibilities in certain configurations, so that feature
is optional and should be validated on your device.

> `apksigner` only applies a v1 signature when the APK's `minSdk` asks for it. ReaDroid does not
> guess: it reads the schemes actually applied from `apksigner verify` output and reports those.

---

## Installation on Termux

### One command

Paste this single line into Termux. The script fetches the project, installs the Termux packages,
runs a self-check and tells you what to do next:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Memati8383/ReaDroid/main/install.sh)"
```

It asks for confirmation on first run (`[e/H]`). To skip the prompt:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Memati8383/ReaDroid/main/install.sh)" -- -y
```

| Option | Effect |
|---|---|
| `-y`, `--yes` | Do not ask for confirmation |
| `--check` | Run the self-check only, install nothing |
| `--dir PATH` | Install somewhere else (default `~/ReaDroid`) |
| `--repo URL` | Fetch from a different repository |
| `--branch NAME` | Use a different branch |
| `--lang tr\|pt` | Language of the installer messages |
| `--no-deps` | Place the code without touching Termux packages |

The script is **idempotent**: running it again updates instead of reinstalling, and it will not
overwrite local modifications — it warns instead. Environment variables: `READROID_REPO`,
`READROID_DIR`, `READROID_BRANCH`, `READROID_LANG`.

### Manual installation

```bash
pkg update && pkg upgrade
pkg install python openjdk-21 jadx apktool aapt unzip git
pkg install apksigner   # optional, but recommended - see "Rebuilding" below
```

`aapt` already includes `zipalign`. If `openjdk-21`, `jadx`, `apktool`, or `apksigner` are not
available in your configured repository, install the available packages and consult the official
Termux documentation. ReaDroid does not automatically download third-party executable binaries.

```bash
git clone https://github.com/Memati8383/ReaDroid.git
cd ReaDroid
bash install.sh --check     # verify before installing anything
python readroid.py
```

To select APKs from the Download folder, enable storage access when prompted by Termux:

```bash
termux-setup-storage
```

Example path: `~/storage/shared/Download/app.apk`.

---

## Usage

1. Run `python readroid.py`.
2. Select the desired analysis from the menu.
3. Paste the APK path when prompted (or choose one automatically discovered in the Download folder).
4. Review reports in `reports/` and exported files in `output/` within the running project
   directory. Use option **9** to browse directories and view files.

The APK path can be absolute or relative to the current working directory. For the JADX option,
the tool uses at most four threads (default: two) to reduce memory pressure. Large APKs may still
require significant RAM and storage.

---

## Rebuilding, Alignment, and Signing (options 5, 10, 11, 12)

This workflow provides an install-ready APK without needing to memorize
`apktool`/`zipalign`/`apksigner` commands:

1. **Option 5** decodes the APK using Apktool (smali + human-readable resources).
2. Edit files inside the generated directory (`output/<app>_apktool/`) using any text editor on
   your device. For common tweaks without manual editing, use **option 10** (quick manifest edits).
3. Also in **option 10** (or directly in option 11 before compiling), you can **rename the package**
   (applicationId). This moves the `smali`/`smali_classesN` directories from the old package path
   to the new one and updates class references found in `.smali` files and the manifest. This is
   best-effort: code that constructs package names via reflection or at runtime might not be
   covered — always test the rebuilt APK before relying on it.
4. **Option 11** rebuilds (`apktool b`), aligns (`zipalign`), and signs (`apksigner`, falling back
   to `jarsigner` if apksigner is not installed) sequentially. The final APK is placed in `builds/`
   and, if storage access is granted, a copy is also sent to `Downloads/ReaDroid/`.
5. **Option 12** inspects or recreates the signing key used (automatically generated during the
   first rebuild).

Without `apksigner`, ReaDroid uses Java's built-in `jarsigner` (v1/JAR signing only). This usually
works, but apps targeting `targetSdkVersion` 24 or higher may be rejected by the package installer
on Android 7+ without a v2 signature. Install `pkg install apksigner` for full signing support.

**Important:** Only use this on your own APKs or applications you have explicit permission to modify.
Re-signing an app changes the original developer identity — the output will not replace the app
store version, and redistributing someone else's modified APK without permission may violate their
license. See `SECURITY.md`.

---

## Important Limitations

- ReaDroid performs static analysis. It does not execute the APK or monitor its runtime behavior.
- It does not bypass DRM, license verification or obfuscation.
- The native AXML parser covers what most analyses require (package, version, permissions,
  components, `<application>` flags); for manifests with unusual structures, the tool still
  attempts JADX/Apktool/aapt2 as fallbacks.
- JADX does not perfectly reconstruct all original code; identifiers may be obfuscated and
  original comments/variable names may be lost.
- URLs, domains, IPs, and permissions are leads for manual review, not definitive proof of
  malicious behavior.
- The string scanner enforces file size and item count limits per category to prevent excessive
  memory usage; the report notes in `truncated_categories` when a list might be incomplete.
- Rebuilding depends on `apktool`/`zipalign`/`apksigner` (or `jarsigner`) being installed; without
  them, each step details precisely what is missing.
- ReaDroid never modifies or signs the original APK — every rebuild generates a new file under
  `builds/`.

---

## Troubleshooting

**Option 11 fails at "Building resources with aapt2".**
The Termux `aapt2` package is sometimes linked against a newer `libprotobuf` than the installed one
and fails with `cannot locate symbol ...TcParser15MpUnknownFields` — even `aapt2 version` breaks.
This is not a ReaDroid bug: apktool 3 shells out to `aapt2` to compile resources. Fix it by
upgrading the library:

```bash
pkg upgrade -y protobuf libprotobuf
```

**The menu opens in Turkish and you expected Portuguese.**
Run `READROID_LANG=pt python readroid.py`.

**JADX reports "JAVA_HOME is not set and no 'java' command could be found".**
Usually the `jadx` wrapper not seeing `PATH`. It works in an interactive Termux session but not in
a zero-`PATH` context such as ssh or CI. Run `pkg install openjdk-21` and retry.

---

## Security and Responsible Use

Analyze only your own applications, test apps, or those you have explicit permission to inspect.
APKs are untrusted files; avoid executing them. The tool invokes JADX/Apktool/zipalign/apksigner
with separate arguments (without shell interpretation) and does not transmit APKs over the internet.
Tool outputs are saved locally. See `SECURITY.md` for specific guidelines regarding rebuilding and
signing.

---

## Testing

```bash
python -m unittest discover -s tests -v      # 36 tests
python tools/selfcheck.py                    # environment, UI and fake-APK self-check
```

Tests are language-independent: `tests/test_analyzer.py` pins Portuguese for its text assertions,
and `tests/test_i18n.py` verifies that both catalogs carry the same keys, that `{placeholder}`
names match, that no translation is empty, and that both yes/no conventions are recognized. CI runs
both languages.

When adding text:

```bash
python tools/extract_strings.py --stats   # lists literals that escaped the t() wrapper
```

---

## License

MIT. See `LICENSE`.

## Credits

ReaDroid is an original interface and automation tool that integrates optional third-party tools.
The original project is [Mcsd7/ReaDroid](https://github.com/Mcsd7/ReaDroid) — copyright
OffensiveTec. This repository is the `Memati8383` fork of it; the Turkish localization, the
`tools/` scripts and the one-command installer belong to the fork. The English translation of the
upstream documentation was contributed by
[MriBoyd](https://github.com/MriBoyd) in PR #1. JADX, Apktool, and apksigner maintain their own
projects, licenses, and terms; see the links below.

- JADX: https://github.com/skylot/jadx
- Apktool: https://github.com/iBotPeaches/Apktool
- apksigner (Termux): https://github.com/termux/termux-packages
- Termux: https://github.com/termux/termux-app