"""
Push-to-talk microphone recorder.
Hold SPACE to record, release to stop. Press ESC at the prompt to quit.
"""

import time
import numpy as np
import sounddevice as sd
import keyboard

SAMPLE_RATE = 16000  # Whisper expects 16kHz mono audio


def record_on_spacebar():
    """Blocks until the user holds SPACE, records while held, and returns
    the audio as a float32 numpy array. Returns None if ESC was pressed
    instead (used as the quit signal)."""
    print("\nHold SPACE to talk (ESC to quit)...")

    while True:
        if keyboard.is_pressed("esc"):
            return None
        if keyboard.is_pressed("space"):
            break
        time.sleep(0.01)

    print("Recording... (release SPACE to stop)")
    frames = []

    def callback(indata, frame_count, time_info, status):
        frames.append(indata.copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=callback):
        while keyboard.is_pressed("space"):
            time.sleep(0.01)

    print("Transcribing...")
    if not frames:
        return np.array([], dtype="float32")
    return np.concatenate(frames, axis=0).flatten()
