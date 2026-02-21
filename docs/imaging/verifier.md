# ImageVerifier

**File**: [`imaging/verifier.py`](imaging/verifier.py)  
**Purpose**: AI-powered image-text verification using CLIP and BLIP models to ensure downloaded images match search queries.

## 🎯 What It Does

The `ImageVerifier` is like having a professional art critic who can look at an image and tell you if it matches what you asked for. It uses two AI models to verify that the downloaded image actually shows the product you searched for.

Think of it as a **quality control inspector** who:
1. ✅ Compares image content with search query using CLIP (visual similarity)
2. ✅ Generates a caption for the image using BLIP (what does it show?)
3. ✅ Compares the AI caption with your query (word overlap)
4. ✅ Combines both scores to accept or reject the image

**Why is this needed?** Image search isn't perfect. A search for "red nike shoes" might return:
- ✅ Actual red Nike shoes (correct!)
- ❌ Blue Nike shoes (wrong color)
- ❌ Red Adidas shoes (wrong brand)
- ❌ A person wearing red shoes (not product-focused)
- ❌ A shoe store sign (not the product itself)

The verifier catches these mismatches before using the image.

## 🔧 Class Structure

```python
@dataclass
class VerificationResult:
    """Result of verifying one image against a query."""
    accepted: bool           # Should we accept this image?
    clip_score: float        # CLIP similarity (0.0-1.0)
    blip_score: float        # BLIP word overlap (0.0-1.0)
    combined_score: float    # Weighted combination
    blip_caption: str        # AI-generated caption
    reason: str              # Acceptance/rejection reason

class ImageVerifier:
    """
    Singleton that loads CLIP and BLIP models once,
    then verifies images against text queries.
    
    Thread-safe: uses locks around model inference.
    """
    
    _instance: Optional["ImageVerifier"] = None
    _init_lock = threading.Lock()
```

### Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| [`verify()`](imaging/verifier.py:335) | Verify image matches query | `VerificationResult` |
| [`_clip_score()`](imaging/verifier.py:244) | Compute CLIP similarity | `float` |
| [`_blip_caption()`](imaging/verifier.py:286) | Generate image caption | `str` |
| [`_blip_score()`](imaging/verifier.py:322) | Compute word overlap | `Tuple[float, str]` |

## 🔄 Verification Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  Image Verification Flow                    │
└─────────────────────────────────────────────────────────────┘

Downloaded Image + Query: "red nike shoes"
                    │
                    ▼
         ┌─────────────────────┐
         │   CLIP Analysis     │
         │                     │
         │  Image ──┐          │
         │          ├──► Score │
         │  Query ──┘          │
         │                     │
         │  "How similar are   │
         │   image and text?"  │
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │   BLIP Analysis     │
         │                     │
         │  Image ──► Caption  │
         │                     │
         │  "red nike running  │
         │   shoes on white bg"│
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  Word Overlap       │
         │                     │
         │  Caption vs Query   │
         │                     │
         │  "red nike running  │
         │   shoes" vs         │
         │  "red nike shoes"   │
         │                     │
         │  Match: red, nike,  │
         │         shoes (3/3) │
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  Combine Scores     │
         │                     │
         │  CLIP: 0.85         │
         │  BLIP: 0.72         │
         │  Combined: 0.79     │
         │                     │
         │  Threshold: 0.20    │
         │  0.79 > 0.20 ✓      │
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  ACCEPTED ✅        │
         │                     │
         │  Use this image!    │
         └─────────────────────┘
