#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
cd /work
# The OCI image otherwise discards downloaded .deb files even on an interrupted install.
if [[ -f /etc/apt/apt.conf.d/docker-clean ]]; then
  mv /etc/apt/apt.conf.d/docker-clean /etc/apt/docker-clean.disabled
fi
apt-get -o Acquire::Retries=3 -o Acquire::http::Timeout=30 update
apt-get -o Acquire::Retries=3 -o Acquire::http::Timeout=30 install -y --no-install-recommends \
  git cmake ninja-build gperf ccache device-tree-compiler python3-dev python3-pip \
  python3-venv python3-setuptools python3-wheel xz-utils file make \
  libsdl2-2.0-0 libgcrypt20 libmagic1 libpixman-1-0 libslirp0 curl wget ca-certificates nano
python3 /manager/scripts/linux-setup.py
