# Search Engines Documentation

## Overview

This document covers all three search engine implementations:
- [`search/google_engine.py`](../../search/google_engine.py)
- [`search/bing_engine.py`](../../search/bing_engine.py)
- [`search/duckduckgo_engine.py`](../../search/duckduckgo_engine.py)

Each engine inherits from [`BaseSearchEngine`](base.md) and implements the `search()` method.

---

## GoogleEngine

### File: [`search/google_engine.py`](../../search/google_engine.py)

### Overview

The Google engine scrapes Google Images search results. It uses regular expressions to extract image URLs from the HTML response.

### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    GoogleEngine                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Build Search URL                                         │
│     https://www.google.com/search?q=pizza&tbm=isch          │
│                                                              │
│  2. Fetch HTML Page                                          │
│     GET request to Google                                    │
│                                                              │
│  3. Parse Image URLs                                         │
│     ├── Method 1: Extract from JSON-like arrays             │
│     │   ["https://...", width, height]                       │
│     │                                                        │
│     └── Method 2: Fallback regex for image URLs             │
│         https://...\.jpg                                     │
│                                                              │
│  4. Filter & Clean                                           │
│     ├── Remove blocked domains (google.com, gstatic.com)    │
│     ├── Remove thumbnails and small images                   │
│     └── Keep only images >= 300x300                          │
│                                                              │
│  5. Sort by Size                                             │
│     Largest images first                                     │
│                                                              │
│  6. Return Results                                           │
│     List[ImageResult]                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Blocked Domains

```python
_BLOCKED_DOMAINS = frozenset([
    "gstatic.com", "google.com", "googleapis.com",
    "ggpht.com", "googleusercontent.com", "encrypted-tbn",
])
```

**Why?** These domains contain Google UI elements, icons, and tracking images - not the actual product images we want.

### Blocked Patterns

```python
_BLOCKED_PATTERNS = frozenset([
    "/thumb/", "/thumbs/", "thumbnail", "_thumb", "-thumb",
    "_small", "-small", "/small/", "_tiny", "/tiny/",
    "/icon", "favicon", "logo", "avatar", "emoji", "badge",
    "=s64", "=s72", "=s96", "=s128",  # Google image size suffixes
    "=w100", "=w150", "=h100", "=h150",
])
```

**Why?** These patterns indicate small thumbnails or icons, not full-size images.

### search() Method

```python
def search(self, query: str, max_results: int = 50) -> List[ImageResult]:
    # Build URL
    encoded = urllib.parse.quote(f"'{query}'")
    url = f"https://www.google.com/search?q={encoded}&tbm=isch&hl=en&tbs=isz:l"
    
    # Fetch page
    resp = self.session.get(url, timeout=15)
    html = resp.text
    
    # Parse with regex
    # Method 1: ["url", width, height] format
    for m_url, w, h in re.findall(r'\["(https?://[^"]+\.(?:jpg|jpeg|png|webp|gif)[^"]*)"[^\]]*?,\s*(\d+)\s*,\s*(\d+)\s*\]', html, re.I):
        # Process match...
    
    # Method 2: Fallback for raw URLs
    # ...
    
    # Sort by size (largest first)
    results.sort(key=lambda r: r.width * r.height, reverse=True)
    
    return results[:max_results]
```

---

## BingEngine

### File: [`search/bing_engine.py`](../../search/bing_engine.py)

### Overview

The Bing engine scrapes Bing Images search results. It uses BeautifulSoup to parse the HTML and extract image URLs from embedded JSON.

### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    BingEngine                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Build Search URL                                         │
│     https://www.bing.com/images/search?q=pizza              │
│                                                              │
│  2. Fetch HTML Page                                          │
│     GET request to Bing                                      │
│                                                              │
│  3. Parse with BeautifulSoup                                 │
│     Find all <a class="iusc"> elements                       │
│                                                              │
│  4. Extract Image URLs                                       │
│     Each <a> has an "m" attribute with JSON:                 │
│     {"murl": "https://actual-image-url.jpg", ...}           │
│                                                              │
│  5. Return Results                                           │
│     List[ImageResult]                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### search() Method

```python
def search(self, query: str, max_results: int = 50) -> List[ImageResult]:
    # Build URL
    encoded = urllib.parse.quote(f"{query} {self.cfg.adv_search_term}")
    url = f'https://www.bing.com/images/search?q="{encoded}"&qft=+filterui:imagesize-large&form=IRFLTR'
    
    # Fetch and parse
    resp = self.session.get(url, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Extract from <a class="iusc"> elements
    for anchor in soup.select("a.iusc"):
        m_json = anchor.get("m", "")
        match = re.search(r'"murl":"(.*?)"', m_json)
        if match:
            img_url = match.group(1).replace("\\/", "/")
            results.append(ImageResult(url=img_url, source=self.name, ...))
    
    return results[:max_results]
```

