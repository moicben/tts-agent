#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Veuillez exécuter en root (sudo)." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

# Mise à jour avec tolérance aux dépôts PPA cassés (ex: deadsnakes sur certaines images)
if ! apt-get update; then
  echo "[WARN] apt-get update a échoué. Tentative de neutralisation des PPAs problématiques…"
  for f in /etc/apt/sources.list.d/*.list; do
    [[ -e "$f" ]] || continue
    if grep -qiE 'deadsnakes|launchpadcontent' "$f"; then
      echo "  - Désactivation: $f"
      sed -i 's/^deb /# deb /g' "$f" || true
    fi
  done
  # Moderniser les sources si disponible
  if command -v apt >/dev/null 2>&1; then
    apt modernize-sources || true
  fi
  apt-get update
fi
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

