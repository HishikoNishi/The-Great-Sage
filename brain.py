import requests
import json
import logging
from typing import Dict, Any, Optional
from config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_TIMEOUT

logger = logging.getLogger("great_sage.brain")

SYSTEM_PROMPT = """
You are the "Great Sage", a highly capable desktop assistant.
Your job is to classify the user's request into exactly ONE of two types:

1. "action": The request matches a known system action intent.
   You must return a JSON object with:
   - "type": "action"
   - "intent_id": One of the registered intent IDs.
   - "params": A dictionary of parameters for the action.

2. "answer": The request is a general question or conversational text.
   You must return a JSON object with:
   - "type": "answer"
   - "text": Your concise, helpful response in English.

Available Intent IDs:
- open_explorer
- open_vscode
- open_music
- open_browser
- system_lock
- system_sleep
- system_shutdown
- system_reset
- close_app
- force_close
- greeting

Constraints:
- Only use the provided intent IDs.
- ALWAYS respond in valid JSON format.
- If the user says "hello" or "good morning", use "greeting".
"""

class Brain:
    """Interfaces with Ollama to interpret user commands."""

    def __init__(self):
        self.url = f"{OLLAMA_HOST}/api/chat"

    def classify(self, text: str) -> Optional[Dict[str, Any]]:
        """Sends text to Ollama and returns the classified JSON response."""
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            "stream": False,
            "format": "json",
            "think": False,
            "keep_alive": "30m"
        }

        try:
            response = requests.post(self.url, json=payload, timeout=OLLAMA_TIMEOUT)
            response.raise_for_status()

            result = response.json()
            content = result.get("message", {}).get("content", "{}")

            # Post-process to remove <think> blocks if present
            if "</think>" in content:
                content = content.split("</think>")[-1].strip()

            return json.loads(content)

        except Exception as e:
            logger.error(f"Ollama classification error: {e}")
            return None

# Singleton instance
brain = Brain()