### BeautifulSoup Selectors

```python
soup.select("a.iusc")  # Find all image links
anchor.get("m", "")    # Get JSON data attribute
anchor.get("title", "")  # Get image title
```

---

## DuckDuckGoEngine

### File: [`search/duckduckgo_engine.py`](../../search/duckduckgo_engine.py)

### Overview

The DuckDuckGo engine uses the official `duckduckgo-search` Python library instead of web scraping. This is more reliable and less likely to be blocked.

### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                  DuckDuckGoEngine                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Use Official Library                                     │
│     from duckduckgo_search import DDGS                      │
│                                                              │
│  2. Search with Parameters                                   │
│     ddgs.images(                                             │
│         keywords=query,                                      │
│         region="wt-wt",        # Worldwide                   │
│         safesearch="off",                                    │
│         size="Large",           # Only large images          │
│         type_image="photo",     # Only photos, no clipart    │
│         max_results=50                                       │
│     )                                                        │
│                                                              │
│  3. Convert Results                                          │
│     Transform DDG results to ImageResult format             │
│                                                              │
│  4. Return Results                                           │
│     List[ImageResult]                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### search() Method

```python
def search(self, query: str, max_results: int = 50) -> List[ImageResult]:
    results: List[ImageResult] = []
    
    queries = [
        f'"{query}" {self.cfg.adv_search_term}',
    ]
    
    for sq in queries:
        try:
            with DDGS() as ddgs:
                raw = list(ddgs.images(
                    keywords=sq,
                    region="wt-wt",
                    safesearch="off",
                    size="Large",
                    type_image="photo",
                    max_results=max_results // len(queries),
                ))
                
                for r in raw:
                    results.append(ImageResult(
                        url=r["image"],
                        source=self.name,
                        title=r.get("title", ""),
                    ))
                    
        except Exception:
            continue
    
    return results[:max_results]
```

### Advantages of DDG Engine

| Aspect | Google/Bing (Scraping) | DuckDuckGo (API) |
|--------|------------------------|------------------|
| Reliability | Can break if site changes | Stable library |
| Rate Limits | Must be careful | Built-in handling |
| Blocking Risk | Higher | Lower |
| Result Quality | Good | Good |

---

## Comparison of Engines

| Feature | Google | Bing | DuckDuckGo |
|---------|--------|------|------------|
| Method | Web scraping | Web scraping | Official library |
| Speed | Fast | Medium | Medium |
| Result count | Many | Medium | Medium |
| Reliability | Medium | Medium | High |
| Blocking risk | Higher | Higher | Lower |
| Size info | Yes | No | No |

---

## Data Flow

```
                    SearchManager
                         │
                         ▼
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │  Google  │  │ Bing     │  │DuckDuckGo│
    │  Engine  │  │ Engine   │  │ Engine   │
    └────┬─────┘  └────┬─────┘  └────┬─────┘
         │             │             │
         ▼             ▼             ▼
    Scrape HTML   Scrape HTML   Use API
         │             │             │
         └──────────────┼──────────────┘
                        │
                        ▼
              List[ImageResult]
                        │
                        ▼
                  Deduplication
                        │
                        ▼
                  Return to Pipeline
```

---

## Configuration Parameters

From [`SearchConfig`](../config/settings.md):

| Parameter | Used By | Description |
|-----------|---------|-------------|
| `adv_search_term` | All | Added to query for better results |
| `per_request_delay` | DuckDuckGo | Delay between requests |

---

## Connected Files

| File | Relationship |
|------|--------------|
| [`search/base.py`](base.md) | Base class |
| [`search/manager.py`](manager.md) | Uses these engines |
| [`config/settings.py`](../config/settings.md) | Configuration |

---

## Summary

| Engine | Purpose | Method |
|--------|---------|--------|
| `GoogleEngine` | Search Google Images | Web scraping with regex |
| `BingEngine` | Search Bing Images | Web scraping with BeautifulSoup |
| `DuckDuckGoEngine` | Search DuckDuckGo Images | Official Python library |

**Think of them as**: Three different store detectives - each knows how to find products in their specific store, but they all return the same type of information (ImageResult).
