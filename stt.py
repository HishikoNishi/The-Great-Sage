import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
import logging
from typing import Optional

logger = logging.getLogger("great_sage.stt")

class SpeechToText:
    """Handles audio recording and transcription using faster-whisper with adaptive energy-based auto-stop."""

    def __init__(self, model_size="base.en"):
        # Initialize Whisper model
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.sample_rate = 16000
        # Fallback threshold if calibration fails
        self.default_energy_threshold = 0.01

    def record_and_transcribe(self, max_duration: int = 10) -> Optional[str]:
        """
        Records audio using adaptive energy levels to detect end of speech.
        - Calibrates ambient noise for the first 200ms.
        - Allows up to 2s of initial silence before speech is required.
        - Stops after 1s of continuous silence after speech has been detected.
        - Caps total recording at max_duration.
        """
        logger.info("Recording with adaptive energy VAD...")

        frame_duration_ms = 30
        frame_size = int(self.sample_rate * frame_duration_ms / 1000)

        audio_buffer = []
        speech_detected = False
        silence_duration_ms = 0
        total_duration_ms = 0

        ambient_noise_samples = []
        calibration_frames = 6 # ~180ms for calibration

        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='float32') as stream:
                while total_duration_ms < max_duration * 1000:
                    data, overflowed = stream.read(frame_size)

                    # --- FIX: Remove DC Offset ---
                    # Subtracting the mean centers the waveform around 0
                    centered_data = data - np.mean(data)

                    # Calculate RMS energy on centered data
                    rms = np.sqrt(np.mean(centered_data**2))

                    # Calibration Phase
                    if total_duration_ms < (calibration_frames * frame_duration_ms):
                        ambient_noise_samples.append(rms)
                        threshold = self.default_energy_threshold
                    else:
                        avg_noise = np.mean(ambient_noise_samples) if ambient_noise_samples else 0
                        threshold = max(self.default_energy_threshold, avg_noise * 1.5)

                    if rms > threshold:
                        speech_detected = True
                        silence_duration_ms = 0
                    else:
                        if speech_detected:
                            silence_duration_ms += frame_duration_ms

                    audio_buffer.append(data) # Store raw data for Whisper
                    total_duration_ms += frame_duration_ms

                    if speech_detected and silence_duration_ms >= 1000:
                        logger.info("Silence detected. Stopping recording.")
                        break

                    if not speech_detected and total_duration_ms >= 2000:
                        logger.info("No speech detected in first 2 seconds. Stopping.")
                        return None

            if not audio_buffer:
                return None

            full_audio = np.concatenate(audio_buffer).flatten()

            segments, info = self.model.transcribe(full_audio, beam_size=5, language="en")
            text = " ".join([segment.text for segment in segments]).strip()
            return text if text else None

        except Exception as e:
            logger.error(f"Recording or transcription error: {e}")
            return None

    def close(self):
        pass

# Singleton instance
stt = SpeechToText()
