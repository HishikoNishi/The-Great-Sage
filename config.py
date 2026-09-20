import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base Directory
BASE_DIR = Path(__file__).parent.absolute()

# Ollama Config
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
TRANSLATE_MODEL = os.getenv("TRANSLATE_MODEL", "qwen2.5:3b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

# Fish Audio Config
FISH_API_KEY = os.getenv("FISH_API_KEY", "")
FISH_VOICE_ID = os.getenv("FISH_VOICE_ID", "")
FISH_MODEL = os.getenv("FISH_MODEL", "")

# Application Settings
HOTKEY = os.getenv("HOTKEY", "ctrl+alt+s")
INTENTS_FILE = BASE_DIR / os.getenv("INTENTS_FILE", "intents.yaml")
AUDIO_DIR = BASE_DIR / os.getenv("AUDIO_DIR", "voice_lines")

# Overlay Settings
OVERLAY_FILE = BASE_DIR / os.getenv("OVERLAY_FILE", "overlay/great-sage-core.html")

# Global Settings
LOG_FILE = BASE_DIR / "great_sage.log"

def get_audio_path(filename):
    """Helper to get absolute path to a voice line."""
    return str(AUDIO_DIR / filename)
