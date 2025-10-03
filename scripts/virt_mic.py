#!/usr/bin/env python3
"""
Relais simple: micro physique -> micro virtuel (PulseAudio/PipeWire).

Pré-requis côté système (Ubuntu):
  - Charger la source pipe avant d'exécuter ce script:
      pactl load-module module-pipe-source \
        source_name=virt_mic file=/tmp/virt_mic.pcm format=s16le rate=48000 channels=1

Utilisation:
  - Lancer ce script, puis dans l'application cible choisir "virt_mic" comme micro.
  - Ctrl+C pour arrêter.
"""

import os
import time
import signal
import sys
import sounddevice as sd


FIFO_PATH = "/tmp/virt_mic.pcm"
SAMPLE_RATE_HZ = 48000
NUM_CHANNELS = 1
BLOCK_FRAMES = 1024


def open_fifo_writer(pipe_path: str) -> int:
    """Ouvre le FIFO en écriture (non bloquant), réessaie tant qu'aucun lecteur n'est présent."""
    while True:
        try:
            return os.open(pipe_path, os.O_WRONLY | os.O_NONBLOCK)
        except OSError:
            time.sleep(0.2)


def main() -> None:
    fifo_fd = open_fifo_writer(FIFO_PATH)

    def handle_sigint(_sig, _frame) -> None:
        try:
            os.close(fifo_fd)
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    with sd.RawInputStream(
        samplerate=SAMPLE_RATE_HZ,
        channels=NUM_CHANNELS,
        dtype="int16",
        blocksize=BLOCK_FRAMES,
    ) as stream:
        while True:
            data, _ = stream.read(BLOCK_FRAMES)
            try:
                os.write(fifo_fd, data)
            except BrokenPipeError:
                try:
                    os.close(fifo_fd)
                except Exception:
                    pass
                fifo_fd = open_fifo_writer(FIFO_PATH)


if __name__ == "__main__":
    main()


