#!/usr/bin/env bash
set -euo pipefail
source /work/env.sh
action=${1:?}
app=${2:?}
[[ $app =~ ^[a-zA-Z0-9_-]+$ ]] || exit 2
case "$action" in
  build)
    west build -p auto -b m5stack_fire/esp32/procpu -d "build-$app" "apps/$app" -o=-j2
    ;;
  run)
    [[ -f build-$app/zephyr/zephyr.elf ]] || { echo 'Nejprve cvičení sestavte.'; exit 1; }
    echo 'QEMU ukončíte: Ctrl+A, potom X.'
    exec ./scripts/run-qemu.sh "build-$app"
    ;;
  edit)
    exec nano --mouse "apps/$app/src/main.c"
    ;;
  *) exit 2;;
esac
