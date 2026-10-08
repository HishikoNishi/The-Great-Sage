import threading
import time
import logging
import os
import sys
import atexit
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

def global_exception_handler(exctype, value, traceback):
    import traceback as tb
    logger.error("[PROCESS_TRACE] UNCAUGHT EXCEPTION")
    logger.error("".join(tb.format_exception(exctype, value, traceback)))

sys.excepthook = global_exception_handler

def thread_exception_handler(args):
    import traceback as tb
    logger.error("[PROCESS_TRACE] UNCAUGHT THREAD EXCEPTION")
    logger.error(f"Thread: {args.thread.name} (ID={args.thread.ident})")
    logger.error(f"Exception: {args.exc_type.__name__}: {args.exc_value}")
    logger.error("".join(tb.format_exception(args.exc_type, args.exc_value, args.exc_traceback)))

threading.excepthook = thread_exception_handler

def on_exit():
    logger.info("[PROCESS_TRACE] atexit handler executed")

atexit.register(on_exit)

logger.info(f"[PROCESS_TRACE] main.py started, pid={os.getpid()}")
logger.info(f"[PROCESS_TRACE] main thread={threading.current_thread().name} (ID={threading.get_ident()})")

class GreatSageApp:
    def __init__(self):
        self.is_listening = False
        self.is_paused = False
        self.overlay_thread = None

        # Pending clarification state
        self.pending_candidates = None # List[str]
        self.pending_timestamp = 0

        # Initialize Tray

        self.tray = TrayManager(
            on_listen=self.trigger_listen,
            on_pause=self.toggle_pause,
            on_quit=self.quit_app,
            on_menu_click=lambda: overlay.play_ui_sfx("interfaceClick"),
        )

    def handle_failure(self, error_msg: str):
        """Consistent failure feedback: visual glitch + spoken Japanese response."""
        logger.info(f"Handling failure: {error_msg}")
        overlay.show()
        try:
            overlay.trigger_failure()
        except Exception:
            pass
        
        logger.info("[UI_TRACE] failure: before set_mode")
        overlay.set_mode('speaking')
        logger.info("[UI_TRACE] failure: after set_mode")
        
        logger.info("[UI_TRACE] failure: before set_caption")
        overlay.set_caption(error_msg)
        logger.info(f"[UI_TRACE] failure: after set_caption (text={error_msg})")
        
        # Attempt spoken feedback
        try:
            from translate import to_great_sage_japanese
            from tts import synthesize_great_sage_voice
            
            failure_text = "I was unable to complete that action."
            japanese_text = to_great_sage_japanese(failure_text)
            audio_path = synthesize_great_sage_voice(japanese_text)
            
            # Synchronize failure audio
            current_gen_id = time.time()
            logger.info(f"[UI_TRACE] failure: generated ID {current_gen_id}")
            event = overlay.register_audio_event(str(current_gen_id))
            logger.info("[UI_TRACE] failure: registered audio event")
            
            logger.info("[UI_TRACE] failure: before play_voice_line")
            overlay.play_voice_line(str(audio_path), str(current_gen_id))
            logger.info(f"[UI_TRACE] failure: play_voice_line called with ID {current_gen_id}")
            
            logger.info(f"[UI_TRACE] failure: waiting for AUDIO_ENDED id={current_gen_id}")
            completed = event.wait(timeout=30)
            
            if completed:
                logger.info(f"[UI_TRACE] failure: AUDIO_ENDED received id={current_gen_id}")
                logger.info("[UI_TRACE] failure: before hide")
                overlay.hide()
                logger.info("[UI_TRACE] failure: after hide")
            else:
                logger.error(f"[UI_TRACE] failure: audio event timeout for ID {current_gen_id}")
            
            overlay.clear_audio_event(str(current_gen_id))
            logger.info("[UI_TRACE] failure: cleared audio event")
            
        except Exception as e:
            logger.exception(f"Failure voice pipeline failed: {e}")
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
        start_total = time.time()
        self.is_listening = True
        overlay.show() # Core should appear when we start listening
        overlay.set_mode('listening')
        overlay.set_caption("Listening...")

        # Generation ID to prevent stale AUDIO_ENDED events from hiding new interactions
        current_gen_id = time.time()

        try:
            # 1. STT
            stt_start = time.time()
            text = stt.record_and_transcribe()
            stt_duration = time.time() - stt_start

            if not text:
                logger.info("No speech detected.")
                logger.info(f"[TIMING] STT recording: {stt_duration:.2f}s")
                self.reset_to_standby()
                return

            logger.info(f"User said: {text}")
            logger.info(f"[TIMING] STT recording/transcription: {stt_duration:.2f}s")

            # --- Handle Pending Clarification ---
            if self.pending_candidates:
                # Check timeout (30s)
                if time.time() - self.pending_timestamp > 30:
                    logger.info("Clarification timeout. Clearing pending state.")
                    self.pending_candidates = None
                    self.pending_timestamp = 0
                else:
                    # Try to match input against candidates only
                    from rapidfuzz import process, fuzz
                    import re

                    # Preprocess input: strip common filler words and punctuation
                    clean_text = text.lower().strip()
                    clean_text = re.sub(r'^(a\s+|the\s+)', '', clean_text)
                    clean_text = clean_text.strip('.,!? ')

                    # Lowered threshold for narrowed context (65)
                    match = process.extractOne(clean_text, self.pending_candidates, scorer=fuzz.WRatio)
                    if match and match[1] >= 65:
                        resolved_app = match[0]
                        logger.info(f"Resolved from candidates: {resolved_app}")
                        self.pending_candidates = None
                        self.pending_timestamp = 0

                        result = {
                            "type": "action",
                            "intent_id": "open_app",
                            "params": {"app_name": resolved_app}
                        }
                    else:
                        logger.info(f"Input '{clean_text}' didn't match pending candidates {self.pending_candidates}")
                        self.pending_candidates = None
                        self.pending_timestamp = 0
                        # Fall back to normal brain classification
                        overlay.set_mode('thinking')
                        overlay.set_caption("Thinking...")
                        brain_start = time.time()
                        result = brain.classify(text)
                        brain_duration = time.time() - brain_start
                        if not result:
                            self.handle_failure("I couldn't tell which one you meant.")
                            self.reset_to_standby()
                            return
            else:
                # Normal Brain Classification
                overlay.set_mode('thinking')
                overlay.set_caption("Thinking...")
                brain_start = time.time()
                result = brain.classify(text)
                brain_duration = time.time() - brain_start

            if not result:
                logger.error("Brain failed to classify request.")
                self.handle_failure("I'm having trouble thinking right now.")
                self.reset_to_standby()
                return

            # Log brain duration if it was calculated
            if 'brain_duration' in locals():
                logger.info(f"[TIMING] Brain classification: {brain_duration:.2f}s")

            # 3. Resolve & Execute
            if result.get("type") == "action":
                intent_id = result.get("intent_id")
                params = result.get("params", {})

                # Special handling for open_app to use the new resolver
                if intent_id == "open_app" or (intent_id == "open_browser" and not params.get("url")):
                    from resolver import resolver
                    query = params.get("app_name", "")
                    resolution = resolver.resolve(query)

                    if isinstance(resolution, str):
                        # Successful resolution
                        params["app_name"] = resolution
                        # Direct execution and dynamic feedback
                        ok = executor.execute("open_app", params)
                        if ok:
                            overlay.trigger_success()
                            overlay.set_mode('speaking')
                            # Dynamic confirmation voice line
                            conf_text = f"Opening {query}."
                            try:
                                from translate import to_great_sage_japanese
                                from tts import synthesize_great_sage_voice
                                jp_conf = to_great_sage_japanese(conf_text)
                                audio_path = synthesize_great_sage_voice(jp_conf)

                                overlay.set_caption(conf_text)

                                # WAIT FOR AUDIO_ENDED
                                event = overlay.register_audio_event(str(current_gen_id))
                                if hasattr(overlay, '_event_listener_thread') and overlay._event_listener_thread:
                                    logger.info(f"[AUDIO_TRACE] listener_alive={overlay._event_listener_thread.is_alive()}")
                                else:
                                    logger.info(f"[AUDIO_TRACE] listener_alive=UNKNOWN")
                                overlay.play_voice_line(str(audio_path), str(current_gen_id))
                                completed = event.wait(timeout=30)
                                if not completed:
                                    logger.error("Audio event timeout for confirmation voice.")
                                    # FAILURE PATH: hide and stop
                                    overlay.hide()
                                    overlay.clear_audio_event(str(current_gen_id))
                                    return

                                overlay.clear_audio_event(str(current_gen_id))
                                overlay.hide()
                            except Exception:
                                logger.exception("Dynamic confirmation voice pipeline failed")
                                overlay.hide()
                            return # SUCCESS: prevent fall-through to legacy logic
                        else:
                            self.handle_failure("I couldn't launch the application.")
                            self.reset_to_standby()
                            return
                    elif isinstance(resolution, (type(None))):
                        # Not found
                        self.handle_failure(f"I couldn't find an app named {query}.")
                        self.reset_to_standby()
                        return
                    else:
                        # resolution is ClarificationRequired
                        candidates = resolution.candidates
                        logger.info(f"Ambiguity detected: {candidates}")

                        # Speak clarification question
                        question_text = f"I found several matches: {', '.join(candidates)}. Please say the exact name."

                        try:
                            from translate import to_great_sage_japanese
                            from tts import synthesize_great_sage_voice
                            japanese_text = to_great_sage_japanese(question_text)
                            audio_path = synthesize_great_sage_voice(japanese_text)

                            overlay.set_caption(japanese_text)
                            overlay.play_voice_line(str(audio_path))

                            # WAIT FOR AUDIO_ENDED
                            event = overlay.register_audio_event(str(current_gen_id))
                            logger.info(f"[AUDIO_TRACE] wait begin id={str(current_gen_id)}")
                            overlay.play_voice_line(str(audio_path), str(current_gen_id))
                            completed = event.wait(timeout=30)
                            if not completed:
                                logger.error("Audio event timeout for clarification voice.")
                                overlay.hide()
                                overlay.clear_audio_event(str(current_gen_id))
                                return
                            overlay.clear_audio_event(str(current_gen_id))
                            overlay.hide()
                        except Exception as e:
                            logger.error(f"Clarification voice pipeline failed: {e}")
                            overlay.hide()

                        # Set pending state
                        self.pending_candidates = candidates
                        self.pending_timestamp = time.time()
                        self.reset_to_standby()
                        return

                # Standard Intent Resolution
                intent_cfg = registry.get_intent(intent_id)
                if intent_cfg and intent_id != "open_app":
                    action_name = intent_cfg['action']
                    action_params = intent_cfg.get('params', {})
                    action_params.update(params)

                    try:
                        action_ok = executor.execute(action_name, action_params)
                        if not action_ok:
                            self.handle_failure("That action could not be completed.")
                            self.reset_to_standby()
                            return
                    except Exception:
                        logger.exception(f"Exception during action execution for intent {intent_id}")
                        self.handle_failure("An error occurred while performing that action.")
                        self.reset_to_standby()
                        return

                    voice_file = intent_cfg.get('audio_file')
                    caption = intent_cfg.get('caption', "")

                    try:
                        overlay.trigger_success()
                    except Exception:
                        pass

                    overlay.set_mode('speaking')
                    overlay.set_caption(caption)

                    from config import get_audio_path
                    if voice_file:
                        audio_path = get_audio_path(voice_file)
                        if os.path.exists(audio_path):
                            try:
                                play_start = time.time()
                                overlay.play_voice_line(audio_path)
                                logger.info(f"[TIMING] Overlay playback trigger: {time.time() - play_start:.2f}s")

                                # WAIT FOR AUDIO_ENDED
                                event = overlay.register_audio_event(str(current_gen_id))
                                logger.info(f"[AUDIO_TRACE] wait begin id={str(current_gen_id)}")
                                overlay.play_voice_line(audio_path, str(current_gen_id))
                                completed = event.wait(timeout=30)
                                if not completed:
                                    logger.error("Audio event timeout for intent voice.")
                                    overlay.hide()
                                    overlay.clear_audio_event(str(current_gen_id))
                                    return
                                overlay.clear_audio_event(str(current_gen_id))
                                overlay.hide()
                            except Exception as e:
                                logger.error(f"Overlay playback failed: {e}, falling back to local play_audio")
                                play_audio(audio_path)
                                overlay.hide()
                        else:
                            logger.error(f"Audio file missing for intent {intent_id}: {audio_path}")
                            overlay.set_caption(f"Audio missing: {voice_file}")
                elif intent_id != "open_app":
                    logger.warning(f"Intent {intent_id} not found in registry.")
                    self.handle_failure(f"I don't know how to perform {intent_id}.")
                    self.reset_to_standby()
                    return

            elif result.get("type") == "answer":
                answer_text = result.get("text", "")

                # Defensive re-confirmation that we are still in thinking mode
                # during translation and synthesis stages.
                try:
                    overlay.set_mode('thinking')
                except Exception:
                    pass

                # IMPORTANT: Do NOT set_caption(answer_text) here to prevent English flash.
                # Only set caption AFTER translation and synthesis are ready.

                try:
                    from translate import to_great_sage_japanese
                    from tts import synthesize_great_sage_voice

                    # 1. Translation
                    trans_start = time.time()
                    japanese_text = to_great_sage_japanese(answer_text)
                    trans_duration = time.time() - trans_start
                    logger.info(f"[TIMING] Translation: {trans_duration:.2f}s")

                    # 2. Synthesis
                    tts_start = time.time()
                    audio_path = synthesize_great_sage_voice(japanese_text)
                    tts_duration = time.time() - tts_start
                    logger.info(f"[TIMING] Fish Audio TTS request: {tts_duration:.2f}s")

                    audio_path = str(audio_path)

                    # 3. Playback: Caption first, then Voice
                    overlay.set_mode('speaking')
                    overlay.set_caption(answer_text)

                    play_start = time.time()
                    overlay.play_voice_line(audio_path)
                    logger.info(f"[TIMING] Overlay playback trigger: {time.time() - play_start:.2f}s")

                    try:
                        overlay.trigger_success()
                    except Exception:
                        pass

                    # 4. WAIT FOR AUDIO_ENDED
                    audio_event = overlay.register_audio_event(str(current_gen_id))
                    overlay.play_voice_line(audio_path, str(current_gen_id))

                    completed = audio_event.wait(timeout=30)

                    if not completed:
                        logger.error("Audio playback timeout or error reported by overlay.")
                        overlay.hide()
                        overlay.clear_audio_event(str(current_gen_id))
                        # Trigger failure feedback for the user
                        self.handle_failure("I couldn't finish speaking.")
                    else:
                        overlay.clear_audio_event(str(current_gen_id))
                        overlay.hide()

                except Exception as e:
                    logger.error(f"Dynamic voice pipeline failed: {e}")
                    self.handle_failure("I couldn't synthesize a response.")

        except Exception as e:
            logger.exception(f"Error in listen loop: {e}")
            self.handle_failure("An unexpected error occurred.")

        finally:
            total_duration = time.time() - start_total
            logger.info(f"[TIMING] Total pipeline: {total_duration:.2f}s")
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

        # Start the hotkey listener and block
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
        self.tray.stop()
        os._exit(0)

    def on_overlay_ready(self):
        """Called by pywebview once the GUI loop is live and the window is ready."""
        logger.info("Overlay ready — registering hotkey.")
        self.setup_hotkey()

    def run(self):
        """Launches all components. webview.start()MUST be on the main thread."""
        logger.info("[PROCESS_TRACE] before GreatSageApp.run()")
        logger.info("Starting Great Sage Assistant...")

        # 1. Start Tray in background
        self.tray.start()

        # 2. Create overlay window (does not start the event loop yet)
        overlay.start()

        # 3. Block on main thread; on_ready runs when webview can start evaluate_js
        overlay.run(on_ready=self.on_overlay_ready)
        logger.info("[SHUTDOWN_TRACE] overlay.run() returned")
        logger.info("[PROCESS_TRACE] after GreatSageApp.run()")

    def quit_app(self):
        logger.info("Quitting Great Sage...")
        self.tray.stop()
        # Since webview.start() is blocking the main thread,
        # we use os._exit to force the process to terminate.
        # Use os._exit(0) for a clean forced exit.
        os._exit(0)

if __name__ == "__main__":
    app = GreatSageApp()
    app.run()
