import re
import os

file_path = r'D:\Project\The-Great-Sage\main.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_func = r'''    def handle_failure(self, error_msg: str):
        """Consistent failure feedback: visual glitch + spoken Japanese response."""
        logger.info(f"Handling failure: {error_msg}")
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
'''

# Regex to find the handle_failure function from its signature to the start of trigger_listen
pattern = re.compile(r'    def handle_failure\(self, error_msg: str\):.*?    def trigger_listen\(self\):', re.DOTALL)

if pattern.search(content):
    # Replace only the function part, keeping 'def trigger_listen(self):'
    updated_content = pattern.sub(new_func + '\n\n    def trigger_listen(self):', content)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    print("Successfully repaired handle_failure")
else:
    print("Could not find handle_failure function for repair")
