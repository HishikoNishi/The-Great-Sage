import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
import logging
from typing import Optional

logger = logging.getLogger("great_sage.stt")

class SpeechToText:
    """Handles audio recording and transcription using faster-whisper with energy-based auto-stop."""

    def __init__(self, model_size="base.en"):
        # Initialize Whisper model
        # compute_type="int8" is good for CPU efficiency
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.sample_rate = 16000
        # Energy threshold for speech detection.
        # This may need tuning based on microphone sensitivity.
        self.energy_threshold = 0.01

    def record_and_transcribe(self, max_duration: int = 10) -> Optional[str]:
        """
        Records audio using energy levels to detect end of speech.
        - Allows up to 2s of initial silence before speech is required.
        - Stops after 1s of continuous silence after speech has been detected.
        - Caps total recording at max_duration.
        """
        logger.info("Recording with energy-based VAD...")

        frame_duration_ms = 30
        frame_size = int(self.sample_rate * frame_duration_ms / 1000)

        audio_buffer = []
        speech_detected = False
        silence_duration_ms = 0
        total_duration_ms = 0

        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='float32') as stream:
                while total_duration_ms < max_duration * 1000:
                    # Read one frame
                    data, overflowed = stream.read(frame_size)

                    # Calculate RMS energy: square root of the mean of squares
                    rms = np.sqrt(np.mean(data**2))

                    if rms > self.energy_threshold:
                        speech_detected = True
                        silence_duration_ms = 0
                    else:
                        if speech_detected:
                            silence_duration_ms += frame_duration_ms

                    audio_buffer.append(data)
                    total_duration_ms += frame_duration_ms

                    # Stop if we've seen speech and then 1s of silence
                    if speech_detected and silence_duration_ms >= 1000:
                        logger.info("Silence detected. Stopping recording.")
                        break

                    # Stop if no speech detected after 2s (initial timeout)
                    if not speech_detected and total_duration_ms >= 2000:
                        logger.info("No speech detected in first 2 seconds. Stopping.")
                        return None

            if not audio_buffer:
                return None

            # Convert buffer to 1D array for Whisper
            full_audio = np.concatenate(audio_buffer).flatten()

            segments, info = self.model.transcribe(full_audio, beam_size=5, language="en")
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
