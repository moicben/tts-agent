#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "[1/5] Installation des paquets système"
sudo /usr/bin/bash "$REPO_DIR/scripts/install_system.sh"

echo "[2/5] Configuration PulseAudio (persistant)"
"$REPO_DIR/scripts/config_pulseaudio.sh"

echo "[3/5] Création périphériques PulseAudio (session)"
"$REPO_DIR/scripts/pulse_session.sh"

echo "[4/5] Déploiement service systemd user"
mkdir -p "$HOME/.config/systemd/user"
cp "$REPO_DIR/systemd/tts-agent.service" "$HOME/.config/systemd/user/"
systemctl --user daemon-reload || true

echo "[5/5] Démarrage (nécessite OPENAI_API_KEY dans l'environnement user)"
systemctl --user enable --now tts-agent.service || true

echo "Terminé. Vérifiez: systemctl --user status tts-agent.service"

