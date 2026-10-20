Opravné vydání **1.0.2** — Android bez rootu.

- Oprava instalace ověřuje původní příklad v samostatné složce. Nedokončený nebo změněný studentský `hello_world` už nezpůsobí falešné selhání instalace.
- Aktualizace chrání i vlastní commity správce a Zephyru, kontroluje origin a odmítá návrat správce na starší vydání.
- Otočení displeje zachová vybrané cvičení. Pomalá odpověď Termuxu se neruší každých pět sekund a úspěšná obnova stavu nesmaže chybu operace.
- Stahování APK se při obnovení aktivity nespustí souběžně podruhé. Dokončený soubor se po návratu nabídne k instalaci.
- Neúspěšná záloha po sobě nenechává neúplný archiv. Záznam dokončené instalace se zapisuje atomicky.
- Regresní testy ochrany dat, záloh a Android rozhraní.

Stáhněte **zephyr-termux.apk**. Stávající instalaci aktualizujte přes Android instalátor
a v průvodci zvolte **Aktualizovat prostředí**, aby se opravily také skripty v Termuxu.
Pro novou instalaci postupujte podle kroků 1–3 v aplikaci.
Soubor **SHA256SUMS.txt** obsahuje kontrolní součet APK.
Požadován 64bitový Android 7+, alespoň 12 GiB volného místa; doporučeno 20 GiB a 6 GiB RAM.

První systémové potvrzení instalace a oprávnění provede uživatel. Root Androidu se nepoužívá.
Přímé flashování fyzického ESP32 přes USB není v této verzi zahrnuto.
Ověřeno v Android 15 x86_64 emulátoru; fyzický ARM64 tablet zatím nebyl připojen k testování.
