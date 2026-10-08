import os
import re

file_path = 'main.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# The replacement content for handle_failure
replacement_content = [
    "    def handle_failure(self, error_msg: str):\n",
    "        \"\"\"Consistent failure feedback: visual glitch + spoken Japanese response.\"\"\"\n",
    "        logger.info(f\"Handling failure: {error_msg}\")\n",
    "        try:\n",
    "            overlay.trigger_failure()\n",
    "        except Exception:\n",
    "            pass\n",
    "        \n",
    "        logger.info(\"[UI_TRACE] failure: before set_mode\")\n",
    "        overlay.set_mode('speaking')\n",
    "        logger.info(\"[UI_TRACE] failure: after set_mode\")\n",
    "        \n",
    "        logger.info(\"[UI_TRACE] failure: before set_caption\")\n",
    "        overlay.set_caption(error_msg)\n",
    "        logger.info(f\"[UI_TRACE] failure: after set_caption (text={error_msg})\")\n",
    "        \n",
    "        # Attempt spoken feedback\n",
    "        try:\n",
    "            from translate import to_great_sage_japanese\n",
    "            from tts import synthesize_great_sage_voice\n",
    "            \n",
    "            failure_text = \"I was unable to complete that action.\"\n",
    "            japanese_text = to_great_sage_japanese(failure_text)\n",
    "            audio_path = synthesize_great_sage_voice(japanese_text)\n",
    "            \n",
    "            # Synchronize failure audio\n",
    "            current_gen_id = time.time()\n",
    "            logger.info(f\"[UI_TRACE] failure: generated ID {current_gen_id}\")\n",
    "            event = overlay.register_audio_event(str(current_gen_id))\n",
    "            logger.info(\"[UI_TRACE] failure: registered audio event\")\n",
    "            \n",
    "            logger.info(\"[UI_TRACE] failure: before play_voice_line\")\n",
    "            overlay.play_voice_line(str(audio_path), str(current_gen_id))\n",
    "            logger.info(f\"[UI_TRACE] failure: play_voice_line called with ID {current_gen_id}\")\n",
    "            \n",
    "            logger.info(f\"[UI_TRACE] failure: waiting for AUDIO_ENDED id={current_gen_id}\")\n",
    "            completed = event.wait(timeout=30)\n",
    "            \n",
    "            if completed:\n",
    "                logger.info(f\"[UI_TRACE] failure: AUDIO_ENDED received id={current_gen_id}\")\n",
    "                logger.info(\"[UI_TRACE] failure: before hide\")\n",
    "                overlay.hide()\n",
    "                logger.info(\"[UI_TRACE] failure: after hide\")\n",
    "            else:\n",
    "                logger.error(f\"[UI_TRACE] failure: audio event timeout for ID {current_gen_id}\")\n",
    "            \n",
    "            overlay.clear_audio_event(str(current_gen_id))\n",
    "            logger.info(\"[UI_TRACE] failure: cleared audio event\")\n",
    "            \n",
    "        except Exception as e:\n",
    "            logger.exception(f\"Failure voice pipeline failed: {e}\")\n"
]

start_idx = -1
end_idx = -1

for i in range(len(lines)):
    if lines[i].strip() == "def handle_failure(self, error_msg: str):":
        start_idx = i
        break

if start_idx == -1:
    print("Error: Could not find handle_failure definition")
    exit(1)

# Find the end of the function (next method at same indentation)
for i in range(start_idx + 1, len(lines)):
    line = lines[i]
    if line.strip() == "":
        continue
    # Check if this line starts at the same indentation as 'def handle_failure'
    # '    def handle_failure' has 4 spaces.
    if line.startswith("    def ") or (line.startswith(" ") and not line.startswith("     ")):
        # This looks like a new method
        end_idx = i
        break

if end_idx == -1:
    # End of file
    end_idx = len(lines)

# Replace
new_lines = lines[:start_idx] + replacement_content + lines[end_idx:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Modification successful")
