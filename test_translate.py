import time
from translate import to_great_sage_japanese

test_sentences = [
    "I am an AI assistant and don't have an age. However, I can help you with various tasks!",
]

for text in test_sentences:
    print(f"\n--- English: {text}")
    start = time.time()
    try:
        result = to_great_sage_japanese(text)
        elapsed = time.time() - start
        print(f"Japanese ({elapsed:.1f}s): {result}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"FAILED after {elapsed:.1f}s: {e}")