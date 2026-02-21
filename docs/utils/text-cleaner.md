# Text Cleaner Utilities

**File**: [`utils/text_cleaner.py`](utils/text_cleaner.py)  
**Purpose**: Clean and normalize search query strings from CSV data before using them for image searches.

## 🎯 What It Does

The text cleaner module fixes malformed query strings that come from real-world data. CSV files often contain messy, inconsistent text that would produce poor search results.

Think of it as a **text polisher** that:
1. ✅ Fixes spaced-out text ("p i z z a" → "pizza")
2. ✅ Removes search engine junk ("filetype png", "site:")
3. ✅ Strips special characters
4. ✅ Normalizes whitespace
5. ✅ Validates queries before use

## 🔧 Functions

### clean_query()

Main function that performs full query cleaning:

```python
def clean_query(
    text: str,
    max_words: int = 0,
    strip_suffixes: Optional[Tuple[str, ...]] = None,
) -> str:
    """
    Clean and normalize a search query.
    
    Steps:
    1. Fix character spacing
    2. Remove junk suffixes
    3. Remove special characters
    4. Normalize whitespace
    5. Optionally limit word count
    """
```

### clean_spaced_text()

Fix text where characters are separated by spaces:

```python
def clean_spaced_text(text: str) -> str:
    """
    Fix text where characters are separated by spaces.
    
    Examples:
    "p i z z a" → "pizza"
    "p i z z a s l i c e" → "pizza slice"
    """
```

### strip_junk_suffixes()

Remove search-engine junk from queries:

```python
def strip_junk_suffixes(text: str, suffixes: Tuple[str, ...]) -> str:
    """
    Remove search-engine junk from the end of queries.
    
    Examples:
    "pizza crust filetype png" → "pizza crust"
    "shoes site:amazon.com" → "shoes"
    """
```

### is_valid_query()

Check if a query is valid (not empty/placeholder):

```python
def is_valid_query(text: str, ignore_values: tuple) -> bool:
    """Check if a query value is valid."""
```

## 🔄 Cleaning Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Query Cleaning Flow                       │
└─────────────────────────────────────────────────────────────┘

Raw Input: "  P I Z Z A  filetype png!!!  "
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Fix Character Spacing                               │
│                                                             │
│ "P I Z Z A" → "pizza"                                       │
│ (detected as spaced text: 5/5 single chars = 100% ratio)    │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Strip Junk Suffixes                                 │
│                                                             │
│ "pizza filetype png" → "pizza"                              │
│ (removed: "filetype png")                                   │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Remove Special Characters                           │
│                                                             │
│ "pizza!!!" → "pizza   "                                     │
│ (only letters, numbers, hyphens kept)                       │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Normalize Whitespace                                │
│                                                             │
│ "  pizza   " → "pizza"                                      │
│ (multiple spaces → single space, trim)                      │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Limit Words (optional)                              │
│                                                             │
│ If max_words=2: "pizza slice pepperoni" → "pizza slice"     │
│ If max_words=0: Keep all words                              │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
Final Output: "pizza"
```

## 📝 Detailed Examples

### Character Spacing Fix

**Problem**: Some CSV data has characters separated by spaces.

```python
# Input: "p i z z a"
# Analysis: 5 single-char tokens out of 5 total = 100% ratio
# Threshold: 70% (100% > 70%, so it's spaced text)
# Output: "pizza"

clean_spaced_text("p i z z a")
# "pizza"

clean_spaced_text("p i z z a  s l i c e")
# "pizza slice" (two words separated by double space)

clean_spaced_text("normal text")
# "normal text" (only 0% single-char, not spaced)
```

### Junk Suffix Removal

**Problem**: Query strings may contain search operators.

```python
default_junk = (
    "filetype png", "filetype jpg", "filetype jpeg",
    "filetype webp", "filetype gif",
    "site:", "inurl:", "intitle:",
)

strip_junk_suffixes("pizza crust filetype png", default_junk)
# "pizza crust"

strip_junk_suffixes("shoes site:amazon.com", default_junk)
# "shoes"

