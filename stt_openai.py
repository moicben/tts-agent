import io
import time
import wave
import queue
import tempfile
from typing import Optional

import numpy as np
import sounddevice as sd
from openai import OpenAI
import openai


def _float_to_int16(samples: np.ndarray) -> np.ndarray:
    samples = np.clip(samples, -1.0, 1.0)
    return (samples * 32767.0).astype(np.int16)


def _write_wav_bytes(samples: np.ndarray, sample_rate_hz: int) -> bytes:
    pcm16 = _float_to_int16(samples)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate_hz)
        wf.writeframes(pcm16.tobytes())
    return buf.getvalue()


def record_until_silence(
    sample_rate_hz: int = 16000,
    threshold_rms: float = 0.010,
    min_speech_ms: int = 800,
    silence_ms: int = 1800,
    max_record_ms: int = 15000,
    min_duration_s: float = 2.0,
) -> bytes:
    """Capture micro jusqu'à silence et retourne un WAV (bytes) mono 16k.

    Heuristique simple: démarre quand le niveau RMS dépasse le seuil,
    s'arrête après un certain temps de silence.
    """
    channels = 1
    block_size = 1024
    started = False
    below_count = 0
    above_count = 0
    buf = []

    silence_blocks = max(1, int((silence_ms / 1000) * sample_rate_hz / block_size))
    min_speech_blocks = max(1, int((min_speech_ms / 1000) * sample_rate_hz / block_size))
    max_blocks = max(1, int((max_record_ms / 1000) * sample_rate_hz / block_size))
    min_blocks = max(1, int((min_duration_s) * sample_rate_hz / block_size))

    q: "queue.Queue[np.ndarray]" = queue.Queue()

    def cb(indata, frames, time_info, status):
        if status:
            # print(status)
            pass
        mono = indata[:, 0] if indata.ndim == 2 else indata
        q.put_nowait(mono.copy())

    with sd.InputStream(
        samplerate=sample_rate_hz,
        channels=channels,
        dtype="float32",
        blocksize=block_size,
        callback=cb,
    ):
        blocks_seen = 0
        start_time = time.time()
        while blocks_seen < max_blocks:
            try:
                block = q.get(timeout=1.0)
            except queue.Empty:
                continue
            blocks_seen += 1
            rms = float(np.sqrt(np.mean(np.square(block)))) if block.size else 0.0
            if not started:
                if rms >= threshold_rms:
                    above_count += 1
                else:
                    above_count = 0
                if above_count >= min_speech_blocks:
                    started = True
                    buf.append(block)
            else:
                buf.append(block)
                if rms < threshold_rms:
                    below_count += 1
                else:
                    below_count = 0
                total_blocks = len(buf)
                if below_count >= silence_blocks and total_blocks >= min_blocks:
                    break

    if not buf:
        return _write_wav_bytes(np.zeros((0,), dtype=np.float32), sample_rate_hz)

    audio = np.concatenate(buf, axis=0).astype(np.float32, copy=False)
    return _write_wav_bytes(audio, sample_rate_hz)


def transcribe_wave(wav_bytes: bytes, client: Optional[OpenAI] = None) -> str:
    """Envoie un WAV mono 16k à OpenAI Whisper et retourne le texte.

    Garde-fous:
    - Si l'audio est trop court (< ~0.1s), ne pas appeler l'API et retourner "".
    - Intercepte l'erreur BadRequestError (audio trop court) et retourne "".
    """
    # 0.1s à 16kHz mono int16 ≈ 3200 octets de données PCM + ~44 octets d'entête WAV
    MIN_WAV_BYTES_FOR_100MS = 3500
    if not wav_bytes or len(wav_bytes) < MIN_WAV_BYTES_FOR_100MS:
        return ""

    client = client or OpenAI()
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            tmp.write(wav_bytes)
            tmp.flush()
            tmp.seek(0)
            with open(tmp.name, "rb") as f:
                tr = client.audio.transcriptions.create(model="whisper-1", file=f)
        text = (tr.text or "").strip()
        return text
    except openai.BadRequestError as e:  # p.ex. audio_too_short
        # Optionnel: afficher une info de debug non bloquante
        print("[STT] Requête ignorée (audio trop court).")
        return ""