```

## 🤖 AI Models Explained

### CLIP (Contrastive Language-Image Pre-training)

**What it does**: Measures how well an image matches a text description

**How it works**:
1. Convert image to a vector (list of numbers representing visual features)
2. Convert text to a vector (list of numbers representing semantic meaning)
3. Calculate cosine similarity between vectors (how aligned are they?)

**Real-world analogy**: Like showing a photo to someone and asking "Does this match 'red nike shoes'?" They give you a yes/no feeling based on visual similarity.

```python
def _clip_score(self, image: Image.Image, query: str) -> float:
    """Compute CLIP cosine similarity between image and text."""
    if self._clip_model is None:
        return 0.0
    
    with self._clip_lock:
        import torch
        
        # Process inputs
        inputs = self._clip_processor(
            text=[query],
            images=image,
            return_tensors="pt",
            padding=True
        ).to(self._device)
        
        # Get embeddings
        with torch.no_grad():
            outputs = self._clip_model(**inputs)
            
        # Cosine similarity (0-1 range)
        logits = outputs.logits_per_image
        score = torch.sigmoid(logits[0][0]).item()
        
        return score
```

**Score interpretation**:
| Score | Meaning |
|-------|---------|
| 0.9+ | Excellent match - image clearly shows the query |
| 0.7-0.9 | Good match - image relates to query |
| 0.5-0.7 | Moderate match - some relevance |
| 0.3-0.5 | Weak match - questionable relevance |
| < 0.3 | Poor match - likely unrelated |

### BLIP (Bootstrapping Language-Image Pre-training)

**What it does**: Generates a text caption describing the image content

**How it works**:
1. Feed image to the BLIP model
2. Model generates text token by token
3. Compare generated caption with original query

**Real-world analogy**: Like asking someone "What do you see in this picture?" and comparing their answer to what you expected.

```python
def _blip_caption(self, image: Image.Image) -> str:
    """Generate caption for image using BLIP."""
    if self._blip_model is None:
        return ""
    
    with self._blip_lock:
        import torch
        
        # Process image
        inputs = self._blip_processor(
            image, 
            return_tensors="pt"
        ).to(self._device)
        
        # Generate caption
        with torch.no_grad():
            output = self._blip_model.generate(**inputs, max_length=50)
        
        caption = self._blip_processor.decode(output[0], skip_special_tokens=True)
        return caption
```

**Example captions**:
| Image | Generated Caption |
|-------|-------------------|
| Red Nike shoes | "red nike running shoes on white background" |
| Blue shoes | "blue athletic sneakers on a wooden floor" |
| Person wearing shoes | "a person wearing red shoes standing on grass" |
| Shoe store | "a shoe store display with many shoes on shelves" |

## 📊 Word Overlap Scoring

After BLIP generates a caption, we compare it with the query:

```python
def _word_overlap_score(text_a: str, text_b: str) -> float:
    """Compute word-level overlap between two texts."""
    stop_words = {"a", "an", "the", "is", "are", ...}
    
    # Extract meaningful words
    words_a = {w.lower() for w in text_a.split() if len(w) > 1} - stop_words
    words_b = {w.lower() for w in text_b.split() if len(w) > 1} - stop_words
    
    # Calculate overlap
    intersection = words_a & words_b
    union = words_a | words_b
    
    # Weighted: 70% query coverage + 30% Jaccard
    query_coverage = len(intersection) / len(words_a) if words_a else 0
    jaccard = len(intersection) / len(union) if union else 0
    
    return 0.7 * query_coverage + 0.3 * jaccard
```

**Example**:
```
Query:   "red nike shoes"
Caption: "red nike running shoes on white background"

Words in query:   {red, nike, shoes}
Words in caption: {red, nike, running, shoes, white, background}

Intersection: {red, nike, shoes} - 3 words
Union: {red, nike, running, shoes, white, background} - 6 words

Query coverage: 3/3 = 1.0 (all query words found)
Jaccard: 3/6 = 0.5 (half of all words match)

Final score: 0.7 * 1.0 + 0.3 * 0.5 = 0.85
```

## ⚙️ Configuration

From [`VerificationConfig`](config/settings.py:717):

```python
@dataclass(frozen=True)
class VerificationConfig:
    use_clip: bool = True              # Enable CLIP model
    use_blip: bool = True              # Enable BLIP model
    clip_model: str = "openai/clip-vit-base-patch32"
    blip_model: str = "Salesforce/blip-image-captioning-base"
    clip_threshold: float = 0.25       # Minimum CLIP score
    blip_threshold: float = 0.15       # Minimum BLIP score
    combined_threshold: float = 0.20   # Minimum combined score
    device: str = "auto"               # "auto", "cuda", or "cpu"
