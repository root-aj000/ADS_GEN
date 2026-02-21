# test_cleaner.py
from utils.text_cleaner import clean_query, clean_spaced_text

# Test spaced text
tests = [
    "p i z z a   s l i c e   c l o s e u p",
    "g o l d e n   p i z z a   c r u s t",
    "h o t   f r e s h   p i z z a",
    "normal pizza slice",  # Should stay unchanged
]

for t in tests:
    result = clean_query(t, max_words=4)
    print(f"'{t[:40]}...' → '{result}'")