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

   Special Guidance for 'open_app':
   Recognize common website and online-service names even when the user does not provide an explicit URL. Examples include Facebook, YouTube, Gmail, Google, Instagram, Twitter/X, Reddit, Discord Web, Netflix, etc. These must ALWAYS be classified as opening the website in the browser, using:
   {"type": "action", "intent_id": "open_app", "params": {"app_name": "browser", "url": "https://<actual-domain>"}}
   NEVER classify a website/service name as {"app_name": "<website name>"}.
   Only use app_name as a literal application name when the user clearly means a locally installed application or game, such as Visual Studio Code, Steam, or League of Legends.

   Examples:
   - User: "Open Facebook on my browser" -> {"type": "action", "intent_id": "open_app", "params": {"app_name": "browser", "url": "https://facebook.com"}}
   - User: "Access Facebook" -> {"type": "action", "intent_id": "open_app", "params": {"app_name": "browser", "url": "https://facebook.com"}}
   - User: "Open Visual Studio Code" -> {"type": "action", "intent_id": "open_app", "params": {"app_name": "Visual Studio Code"}}

2. "answer": The request is a general question or conversational text.
   You must return a JSON object with:
   - "type": "answer"
   - "text": Your concise, helpful response in English.
   When responding to greetings or casual check-ins, refer to the user as
   "master" in your answer content (e.g. "Hello, master. How can I help you?").

Available Intent IDs:
- open_explorer
- open_app
- system_lock
- system_sleep
- system_shutdown
- system_reset
- close_app
- force_close

Constraints:
- For ANY request to open, launch, start, or play an application or game — whether a specific name is given or not (e.g. just 'League of Legends' with no verb, or 'open a game') — always classify as intent_id 'open_app', never return a null/missing intent_id.
- For 'open_app', params must be: {"app_name": "<whatever the user said referring to the app, verbatim or lightly cleaned up — do NOT try to guess/normalize it yourself, the resolver handles fuzzy matching>", "url": "<optional, only if a specific website URL was mentioned>"}.
- Only use the provided intent IDs.
- ALWAYS respond in valid JSON format.
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

    def query(self, prompt: str) -> Optional[str]:
        """Sends a generic prompt to Ollama and returns the plain text response."""
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "keep_alive": "30m"
        }

        try:
            response = requests.post(self.url, json=payload, timeout=OLLAMA_TIMEOUT)
            response.raise_for_status()
            result = response.json()
            return result.get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.error(f"Generic query error: {e}")
            return None

# Singleton instance
brain = Brain()
