import argparse
import os
import sys
import multiprocessing as mp
from pathlib import Path

import agent
from tts_engine import create_coqui_synth
from stt_openai import record_until_silence, transcribe_wave


def main():
    try:
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    parser = argparse.ArgumentParser(description="Agent vocal (Whisper + GPT-4o-mini → FR TTS)")
    parser.add_argument("--device-index", type=int, default=None, help="Index du périphérique de sortie audio")
    args = parser.parse_args()

    # Charger .env si présent (sans rendre python-dotenv obligatoire)
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).resolve().parent / ".env"
        load_dotenv(dotenv_path=env_path, override=False)
    except Exception:
        pass

    # Accepter les TOS Coqui XTTS v2 si non défini (CPML)
    os.environ.setdefault("COQUI_TOS_AGREED", "1")

    if not os.getenv("OPENAI_API_KEY"):
        print("Erreur: OPENAI_API_KEY n'est pas défini dans l'environnement.")
        sys.exit(1)

    synth = create_coqui_synth()
    print("Parlez après le bip. Pausez pour terminer la tournure. Ctrl+C pour quitter.")

    try:
        while True:
            # Petit bip (440 Hz) pour indiquer l'écoute
            try:
                import numpy as np
                import sounddevice as sd
                fs = 44100
                t = np.linspace(0, 0.1, int(fs * 0.1), False)
                tone = (0.2 * np.sin(2 * np.pi * 440 * t)).astype("float32")
                sd.play(tone, fs)
                sd.wait()
            except Exception:
                pass

            wav_bytes = record_until_silence()
            text = transcribe_wave(wav_bytes)
            if not text:
                # réponse immédiate
                reply = "Je n'ai rien entendu. Peux-tu répéter ?"
                wav, sr = synth(reply)
                import sounddevice as sd
                sd.play(wav, sr, device=args.device_index)
                sd.wait()
                continue

            reply = agent.respond(text)
            wav, sr = synth(reply)
            import sounddevice as sd
            sd.play(wav, sr, device=args.device_index)
            sd.wait()

    except KeyboardInterrupt:
        print("Au revoir !")


if __name__ == "__main__":
    main()


