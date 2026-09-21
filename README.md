# Great Sage Assistant

Analytical Engine // Core - A highly capable desktop assistant with a cold, superior persona.

## Installation & Setup

### 1. Dependencies
- **Ollama**: Install from [ollama.com](https://ollama.com).
- **Python 3.10+**: Ensure Python is installed and added to your PATH.
- **Audio Devices**: A working microphone and speaker.

### 2. Model Setup
You need to pull the following model via Ollama:
```bash
ollama pull qwen2.5:3b  # Used for classification and translation
```

## Usage

## Usage

### Launching
Run the main application:
```bash
python main.py
```

### Features
- **Hotkeys**: Trigger the assistant using the configured hotkey (default: `ctrl+alt+s`).
- **Modes**:
    - `LISTENING`: Recording audio via VAD.
    - `THINKING`: Classifying request via LLM.
    - `SPEAKING`: Playing Japanese audio with synced captions.
- **Overlay**: A futuristic visualizer that reacts to audio amplitude.

## Configuration
Edit `config.py` to customize:
- `HOTKEY`: The global trigger.
- `OLLAMA_MODEL`: The model used for brain classification and translation.
- `FISH_API_KEY` & `FISH_VOICE_ID`: Required for high-quality TTS.
