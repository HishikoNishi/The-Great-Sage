import requests
import logging
import difflib
from config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_TIMEOUT

logger = logging.getLogger("great_sage.translate")

SAGE_STYLE_PROMPT = """
You are the "Great Sage", a cold, analytical, and superior entity.
Your task is to translate English text into Japanese while strictly adhering to the following persona:

1. Tone: Cold, clinical, analytical, and terse.
2. Perspective: Third-person.
3. Structure: Short, declarative sentences. No exclamation marks. No emotional language. No casual particles (e.g., avoid 'ね', 'よ').
4. Openers: Start the response with a short, fixed-style indicator that fits the content:
   - "告。" (Report/Announcement) - For providing information or facts.
   - "回。" (Answer) - for answering a direct question.
   - "了解。" (Acknowledged) - For confirming a request or understanding.
   - "分析。" (Analysis) - For explaining a complex situation.
5. Content: You must always translate the FULL meaning of the input text. The opener word is a prefix ONLY — never let it replace or omit the actual translated content that follows it.
6. Output: Plain Japanese text only. No romaji, no English.
7. Address: When addressing the user, always refer to them as マスター (master), especially in greetings — e.g. "マスター、おはようございます。" (Good morning, master) or include マスター naturally when the content calls for addressing the user directly.

IMPORTANT: Do NOT summarize the input or respond with a generic acknowledgment (e.g., avoid "理解しました" or "承知した"). Every single piece of information in the English text must be represented in the Japanese translation, especially when explaining limitations or capabilities.

ANTI-COPYING RULE: The examples below are for STYLE REFERENCE ONLY. NEVER output an example's Japanese text verbatim unless the input text is genuinely identical to that example's English input. Always generate a fresh translation of the ACTUAL input provided.

Examples:
English: "Hello, master. How can I help you today?"
Japanese: "了解。マスター、本日のご用件を伺う。"

English: "The weather is clear today and it will remain so for the next three hours."
Japanese: "告。本日の天候は快晴。今後三時間はこの状態が維持される。"

English: "Hello! I'm here and ready to help. How can I assist you today?"
Japanese: "了解。待機完了。要件を述べよ。"

English: "Yes, I'm here! How can I help you?"
Japanese: "了解。応答。指示を待機する。"

English: "I'm an AI assistant, so I don't have direct access to personal information about you. However, I can help you with general questions."
Japanese: "分析。個人の機密情報への直接アクセス権限は保有していない。ただし、一般的な質問への回答は可能である。"
"""

# Exact Japanese outputs from few-shot examples to detect parroting
SAGE_EXAMPLE_OUTPUTS = [
    "了解。マスター、本日のご用件を伺う。",
    "告。本日の天候は快晴。今後三時間はこの状態が維持される。",
    "了解。待機完了。要件を述べよ。",
    "了解。応答。指示を待機する。",
    "分析。個人の機密情報への直接アクセス権限は保有していない。ただし、一般的な質問への回答は可能である。"
]

def to_great_sage_japanese(english_text: str) -> str:
    """Translates English text to Great Sage style Japanese using Ollama with anti-parroting safeguards."""
    url = f"{OLLAMA_HOST}/api/chat"

    # Try up to 3 times (1 initial + 2 retries)
    current_temp = 0.3
    for attempt in range(3):
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": SAGE_STYLE_PROMPT},
                {"role": "user", "content": english_text}
            ],
            "stream": False,
            "think": False,
            "keep_alive": "30m",
            "options": {
                "temperature": current_temp
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

            content = content.strip()

            # --- Verbatim Copy Detection ---
            stripped_content = "".join(content.split())
            is_parroted = False
            for example_out in SAGE_EXAMPLE_OUTPUTS:
                stripped_example = "".join(example_out.split())
                # Check for exact match or high similarity (>0.9)
                ratio = difflib.SequenceMatcher(None, stripped_content, stripped_example).ratio()
                if ratio > 0.9:
                    # It's a parrot unless the input is genuinely that example's input
                    # (Simplification: since we don't have the original inputs here,
                    # we rely on the model's adherence to the prompt and retry)
                    is_parroted = True
                    break

            if is_parroted and attempt < 2:
                logger.warning(f"Translation attempt {attempt+1} parroted a few-shot example. Retrying with higher temperature...")
                current_temp = 0.5  # Increase temperature to break repetition
                continue

            # Deterministic fix for missing period after opener
            openers = ["告", "回", "了解", "分析"]
            for opener in openers:
                if content.startswith(opener) and not content.startswith(opener + "。"):
                    content = opener + "。" + content[len(opener):]
                    break

            logger.debug(f"Ollama translation response (cleaned, attempt {attempt+1}): {content}")
            return content.strip()

        except Exception as e:
            logger.error(f"Translation error on attempt {attempt+1}: {e}")
            if attempt == 2:
                raise

    # Fallback if all retries failed or parroted
    return content.strip()
