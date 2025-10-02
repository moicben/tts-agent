#!/usr/bin/env bash
set -euo pipefail

# À exécuter en tant qu'UTILISATEUR (pas root), dans la session PulseAudio user.

mkdir -p "$HOME/.config/pulse"
PA_DEFAULT="$HOME/.config/pulse/default.pa"

if [[ ! -f "$PA_DEFAULT" ]]; then
  cp /etc/pulse/default.pa "$PA_DEFAULT" || true
fi

add_line() {
  local line="$1"
  grep -Fq "$line" "$PA_DEFAULT" || echo "$line" >> "$PA_DEFAULT"
}

add_line "load-module module-null-sink sink_name=meet_output sink_properties=\"device.description=MeetOutput\""
add_line "load-module module-null-sink sink_name=agent_output sink_properties=\"device.description=AgentOutput\""
add_line "load-module module-remap-source source_name=agent_mic master=agent_output.monitor source_properties=\"device.description=AgentMic\""

pulseaudio -k || true
sleep 1
pulseaudio --start

echo "[OK] PulseAudio configuré. Sinks/sources:" 
pactl list short sinks || true
pactl list short sources || true

