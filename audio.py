import logging
import os
from playsound import playsound
from threading import Thread

logger = logging.getLogger("great_sage.audio")

def play_audio(file_path: str):
    """Plays an audio file in a background thread to avoid blocking."""
    if not os.path.exists(file_path):
        logger.error(f"Audio file not found: {file_path}")
        return

    def _play():
        try:
            playsound(file_path)
        except Exception as e:
            logger.error(f"Error playing audio {file_path}: {e}")

    # Run in thread so the app doesn't freeze while audio plays
    Thread(target=_play, daemon=True).start()
