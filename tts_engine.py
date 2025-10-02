from typing import Optional, Callable, Tuple
import numpy as np
from TTS.api import TTS


def create_coqui_synth(
    model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2",
    language: str = "fr",
) -> Callable[[str], Tuple[np.ndarray, int]]:
    """Retourne une fonction de synthèse Coqui XTTS v2 → (waveform, sample_rate)."""
    tts = TTS(model_name)

    def synthesize(text: str) -> Tuple[np.ndarray, int]:
        wav = tts.tts(text=text, language=language)
        sr = getattr(getattr(tts, "synthesizer", None), "output_sample_rate", 24000)
        return np.array(wav, dtype=np.float32), int(sr)

    return synthesize


