#!/usr/bin/env bash
set -euo pipefail

echo "=== Périphériques PulseAudio (sinks) ==="
pactl list short sinks || true
echo
echo "=== Périphériques PulseAudio (sources) ==="
pactl list short sources || true
echo
echo "=== Test lecture 440 Hz via ffplay (agent_output) ==="
if command -v ffplay >/dev/null 2>&1; then
  ffplay -hide_banner -loglevel error -nodisp -autoexit \
    -f lavfi -i "sine=frequency=440:duration=1" -af aresample=48000,pan=mono|c0=c0 || true
else
  echo "ffplay introuvable (installez ffmpeg)."
fi

echo "=== Rappel: Dans Google Meet ==="
echo "Micro: AgentMic | Haut-parleur: MeetOutput"

