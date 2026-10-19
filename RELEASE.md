První vydání průvodce **Zephyr pro Termux** pro Android ARM64 a x86_64, bez rootu.

- Stahování GitHub Termuxu s kontrolou SHA-256 a podpisu.
- Ubuntu 24.04 v proot, Zephyr v4.4.2, ESP32 SDK, QEMU a zephyr4squirrels.
- Instalace, sestavení, spuštění, editor, terminál, stav a zálohy cvičení.
- Aktualizace prostředí i průvodce z GitHubu.
- Nativní ovládání dotykem, klávesnicí, myší a touchpadem.

Stáhněte **zephyr-termux.apk**, otevřete jej a postupujte podle kroků 1–3.
Soubor **SHA256SUMS.txt** obsahuje kontrolní součet APK.
Požadován 64bitový Android 7+, alespoň 12 GiB volného místa; doporučeno 20 GiB a 6 GiB RAM.

První systémové potvrzení instalace a oprávnění provede uživatel. Root Androidu se nepoužívá.
Přímé flashování fyzického ESP32 přes USB není v této verzi zahrnuto.
Ověřeno v Android 15 x86_64 emulátoru; fyzický ARM64 tablet zatím nebyl připojen k testování.
