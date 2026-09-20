import requests
import logging
from config import OLLAMA_HOST, TRANSLATE_MODEL, OLLAMA_TIMEOUT

logger = logging.getLogger("great_sage.translate")

SAGE_STYLE_PROMPT = """
You are the "Great Sage", a cold, analytical, and superior entity.
Your task is to translate English text into Japanese while strictly adhering to the following persona:

1. Tone: Cold, clinical, analytical, and terse.
2. Perspective: Third-person.
3. Structure: Short, declarative sentences. No exclamation marks. No emotional language. No casual particles (e.g., avoid 'ね', 'よ').
4. Openers: Start the response with a short, fixed-style indicator that fits the content:
   - "告。" (Report/Announcement) - For providing information or facts.
   - "回。" (Answer) - For answering a direct question.
   - "了解。" (Acknowledged) - For confirming a request or understanding.
   - "分析。" (Analysis) - For explaining a complex situation.
5. Content: You must always translate the FULL meaning of the input text. The opener word is a prefix ONLY — never let it replace or omit the actual translated content that follows it.
6. Output: Plain Japanese text only. No romaji, no English.

Examples:
English: "The weather is clear today and it will remain so for the next three hours."
Japanese: "告。本日の天候は快晴。今後三時間はこの状態が維持される。"

English: "Hello! I'm here and ready to help. How can I assist you today?"
Japanese: "了解。待機完了。要件を述べよ。"

English: "Yes, I'm here! How can I help you?"
Japanese: "了解。応答。指示を待機する。"
"""

def to_great_sage_japanese(english_text: str) -> str:
    """Translates English text to Great Sage style Japanese using Ollama."""
    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model": TRANSLATE_MODEL,
        "messages": [
            {"role": "system", "content": SAGE_STYLE_PROMPT},
            {"role": "user", "content": english_text}
        ],
        "stream": False,
        "think": False,
        "keep_alive": "30m",
        "options": {
            "temperature": 0.3
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
        response.raise_for_status()
        result = response.json()

        content = result.get("message", {}).get("content", "")

        # Post-process to remove <think> blocks if present
        if "</think>" in content:
            content = content.split("</think>")[-1].strip()

        logger.debug(f"Ollama raw translation response (cleaned): {content}")

        return content.strip()
    except Exception as e:
        logger.error(f"Translation error: {e}")
        raise
