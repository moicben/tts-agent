import argparse
import os
import sys
import multiprocessing as mp
from pathlib import Path
from typing import Tuple

import numpy as np

import agent
from tts_engine import create_coqui_synth
from stt_openai import record_until_silence, transcribe_wave


def main():
    try:
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    parser = argparse.ArgumentParser(description="Agent vocal (Whisper + GPT-4o-mini → FR TTS)")
    parser.add_argument("--device-index", type=int, default=None, help="Index du périphérique de sortie audio (fallback si SD_OUTPUT_DEVICE non défini)")
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
                import sounddevice as sd

                out_sr = int(os.getenv("OUTPUT_SAMPLE_RATE_HZ", "48000") or 48000)
                t = np.linspace(0, 0.1, int(out_sr * 0.1), False)
                tone = (0.2 * np.sin(2 * np.pi * 440 * t)).astype("float32")

                # Sélection du périphérique via env si disponible
                device_idx = _resolve_output_device_index(os.getenv("SD_OUTPUT_DEVICE", ""))
                if device_idx is None:
                    device_idx = args.device_index

                sd.play(tone, out_sr, device=device_idx)
                sd.wait()
            except Exception:
                pass

            wav_bytes = record_until_silence()
            text = transcribe_wave(wav_bytes)
            if not text:
                # réponse immédiate
                reply = "Je n'ai rien entendu. Peux-tu répéter ?"
                wav, sr = synth(reply)
                wav_48k = _to_48k_mono(wav, sr)
                import sounddevice as sd
                device_idx = _resolve_output_device_index(os.getenv("SD_OUTPUT_DEVICE", ""))
                if device_idx is None:
                    device_idx = args.device_index
                sd.play(wav_48k, 48000, device=device_idx)
                sd.wait()
                continue

            reply = agent.respond(text)
            wav, sr = synth(reply)
            wav_48k = _to_48k_mono(wav, sr)
            import sounddevice as sd
            device_idx = _resolve_output_device_index(os.getenv("SD_OUTPUT_DEVICE", ""))
            if device_idx is None:
                device_idx = args.device_index
            sd.play(wav_48k, 48000, device=device_idx)
            sd.wait()

    except KeyboardInterrupt:
        print("Au revoir !")


if __name__ == "__main__":
    main()

# --- helpers audio output ---

def _resolve_output_device_index(name_or_substr: str) -> "int | None":
    """Retourne l'index du périphérique de sortie dont le nom contient name_or_substr (insensible à la casse).
    Si vide ou introuvable, retourne None.
    """
    try:
        if not name_or_substr:
            return None
        import sounddevice as sd

        devices = sd.query_devices()
        target = name_or_substr.lower()
        for idx, dev in enumerate(devices):
            try:
                if dev.get("max_output_channels", 0) <= 0:
                    continue
                dev_name = str(dev.get("name", "")).lower()
                if target in dev_name:
                    return idx
            except Exception:
                continue
        return None
    except Exception:
        return None


def _to_48k_mono(wav: np.ndarray, sr: int) -> np.ndarray:
    """Convertit en mono float32 et rééchantillonne à 48 kHz via interpolation linéaire."""
    if wav.ndim > 1:
        wav = np.mean(wav, axis=-1)
    wav = wav.astype("float32", copy=False)
    if sr == 48000:
        return wav
    if sr <= 0 or wav.size == 0:
        return wav
    duration = wav.shape[0] / float(sr)
    new_len = max(1, int(round(duration * 48000)))
    # Interpolation linéaire simple
    x_old = np.linspace(0.0, 1.0, wav.shape[0], endpoint=False)
    x_new = np.linspace(0.0, 1.0, new_len, endpoint=False)
    wav_48k = np.interp(x_new, x_old, wav).astype("float32", copy=False)
    return wav_48k



