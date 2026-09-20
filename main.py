import threading
import time
import logging
import os
from pynput import keyboard
from config import HOTKEY, LOG_FILE
from stt import stt
from brain import brain
from intents import registry
from actions import executor
from overlay import overlay
from tray import TrayManager
from audio import play_audio

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("great_sage.main")

class GreatSageApp:
    def __init__(self):
        self.is_listening = False
        self.is_paused = False
        self.overlay_thread = None

        # Initialize Tray
        self.tray = TrayManager(
            on_listen=self.trigger_listen,
            on_pause=self.toggle_pause,
            on_quit=self.quit_app
        )

    def trigger_listen(self):
        """Triggered by hotkey or tray menu."""
        if self.is_paused:
            logger.info("Assistant is paused. Ignoring trigger.")
            return

        if not self.is_listening:
            # Start listening in a separate thread to avoid blocking the trigger
            threading.Thread(target=self.listen_loop, daemon=True).start()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        state = "Paused" if self.is_paused else "Active"
        logger.info(f"Assistant state changed to: {state}")
        overlay.set_caption(f"Assistant {state}")

    def listen_loop(self):
        """The core pipeline: STT -> Brain -> Action -> Feedback."""
        self.is_listening = True
        overlay.set_mode('listening')
        overlay.set_caption("Listening...")

        try:
            # 1. STT
            text = stt.record_and_transcribe()
            if not text:
                logger.info("No speech detected.")
                self.reset_to_standby()
                return

            logger.info(f"User said: {text}")
            overlay.set_mode('thinking')
            overlay.set_caption("Thinking...")

            # 2. Brain (Ollama)
            result = brain.classify(text)
            if not result:
                logger.error("Brain failed to classify request.")
                overlay.set_caption("I'm having trouble thinking right now.")
                self.reset_to_standby()
                return

            # 3. Resolve & Execute
            if result.get("type") == "action":
                intent_id = result.get("intent_id")
                params = result.get("params", {})

                intent_cfg = registry.get_intent(intent_id)
                if intent_cfg:
                    # Execute action
                    action_name = intent_cfg['action']
                    action_params = intent_cfg.get('params', {})
                    # Merge dynamic params from LLM if any
                    action_params.update(params)

                    executor.execute(action_name, action_params)

                    # Feedback: Audio & Visuals
                    voice_file = intent_cfg.get('audio_file')
                    caption = intent_cfg.get('caption', "")

                    overlay.set_mode('speaking')
                    overlay.set_caption(caption)

                    from config import get_audio_path
                    if voice_file:
                        audio_path = get_audio_path(voice_file)
                        if os.path.exists(audio_path):
                            try:
                                # Trigger overlay for visualizer and caption
                                # This now handles the actual playback via the JS <audio> element
                                overlay.play_voice_line(audio_path)
                            except Exception as e:
                                logger.error(f"Overlay playback failed: {e}, falling back to local play_audio")
                                play_audio(audio_path)
                        else:
                            logger.error(f"Audio file missing for intent {intent_id}: {audio_path}")
                            overlay.set_caption(f"Audio missing: {voice_file}")
                else:
                    logger.warning(f"Intent {intent_id} not found in registry.")
                    overlay.set_caption(f"I don't know how to perform {intent_id}.")

            elif result.get("type") == "answer":
                answer_text = result.get("text", "")
                overlay.set_mode('speaking')
                overlay.set_caption(answer_text)

                try:
                    from translate import to_great_sage_japanese
                    from tts import synthesize_great_sage_voice

                    # 1. Translate English answer to Sage-style Japanese
                    japanese_text = to_great_sage_japanese(answer_text)

                    # 2. Synthesize Japanese text to audio
                    audio_path = synthesize_great_sage_voice(japanese_text)

                    # Log verification: path and size
                    file_size = os.path.getsize(audio_path)
                    logger.info(f"TTS synthesized successfully: {audio_path} ({file_size} bytes)")

                    # 3. Play audio via existing overlay mechanism
                    overlay.play_voice_line(str(audio_path))

                    # Cleanup: we can't delete immediately as playback is async in JS,
                    # but for now we let the OS handle temp files or cleanup in next run.
                    # In a production version, we'd track these files for deletion.

                except Exception as e:
                    logger.error(f"Dynamic voice pipeline failed: {e}")
                    # Fallback: caption is already set, just sleep
                    time.sleep(3)

                # Ensure user has time to read if audio was short or failed
                time.sleep(3)

        except Exception as e:
            logger.exception(f"Error in listen loop: {e}")
            overlay.set_caption("An unexpected error occurred.")

        finally:
            self.reset_to_standby()

    def reset_to_standby(self):
        time.sleep(2)
        overlay.set_mode('standby')
        overlay.set_caption("")
        self.is_listening = False

    def setup_hotkey(self):
        """Sets up the global hotkey trigger."""
        # Convert 'ctrl+alt+s' to pynput format: '<ctrl>+<alt>+s'
        # pynput's GlobalHotKeys expects keys as strings. Special keys are wrapped in <>.
        special_keys = {'ctrl', 'alt', 'shift', 'win', 'cmd'}

        parts = HOTKEY.split('+')
        formatted_parts = []
        for p in parts:
            p = p.strip().lower()
            if p in special_keys:
                formatted_parts.append(f"<{p}>")
            else:
                formatted_parts.append(p)

        hotkey_string = "+".join(formatted_parts)
        logger.info(f"Registering hotkey: {hotkey_string}")

        # Start the hotkey listener in a background thread
        def run_listener():
            with keyboard.GlobalHotKeys({
                hotkey_string: self.trigger_listen
            }) as h:
                h.join()

        listener_thread = threading.Thread(target=run_listener, daemon=True)
        listener_thread.start()


    def quit_app(self):
        logger.info("Quitting Great Sage...")
        self.tray.stop()
        os._exit(0)

    def run(self):
        """Launches all components. webview.start() MUST be on the main thread."""
        logger.info("Starting Great Sage Assistant...")

        # 1. Start Tray in background thread
        self.tray.start()

        # 2. Start Hotkey listener in background thread
        self.setup_hotkey()

        # 3. Initialize Overlay
        overlay.start()

        # 4. Launch webview.start() on the main thread (Blocking call)
        # This is required by pywebview
        overlay.run()

    def quit_app(self):
        logger.info("Quitting Great Sage...")
        self.tray.stop()
        # Since webview.start() is blocking the main thread,
        # we use os._exit to force the whole process to terminate.
        os._exit(0)

if __name__ == "__main__":
    app = GreatSageApp()
    app.run()
