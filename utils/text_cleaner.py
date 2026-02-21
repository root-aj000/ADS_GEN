"""
Text cleaning utilities for fixing malformed query strings.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from utils.log_config import get_logger

log = get_logger(__name__)


def clean_spaced_text(text: str) -> str:
    """
    Fix text where characters are separated by spaces.
    
    Examples:
        "p i z z a" → "pizza"
        "p i z z a   s l i c e" → "pizza slice"
        "normal text" → "normal text" (unchanged)
    """
    if not text:
        return ""
    
    text = str(text).strip()
    if not text:
        return ""
    
    tokens = text.split()
    if not tokens:
        return ""
    
    single_char_count = sum(1 for t in tokens if len(t) == 1)
    single_char_ratio = single_char_count / len(tokens)
    
    if single_char_ratio > 0.7:
        return _reconstruct_spaced_text(text)
    
    return " ".join(tokens)


def _reconstruct_spaced_text(text: str) -> str:
    """
    Reconstruct from character-by-character format.
    "p i z z a   s l i c e" → "pizza slice"
    """
    word_groups = re.split(r'\s{2,}', text)
    
    reconstructed: List[str] = []
    for group in word_groups:
        group = group.strip()
        if not group:
            continue
        
        chars = group.split()
        if chars and all(len(c) == 1 for c in chars):
            reconstructed.append("".join(chars))
        else:
            reconstructed.append(group)
    
    return " ".join(reconstructed)


def strip_junk_suffixes(text: str, suffixes: Tuple[str, ...]) -> str:
    """
    Remove search-engine junk from the end of queries.
    
    Examples:
        "pizza crust filetype png" → "pizza crust"
        "shoes site:amazon.com" → "shoes"
    """
    lower = text.lower()
    for suffix in suffixes:
        idx = lower.find(suffix.lower())
        if idx >= 0:
            text = text[:idx].strip()
            lower = text.lower()
    return text


def clean_query(
    text: str,
    max_words: int = 0,
    strip_suffixes: Optional[Tuple[str, ...]] = None,
) -> str:
    """
    Clean and normalize a search query.
    
    Steps:
        1. Fix character spacing
        2. Remove junk suffixes (filetype png, site:, etc.)
        3. Remove special characters
        4. Normalize whitespace
        5. Optionally limit word count (0 = no limit)
    
    Args:
        text: Raw query text from CSV
        max_words: Max words to keep. 0 = unlimited (full text)
        strip_suffixes: Junk patterns to remove
        
    Returns:
        Cleaned, normalized query string
    """
    if not text:
        return ""
    
    # Step 1: Fix character spacing
    cleaned = clean_spaced_text(text)
    
    # Step 2: Strip junk suffixes
    if strip_suffixes:
        cleaned = strip_junk_suffixes(cleaned, strip_suffixes)
    else:
        # Default junk patterns
        default_junk = (
            "filetype png", "filetype jpg", "filetype jpeg",
            "filetype webp", "filetype gif",
            "site:", "inurl:", "intitle:",
        )
        cleaned = strip_junk_suffixes(cleaned, default_junk)
    
    # Step 3: Remove special characters (keep letters, numbers, spaces, hyphens)
    cleaned = re.sub(r'[^\w\s\-]', ' ', cleaned)
    
    # Step 4: Normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Step 5: Limit words ONLY if max_words > 0
    if max_words > 0:
        words = cleaned.split()[:max_words]
        cleaned = " ".join(words)
    
    return cleaned


def is_valid_query(text: str, ignore_values: tuple) -> bool:
    """Check if a query value is valid."""
    if not text:
        return False
    text = str(text).strip().lower()
    return text not in ignore_values and len(text) > 1