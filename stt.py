import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
import logging
from typing import Optional

logger = logging.getLogger("great_sage.stt")

class SpeechToText:
    """Handles audio recording and transcription using faster-whisper."""

    def __init__(self, model_size="base.en"):
        # Initialize Whisper model
        # compute_type="int8" is good for CPU efficiency
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.sample_rate = 16000

    def record_and_transcribe(self, duration: int = 5) -> Optional[str]:
        """Records audio for a set duration and transcribes it."""
        logger.info(f"Recording for {duration} seconds...")

        try:
            # sounddevice records directly into a numpy array as float32 by default
            recording = sd.rec(int(duration * self.sample_rate),
                                samplerate=self.sample_rate,
                                channels=1,
                                dtype='float32')
            sd.wait()  # Wait until recording is finished

            # flatten to 1D array for Whisper
            audio_data = recording.flatten()

            segments, info = self.model.transcribe(audio_data, beam_size=5, language="en")
            text = " ".join([segment.text for segment in segments]).strip()
            return text if text else None
        except Exception as e:
            logger.error(f"Recording or transcription error: {e}")
            return None

    def close(self):
        """Clean up resources."""
        pass

# Singleton instance
stt = SpeechToText()

