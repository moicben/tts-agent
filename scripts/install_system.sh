#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Veuillez exécuter en root (sudo)." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  pulseaudio pulseaudio-utils alsa-utils pavucontrol \
  ffmpeg sox \
  python3 python3-venv python3-pip python3-dev \
  portaudio19-dev \
  ca-certificates curl git

echo "[OK] Paquets système installés."

# Préparer l'environnement Python (dans le repo)
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "[OK] Environnement Python prêt. Activez-le avec: source .venv/bin/activate"