```

## 🔗 Singleton Pattern

The `ImageVerifier` uses a singleton pattern to load models only once:

```python
class ImageVerifier:
    _instance: Optional["ImageVerifier"] = None
    _init_lock = threading.Lock()
    
    def __new__(cls, cfg: VerificationConfig):
        """Singleton: one instance shared across all threads."""
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self, cfg: VerificationConfig) -> None:
        if self._initialized:
            return  # Already initialized, skip
        
        self.cfg = cfg
        self._setup_device()
        self._load_models()
        self._initialized = True
```

**Why singleton?**
- AI models are large (hundreds of MB)
- Loading them is slow (several seconds)
- Multiple threads can share the same model instance
- Models are thread-safe when inference is locked

## 🧵 Thread Safety

```python
# Locks protect model inference
self._clip_lock = threading.Lock()
self._blip_lock = threading.Lock()

def _clip_score(self, image, query):
    with self._clip_lock:  # Only one thread at a time
        # ... model inference ...

def _blip_caption(self, image):
    with self._blip_lock:  # Only one thread at a time
        # ... model inference ...
```

**Why locks?** The model inference is not thread-safe. Multiple threads calling the model simultaneously would cause errors or corrupted results.

## 🎯 Real-World Example

### Scenario: Verifying "Red Nike Shoes" Images

```python
verifier = ImageVerifier(cfg)

# Test Image 1: Actual red Nike shoes
img1 = Image.open("red_nike_shoes.png")
result1 = verifier.verify(img1, "red nike shoes")
print(result1.summary())
# ✅ ACCEPT (combined=0.790 | clip=0.850 | blip=0.720 | caption='red nike running shoes')

# Test Image 2: Blue Nike shoes (wrong color)
img2 = Image.open("blue_nike_shoes.png")
result2 = verifier.verify(img2, "red nike shoes")
print(result2.summary())
# ❌ REJECT (combined=0.150 | clip=0.200 | blip=0.100 | caption='blue nike athletic shoes')

# Test Image 3: Person wearing shoes
img3 = Image.open("person_wearing_shoes.jpg")
result3 = verifier.verify(img3, "red nike shoes")
print(result3.summary())
# ❌ REJECT (combined=0.180 | clip=0.250 | blip=0.110 | caption='person wearing red shoes on grass')
```

### Integration with Pipeline

```python
# In core/pipeline.py
if self.verifier:
    result = self.verifier.verify(image, query)
    if not result.accepted:
        log.warning(
            "Image rejected for '%s': %s",
            query,
            result.reason
        )
        # Try next candidate
        continue
```

## 📈 Performance Considerations

| Device | Model Load Time | Inference Time |
|--------|-----------------|----------------|
| CPU | 5-10 seconds | 200-500ms per image |
| GPU (CUDA) | 3-5 seconds | 50-100ms per image |

**Tips for faster verification**:
1. Use GPU if available (automatically detected with `device="auto"`)
2. Set `use_clip=False` or `use_blip=False` to skip one model
3. Increase thresholds to reject more quickly

## 🔍 VerificationResult Summary

```python
@dataclass
class VerificationResult:
    accepted: bool           # Final decision
    clip_score: float        # 0.0-1.0
    blip_score: float        # 0.0-1.0
    combined_score: float    # Weighted average
    blip_caption: str        # AI-generated description
    reason: str              # Explanation
    
    def summary(self) -> str:
        status = "✅ ACCEPT" if self.accepted else "❌ REJECT"
        return f"{status} (combined={self.combined_score:.3f} ...)"
```

---

**Next**: [Background Removal](background.md) → AI-powered background removal
