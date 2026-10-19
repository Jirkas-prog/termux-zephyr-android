#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
[[ ${PREFIX:-} == /data/data/com.termux/files/usr ]] || { echo 'Spustte tento skript uvnitr Termuxu.'; exit 1; }
case $(uname -m) in aarch64|x86_64) ;; *) echo 'Je potreba 64bitovy Android (arm64 nebo x86_64).'; exit 1;; esac
apt-get update
# GitHub APK contains an older bootstrap. Upgrade libraries together before curl/git.
apt-get upgrade -y --with-new-pkgs --no-install-recommends -o Dpkg::Options::=--force-confold
apt-get install -y --no-install-recommends git python proot-distro curl termux-tools util-linux
mkdir -p "$HOME/.termux"
properties="$HOME/.termux/termux.properties"
touch "$properties"
if ! grep -Eq '^allow-external-apps\s*=\s*true\s*$' "$properties"; then
  sed -i '/^[[:space:]]*allow-external-apps[[:space:]]*=/d' "$properties"
  printf '\nallow-external-apps=true\n' >> "$properties"
fi
termux-reload-settings
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
printf '#!%s/bin/bash\nexec %q %q "$@"\n' "$PREFIX" "$PREFIX/bin/python" "$repo/scripts/zephyrctl.py" > "$PREFIX/bin/zephyrctl"
chmod 755 "$PREFIX/bin/zephyrctl"
echo 'Termux je propojen. V aplikaci povolte Spousteni prikazu v Termuxu a zvolte Instalovat.'
if [[ ${1:-} == --install ]]; then exec python "$repo/scripts/zephyrctl.py" install; fi
