## Déploiement rapide sur Droplet (Google Meet)

### TL;DR (one-liner)

Sur un Droplet Ubuntu connecté avec votre utilisateur:

```bash
sudo bash -c 'apt-get update && apt-get install -y git && su - $SUDO_USER -c "cd ~ && test -d tts-agent || git clone <VOTRE_REPO_URL>.git tts-agent && cd tts-agent && git pull && bash scripts/bootstrap.sh"'
```

Remplacez `<VOTRE_REPO_URL>` par l’URL Git de ce repo.

### Ce que fait le bootstrap
1. Installe les paquets système (PulseAudio/ALSA, ffmpeg/sox, Python venv, etc.).
2. Crée les périphériques audio virtuels PulseAudio (persistants et pour la session).
3. Crée l’environnement Python et installe les dépendances.
4. Configure le service `systemd --user` `tts-agent.service`.
5. Démarre l’agent.

### Pré-requis
- Droplet Ubuntu 22.04+ (recommandé: 4 vCPU / 8 Go RAM)
- Variable d’environnement `OPENAI_API_KEY` définie pour l’utilisateur

### Détails

1) Installation système et Python
```bash
sudo /usr/bin/bash ~/tts-agent/scripts/install_system.sh
```

2) Config PulseAudio (persistant et session)
```bash
bash ~/tts-agent/scripts/config_pulseaudio.sh
bash ~/tts-agent/scripts/pulse_session.sh
```

3) Exporter la clé OpenAI (systemd user lit l’environnement via `systemctl --user import-environment`)
```bash
export OPENAI_API_KEY=sk-...  # à mettre dans ~/.profile ou ~/.bashrc
systemctl --user import-environment OPENAI_API_KEY
```

4) Activer le service
```bash
mkdir -p ~/.config/systemd/user
cp ~/tts-agent/systemd/tts-agent.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now tts-agent.service
```

5) Vérification audio
```bash
bash ~/tts-agent/scripts/validate_audio.sh
```

### Google Meet (navigateur géré manuellement)
- Micro: `AgentMic`
- Haut-parleur: `MeetOutput`
- AEC Meet activé; ajuster volumes via `pavucontrol` si nécessaire.

### Variables utiles (optionnelles)
- `INPUT_SAMPLE_RATE_HZ` (def: 16000)
- `OUTPUT_SAMPLE_RATE_HZ` (def: 48000)
- `SD_INPUT_DEVICE` / `PULSE_SOURCE` (sélection entrée)
- `SD_OUTPUT_DEVICE` / `PULSE_SINK` (sélection sortie)

