#!/usr/bin/env bash
set -euo pipefail

# À lancer dans la session utilisateur pour créer les périphériques virtuels pour la session courante
pactl load-module module-null-sink sink_name=meet_output sink_properties=device.description=MeetOutput || true
pactl load-module module-null-sink sink_name=agent_output sink_properties=device.description=AgentOutput || true
pactl load-module module-remap-source source_name=agent_mic master=agent_output.monitor source_properties=device.description=AgentMic || true

echo "[OK] Périphériques créés (session). Sinks/sources:"
pactl list short sinks || true
pactl list short sources || true

