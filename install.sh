#!/usr/bin/env bash
set -euo pipefail

# Script d'installation pour Ubuntu/Debian
# - Installe les dépendances système audio et Python
# - Crée un environnement virtuel et installe requirements.txt

if command -v sudo >/dev/null 2>&1; then
  SUDO="sudo"
else
  SUDO=""
fi

echo "[1/4] Mise à jour des paquets"
$SUDO apt-get update -y

echo "[2/4] Installation des dépendances système"
$SUDO apt-get install -y \
  python3 \
  python3-venv \
  python3-pip \
  build-essential \
  portaudio19-dev \
  libsndfile1 \
  libasound2-dev \
  ffmpeg \
  git \
  curl \
  ca-certificates

echo "[3/4] Création de l'environnement virtuel (.venv)"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel

echo "[4/4] Installation des dépendances Python"
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
else
  echo "requirements.txt introuvable, installation minimale..."
  pip install openai numpy sounddevice python-dotenv TTS realtime-tts
fi

# Prépare un .env si absent (variables vides à remplir)
if [ ! -f .env ]; then
  cat > .env << 'EOF'
# Renseignez vos clés puis sourcez ce fichier si besoin
OPENAI_API_KEY=
COQUI_TOS_AGREED=1
EOF
  echo ".env créé (placeholders). Pensez à y renseigner vos clés."
fi

echo "\nInstallation terminée."
echo "- Activez l'env:  source .venv/bin/activate"
echo "- Lancez:        python3 talk_segments.py   (ou)   python3 agent.py"