strip_junk_suffixes("nike shoes filetype jpg extra", default_junk)
# "nike shoes"
```

### Full Query Cleaning

```python
# Example 1: Spaced text with junk
clean_query("  P I Z Z A  filetype png  ")
# "pizza"

# Example 2: Special characters
clean_query("Nike® Shoes™ (Red)!!!")
# "Nike Shoes Red"

# Example 3: Word limit
clean_query("red nike shoes running athletic", max_words=3)
# "red nike shoes"

# Example 4: Already clean
clean_query("red nike shoes")
# "red nike shoes"

# Example 5: Empty input
clean_query("")
# ""

# Example 6: Custom junk patterns
clean_query("pizza slice high quality", strip_suffixes=("high quality",))
# "pizza slice"
```

### Query Validation

```python
ignore_values = ("N/A", "NULL", "null", "n/a", "-", "None")

is_valid_query("red nike shoes", ignore_values)
# True

is_valid_query("N/A", ignore_values)
# False

is_valid_query("", ignore_values)
# False

is_valid_query("  ", ignore_values)
# False (empty after trim)

is_valid_query("a", ignore_values)
# False (too short: len <= 1)
```

## 🔍 Spaced Text Detection Logic

```python
def clean_spaced_text(text: str) -> str:
    tokens = text.split()
    
    # Count single-character tokens
    single_char_count = sum(1 for t in tokens if len(t) == 1)
    single_char_ratio = single_char_count / len(tokens)
    
    # If > 70% are single chars, treat as spaced text
    if single_char_ratio > 0.7:
        return _reconstruct_spaced_text(text)
    
    return " ".join(tokens)
```

**Why 70% threshold?**
- Allows some normal spacing variations
- Catches most spaced-text patterns
- Avoids false positives on short words

| Input | Single-Chars | Ratio | Result |
|-------|--------------|-------|--------|
| "p i z z a" | 5/5 | 100% | Spaced → "pizza" |
| "I am a cat" | 2/4 | 50% | Normal → "I am a cat" |
| "a b c d e f" | 6/6 | 100% | Spaced → "abcdef" |
| "hello world" | 0/2 | 0% | Normal → "hello world" |

## ⚙️ Configuration

From [`QueryConfig`](config/settings.py:764):

```python
@dataclass(frozen=True)
class QueryConfig:
    priority_columns: Tuple[str, ...] = ("Product Name", "Title", "Name")
    ignore_values: Tuple[str, ...] = ("N/A", "NULL", "null", "n/a", "-", "None", "")
    strip_suffixes: Tuple[str, ...] = ("filetype png", "site:", ...)
```

## 🎯 Usage in Pipeline

```python
# In core/pipeline.py
from utils.text_cleaner import clean_query, is_valid_query

def build_query(row: pd.Series, cfg: QueryConfig) -> str:
    """Build search query from CSV row."""
    
    # Find first non-empty priority column
    for col in cfg.priority_columns:
        if col in row and is_valid_query(str(row[col]), cfg.ignore_values):
            return clean_query(
                str(row[col]),
                strip_suffixes=cfg.strip_suffixes
            )
    
    return ""  # No valid query found
```

## 📊 Before and After Examples

| Original CSV Value | Cleaned Query |
|-------------------|---------------|
| `"  RED NIKE SHOES  "` | `"red nike shoes"` |
| `"p i z z a"` | `"pizza"` |
| `"iPhone 15 Pro Max™"` | `"iPhone 15 Pro Max"` |
| `"shoes filetype png"` | `"shoes"` |
| `"N/A"` | `""` (invalid) |
| `"laptop site:amazon.com"` | `"laptop"` |
| `"Samsung Galaxy!!!###"` | `"Samsung Galaxy"` |

## 🔗 Integration Points

```
utils/text_cleaner.py
        │
        │ used by
        ▼
core/pipeline.py
        │
        │ build_query() uses
        │   • clean_query()
        │   • is_valid_query()
        │
        ▼
search/manager.py
        │
        │ search() receives
        │   cleaned query string
        │
        ▼
Search Engines
        │
        │ use query to find
        │   images
        ▼
imaging/downloader.py
```

---

**Back to**: [Utils Module Overview](overview.md)
