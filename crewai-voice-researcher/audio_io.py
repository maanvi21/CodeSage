"""
Push-to-talk audio capture + local transcription with faster-whisper.
Same approach as the original voice-assistant: record while a key is held,
then transcribe the buffered audio locally (no audio ever leaves the machine
for transcription — only the resulting text goes to Groq/Tavily/CrewAI).
"""

import queue
import tempfile
import os
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as write_wav
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
CHANNELS = 1

# "base.en" is a good speed/accuracy tradeoff for push-to-talk questions.
# Swap for "small.en" or "medium.en" if you want more accuracy and have the CPU/GPU for it.
_model = WhisperModel("base.en", device="cpu", compute_type="int8")


def record_while_held(is_key_held) -> str:
    """
    Records audio from the default mic as long as `is_key_held()` returns True.
    Returns the path to a temp WAV file containing the recording.
    """
    q: "queue.Queue[np.ndarray]" = queue.Queue()

    def callback(indata, frames, time_info, status):
        q.put(indata.copy())

    frames = []
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=callback):
        while is_key_held():
            try:
                frames.append(q.get(timeout=0.1))
            except queue.Empty:
                continue

    if not frames:
        return ""

    audio = np.concatenate(frames, axis=0)
    tmp_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    write_wav(tmp_path, SAMPLE_RATE, audio)
    return tmp_path


def transcribe(wav_path: str) -> str:
    """Transcribes a WAV file to text using faster-whisper. Cleans up the temp file after."""
    if not wav_path or not os.path.exists(wav_path):
        return ""
    try:
        segments, _ = _model.transcribe(wav_path, language="en")
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return text
    finally:
        try:
            os.remove(wav_path)
        except OSError:
            pass
