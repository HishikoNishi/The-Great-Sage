import requests
import logging
import tempfile
from pathlib import Path
from config import FISH_API_KEY, FISH_VOICE_ID, FISH_MODEL

logger = logging.getLogger("great_sage.tts")

def synthesize_great_sage_voice(japanese_text: str) -> Path:
    """
    Sends Japanese text to Fish Audio TTS API and saves the result to a temp mp3 file.
    Follows official Fish Audio request structure.
    Returns the Path to the temp file.
    """
    if not FISH_API_KEY or not FISH_VOICE_ID:
        raise ValueError("FISH_API_KEY or FISH_VOICE_ID not configured in environment")

    # Official request structure
    response = requests.post(
        "https://api.fish.audio/v1/tts",
        headers={
            "Authorization": f"Bearer {FISH_API_KEY}",
            "Content-Type": "application/json",
            "model": FISH_MODEL,
        },
        json={
            "text": japanese_text,
            "reference_id": FISH_VOICE_ID,
            "format": "mp3",
        },
    )

    # Error handling: check for 200 OK
    if response.status_code != 200:
        try:
            error_msg = response.json().get("message", response.text)
        except:
            error_msg = response.text

        logger.error(f"Fish Audio API Error ({response.status_code}): {error_msg}")
        raise Exception(f"Fish Audio API error {response.status_code}: {error_msg}")

    # Use a temporary file that persists after closing (delete=False)
    temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    try:
        with open(temp_file.name, "wb") as f:
            f.write(response.content)
        return Path(temp_file.name)
    except Exception as e:
        logger.error(f"Failed to write TTS audio to disk: {e}")
        try:
            Path(temp_file.name).unlink(missing_ok=True)
        except:
            pass
        raise
