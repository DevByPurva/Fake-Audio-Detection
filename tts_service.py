import os
from datetime import datetime

import pyttsx3


def synthesize_to_wav(text: str, output_dir: str = "uploads") -> tuple[str, str]:
    """Generate a speech WAV file from the given text using pyttsx3.

    Returns (filename, full_path).
    """
    os.makedirs(output_dir, exist_ok=True)

    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("Text for TTS is empty.")

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"tts_{timestamp}.wav"
    filepath = os.path.join(output_dir, filename)

    engine = pyttsx3.init()
    try:
        engine.setProperty("rate", 180)
        engine.setProperty("volume", 1.0)
        engine.save_to_file(cleaned, filepath)
        engine.runAndWait()
    finally:
        engine.stop()

    return filename, filepath
