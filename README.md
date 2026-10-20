# Zephyr pro Termux — Android bez rootu

Nativní průvodce pro Android: stáhne GitHub Termux, propojí jej s aplikací,
nainstaluje Ubuntu v proot a připraví Zephyr pro cvičení **zephyr4squirrels**.
Umí sestavit a spustit ESP32 v QEMU, otevřít editor/terminál, vytvořit zálohu
a stáhnout aktualizace z GitHubu. **Root, Magisk, odemknutí bootloaderu ani Docker nejsou potřeba.**

## Instalace na tabletu

1. Z [nejnovějšího vydání](https://github.com/Jirkas-prog/termux-zephyr-android/releases/latest)
   stáhněte **zephyr-termux.apk** a otevřete jej. Android může požádat o povolení instalace z daného zdroje.
2. V průvodci zvolte **1 Stáhnout Termux**. APK se bere přímo z
   [oficiálních GitHub Releases](https://github.com/termux/termux-app/releases).
   Po instalaci Termux jednou otevřete a nechte dokončit přípravu terminálu.
   Povolte oznámení a běh na pozadí, pokud se Android zeptá.
3. Vraťte se do průvodce, zvolte **2 Propojit Termux**, otevřete Termux,
   vložte zkopírovaný příkaz a potvrďte Enter. Na dotyku: dlouhé podržení → Paste.
4. Po dokončení přepněte zpět, zvolte **3 Povolit příkazy** a udělte oprávnění Androidu.
5. Zvolte **Instalovat / opravit**. Průběh se zobrazuje v dolní části průvodce.
6. Vyberte cvičení, stiskněte **Sestavit**, potom **Spustit**.

První potvrzení instalátoru a oprávnění musí provést uživatel. Aplikace je neobchází.
Po propojení se další operace spouštějí tlačítkem. Prostředí se nevytváří na PC ani v cloudu;
kompilace běží přímo v tabletu.

### Požadavky

- Android 7.0+ s **64bitovým ARM64 nebo x86_64** uživatelským prostředím.
- Doporučeno 6 GiB RAM a 20 GiB volného interního úložiště. Instalátor při první instalaci kontroluje minimum 12 GiB.
  Při pokračování přerušené instalace požaduje rezervu 1 GiB; již stažená data znovu nezapočítává do počátečního minima.
- Internet při instalaci a aktualizacích; stažení může trvat desítky minut podle zařízení a sítě.
- Pro první instalaci připojte nabíječku. V nastavení Androidu povolte Termuxu neomezené využití baterie.
- Existující Termux z F-Droidu/Google Play nelze přepsat GitHub APK s jiným podpisem.
  Průvodce tento konflikt zastaví. Před případnou ruční změnou zdroje zálohujte data.

## Co se instaluje

Verze jsou v [`environment.json`](environment.json): Zephyr **v4.4.2**, Ubuntu **24.04**,
Zephyr SDK s kompilátorem Xtensa ESP32, Espressif QEMU a připnutá revize kurzu.
ARM64 tablet používá nativní ARM64 hostitelské nástroje; ESP32 se emuluje v QEMU.
Nepoužívá se emulace celého x86 Linuxu na ARM tabletu.
Pro Android je připnuté oficiální Espressif QEMU **9.0.0 (20240606)**.
Sestavení 9.2.2 při testu v proot selhalo při inicializaci GLib; verze 9.0
úspěšně spustila Zephyr 4.4.2. SHA-256 pochází z oficiálního
[manifestu nástrojů ESP-IDF](https://github.com/espressif/esp-idf/blob/v5.3.1/tools/tools.json).
Systémové knihovny se neupravují.

Stahují se moduly pro ESP32 a příslušné kryptografické/bootovací závislosti,
nikoli HAL všech ostatních výrobců. Případné další moduly lze doplnit příkazem
`west update NAZEV_MODULU` v `/work/zephyrproject`. Výchozí sada pokrývá cvičení kurzu.
Zdroje Zephyru se stahují po adresářích; vynechává se jeho dokumentace a vlastní
testovací sada. Ukázky `samples` jsou zahrnuté. Kompletní strom lze doplnit pomocí
`git -C /work/zephyrproject/zephyr sparse-checkout disable`.
Python obsahuje závislosti pro sestavení a použité moduly. Nástroje pro testování
samotného Zephyru lze doplnit pomocí `west packages pip --install` v jeho adresáři.

PRoot emuluje oprávnění potřebná pro balíčky Ubuntu. Uvnitř můžete vidět uživatele `root`,
ale jde o virtuální identitu: procesy mají stále běžné oprávnění aplikace Termux v Androidu.
Průvodce nežádá `su`, správce zařízení, služby přístupnosti ani oprávnění k celému úložišti.

Po instalaci se skutečně sestaví `hello_world` pro `m5stack_fire/esp32/procpu`
a zkontroluje text `Hello, squirrels! Zephyr is alive.` v ESP32 emulátoru.
Teprve po tomto testu se prostředí označí jako nainstalované.
Test používá původní zdroj z připnutého commitu v samostatné složce
`~/zephyr-work/validation/`. Rozpracované cvičení ani jeho build se při opravě nemění;
vlastní verzi příkladu sestavíte tlačítkem **Sestavit**.

## Ovládání

| Vstup | Ovládání |
|---|---|
| Dotyk | Tlačítka alespoň 48 dp, posun prstem, výběr textu v logu |
| Klávesnice | Tab / Shift+Tab, šipky, Enter / mezerník, viditelné zvýraznění fokusu |
| Zkratky průvodce | Ctrl+B sestavit, Ctrl+R spustit, Ctrl+L obnovit stav, F1 nápověda |
| Myš | Kliknutí, kolečko, standardní výběrové nabídky Androidu |
| Touchpad | Kliknutí a systémový dvouprstý posun, stejné akce jako myš |
| Terminál | Standardní ovládání Termuxu, jeho dotyková klávesnice a extra řádek kláves |
| QEMU | Ctrl+A, potom X ukončí emulaci |
| nano | Ctrl+O uloží, Ctrl+X zavře |

Editor nano se spouští se zapnutou podporou myši. Na dotykové klávesnici Termuxu
použijte jeho přídavné klávesy Ctrl/Alt/Tab; pro emulátor stačí Ctrl+A a následně X.

Průvodce podporuje tablet na šířku, telefon na výšku, změnu velikosti okna,
systémovou velikost písma a běžné popisky pro TalkBack. Konkrétní gesta touchpadu
závisejí na ovladači Androidu; aplikace používá standardní události posunu.

## Soubory a práce v terminálu

V Termuxu:

```text
~/termux-zephyr-android/       správce z tohoto repozitáře
~/zephyr-work/                nástroje a pracovní data
~/zephyr-work/zephyr4squirrels/ vaše cvičení a jejich Git větev moje-cviceni
~/zephyr-backups/             datované archivy cvičení
~/.local/state/zephyr-android/ stav a poslední log
```

Ubuntu se jmenuje `zephyr-ops`. Pracovní složka je do něj připojena jako `/work`.
V Termuxu lze použít i příkazy:

```sh
zephyrctl install
zephyrctl status
zephyrctl build --app hello_world
zephyrctl run --app hello_world
zephyrctl edit --app hello_world
zephyrctl shell
zephyrctl backup
zephyrctl check-updates
zephyrctl update
```

V linuxovém terminálu je aktivní Python venv a Zephyr SDK. Vlastní west příkazy
můžete spouštět obvyklým způsobem. Build má omezení na dvě souběžné úlohy.
Terminál ukončíte příkazem `exit` nebo Ctrl+D. Do jeho uzavření správce blokuje
další souběžné operace, aby se neměnily soubory pod běžícím prostředím.

## Aktualizace a zálohy

- **Stáhnout Termux** nabízí nejnovější stabilní GitHub APK pro architekturu zařízení.
  Ověřuje oficiální SHA-256, název balíčku a známý certifikát Termuxu.
- **Aktualizovat průvodce** stáhne vlastní APK z Releases. Ověřuje SHA-256 a shodu
  podpisu s právě nainstalovanou aplikací. Instalaci potvrdí systém Android.
- **Aktualizovat prostředí** nejprve zálohuje cvičení, stáhne nejnovější vydaný tag
  tohoto správce a aplikuje jím připnuté verze. Nenásleduje pohyblivou vývojovou větev Zephyru.
- Změněné repozitáře se nepřepisují pomocí `reset --hard`. Vlastní úpravy správce či modulů
  aktualizaci zastaví; chráněné jsou i vlastní commity správce a Zephyru.
  Větev cvičení se posouvá jen pomocí `--ff-only`. Oprava stejné verze kurzu zachová
  rozpracované úpravy i vlastní commity. Jiný origin repozitáře se automaticky nepoužije.
  Starší vydání správce se automaticky neinstaluje.
- Záloha obsahuje cvičení i jejich `.git`, bez přeložených buildů, Ubuntu a SDK.
  Je místní: pro ochranu před ztrátou tabletu ji přeneste mimo zařízení.

Obnova do **nové prázdné složky**, bez přepsání práce:

```sh
mkdir -p ~/obnovena-cviceni
tar -xzf ~/zephyr-backups/cviceni-DATUM-CAS.tar.gz -C ~/obnovena-cviceni
```

Při přesunu mezi ARM64 a x86_64 nainstalujte nástroje znovu a přeneste cvičení;
binární SDK a Ubuntu nejsou mezi architekturami zaměnitelné.

## Řešení potíží

- **Přerušená instalace / nedostatek paměti:** vraťte se k `Instalovat / opravit`.
  Hotová stažení a pracovní data zůstávají zachována. Android může ukončit procesy na pozadí;
  nechte Termux otevřený a zkontrolujte jeho nastavení baterie.
- **Příkazy nejsou povoleny:** zopakujte krok 2, potom zkontrolujte oprávnění
  „Spouštět příkazy v prostředí Termux“ u průvodce. Propojení používá oficiální
  [RUN_COMMAND rozhraní](https://github.com/termux/termux-app/wiki/RUN_COMMAND-Intent).
- **GitHub HTTP 403/429:** vyčkejte na obnovení limitu veřejného GitHub API.
  Průvodce nepotřebuje účet ani token.
- **Chyba certifikátu / SHA-256:** soubor se nenainstaluje. Zkontrolujte oficiální zdroj a zkuste nové stažení.
- **Konflikt vlastních změn:** nejprve je commitněte nebo zálohujte. Správce automaticky nemaže práci.
- **Pomalé zrcadlo Termuxu:** v Termuxu spusťte `termux-change-repo` a vyberte jiné oficiálně nabízené zrcadlo.

Tato verze používá ESP32 emulaci. Přímé flashování fyzické desky přes USB není součástí
tohoto instalačního postupu. QEMU nemusí emulovat všechny periferie skutečné desky.

## Soukromí a sestavení

Žádné účty, reklamy, analytika ani odesílání cvičení. Síť se používá pro GitHub,
repozitáře Termuxu/Ubuntu, Docker Hub a Python balíčky. Logy zůstávají v zařízení.
Podpisové klíče, tokeny, APK, osobní nastavení a lokální cesty nepatří do zdrojového repozitáře.

Sestavení na Linuxu nebo WSL vyžaduje JDK 21, Python 3 a Android SDK 35:

```sh
export ANDROID_HOME=/cesta/k/android-sdk
sdkmanager 'platforms;android-35' 'build-tools;35.0.0'
python3 -m unittest discover -s tests -v
python3 tools/build.py
```

Výsledek: `dist/zephyr-termux.apk` a `dist/SHA256SUMS.txt`. Bez nastavení klíče jde
o vývojový podpis; takový APK nenainstalujete přes vydání podepsané produkčním klíčem.
Release sestavení: `KEYSTORE_PATH`, `KEYSTORE_PASSWORD`, volitelně `KEY_ALIAS=zephyr`.
Klíč držte mimo repozitář. GitHub Actions používá šifrovaná repository secrets
`SIGNING_KEY_BASE64` a `KEYSTORE_PASSWORD`; při tagu `vX.Y.Z` vydá podepsaný APK.
Číslo tagu musí odpovídat `environment.json`. Při nové verzi zvyšte také `version_code`.

Na připojeném testovacím Androidu lze spustit skutečné vstupní testy:

```sh
ANDROID_SERIAL=emulator-5580 python3 tools/test-android.py
```

Testy ověřují běžné UID aplikace, velikost dotykových prvků, Tab/Enter, dotyk,
události kolečka myši/touchpadu, nápovědu a zachování výběru při změně rozložení.
Pro test pomalých odpovědí musí být Termux propojený a povolené spouštění příkazů.
Testují se také dokončení callbacku a zachování chyb operací mezi obnovami stavu.
Nevyžadují root. Python testy používají Linux/WSL a Python 3.12+.
Průvodce byl ověřen na Androidu 15 (API 35), x86_64, v emulátoru na výšku i na šířku.
Fyzický ARM64 tablet nebyl při vývoji připojen; jeho ovladače vstupu a řízení běhu
na pozadí zatím nejsou ověřené. Instalační skripty vybírají ARM64 nástroje podle zařízení.
Externí komponenty a licence: [NOTICE.md](NOTICE.md).
