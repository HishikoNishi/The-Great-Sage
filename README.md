# Great Sage Desktop Assistant

The **Great Sage** is a Python-based background assistant that lives in your system tray. It listens to your voice commands, uses a local Ollama model for intent classification, and executes system actions with reactive visual feedback via a borderless HTML overlay.

## 🚀 Setup

### 1. Prerequisites
- **Python 3.11+**
- **Ollama**: Install from [ollama.com](https://ollama.com).
- **Model**: Pull the classification model:
  ```bash
  ollama pull qwen3:4b
  ```
- **Microphone**: Ensure a working microphone is connected.

### 2. Installation
1. Clone this repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```
4. (Optional) Edit `.env` to change the hotkey or Ollama host.

### 3. Running the App
```bash
python main.py
```

## 🛠 How it Works

### The Pipeline
1. **Trigger**: Press the hotkey (default `Ctrl+Alt+S`) or use the tray menu "Listen now".
2. **STT**: `faster-whisper` transcribes your English speech locally.
3. **Brain**: The text is sent to `qwen3:4b` via Ollama, which returns a JSON intent (e.g., `open_vscode`).
4. **Execution**: The app looks up the intent in `intents.yaml` and executes the mapped `pyautogui` or `os` command.
5. **Feedback**: The `pywebview` overlay switches to `SPEAKING` mode, plays the matched `.mp3` from `voice_lines/`, and displays a caption. The visual core reacts to the audio amplitude of the voice line.

### Adding New Intents
To add a new command:
1. Add a new entry to `intents.yaml`:
   ```yaml
   my_new_command:
     action: "open_app"
     params: { "app_name": "notepad" }
     audio_file: "my_voice_line.mp3"
     caption: "Opening Notepad for you."
   ```
2. Place the corresponding `my_voice_line.mp3` in the `voice_lines/` folder.
3. Update the `SYSTEM_PROMPT` in `brain.py` to include the new `intent_id` so the LLM knows it exists.

## 🎨 Visual Integration
The visual core is an HTML/JS canvas animation located in `overlay/great-sage-core.html`.
- **Python $\rightarrow$ JS**: Python uses `window.evaluate_js()` to call `setMode()`, `setCaption()`, and `playVoiceLine()`.
- **Audio Reactivity**: The `playVoiceLine` function routes the audio through an `AnalyserNode`, allowing the canvas animation to pulse in sync with the pre-recorded voice lines.
