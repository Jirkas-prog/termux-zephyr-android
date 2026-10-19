# Externí projekty

Tento repozitář obsahuje vlastní průvodní aplikaci a instalační skripty.
Není oficiální aplikací Termuxu, Zephyr Project ani Espressifu.
Následující projekty se stahují ze svých původních zdrojů a mají vlastní licence:

- [Termux](https://github.com/termux/termux-app), GPL-3.0.
- [proot-distro](https://github.com/termux/proot-distro), GPL-3.0.
- [Zephyr RTOS](https://github.com/zephyrproject-rtos/zephyr), převážně Apache-2.0; jednotlivé moduly mají své licence.
- [Zephyr SDK](https://github.com/zephyrproject-rtos/sdk-ng), soubor komponent s vlastními licencemi.
- [Espressif QEMU](https://github.com/espressif/qemu), převážně GPL-2.0.
- [zephyr4squirrels](https://github.com/lenkakt/zephyr4squirrels), licence uvedené v původním projektu.
- [Ubuntu](https://hub.docker.com/_/ubuntu), jednotlivé distribuční balíčky mají vlastní licence.

APK Termuxu se nepřebaluje ani nepodepisuje jiným klíčem. Stahuje se přímo
z oficiálního GitHub vydání a ověřuje se jeho kontrolní součet i certifikát.
