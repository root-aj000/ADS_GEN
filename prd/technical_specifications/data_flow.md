# Technical Specification: Data Flow
## Ad Generator System

---

## 1. Overview

This document details the data flow within the Ad Generator system, covering how data moves through each component, transformations applied, and the relationships between different data entities.

---

## 2. Data Entities

### 2.1 Input Data

#### 2.1.1 Product Catalog (CSV)
The primary input to the system is a CSV file containing product information.

**Structure:**
```csv
Product Name,Price,Category,Description,img_desc,keywords,object_detected,text,monetary_mention,call_to_action,dominant_colour
"Wireless Bluetooth Headphones",$89.99,Electronics,"Noise cancelling headphones with 30hr battery","headphones wireless bluetooth","electronics audio","headphones","Premium sound quality with noise cancellation","20% off today","Shop Now","Black"
```

**Required Columns:**
- At least one column for search query generation (configurable via `QueryConfig.priority_columns`)

**Optional Columns:**
- `img_desc`: Primary search query
- `keywords`: Alternative search terms
- `object_detected`: Detected objects in images
- `text`: Additional descriptive text
- `monetary_mention`: Pricing or discount information
- `call_to_action`: Call-to-action text
- `dominant_colour`: Dominant color for styling

#### 2.1.2 Configuration Settings
Immutable configuration data defined in `config/settings.py`.

**Key Configuration Objects:**
- `AppConfig`: Top-level configuration aggregator
- `PathConfig`: File system paths
- `SearchConfig`: Search engine settings
- `ImageQualityConfig`: Image validation parameters
- `BackgroundRemovalConfig`: Background removal settings
- `PipelineConfig`: Processing parameters
- `QueryConfig`: CSV column mapping

### 2.2 Intermediate Data

#### 2.2.1 Search Results
Data structures representing image search results from various engines.

**Structure:**
```python
class ImageResult:
    url: str           # Image URL
    width: int         # Image width in pixels
    height: int        # Image height in pixels
    source: str        # Search engine source
    thumbnail: str     # Thumbnail URL (if available)
```

#### 2.2.2 Downloaded Images
Raw image data and metadata during processing.

**Structure:**
```python
class DownloadResult:
    success: bool              # Download success status
    path: Optional[Path]       # Saved file path
    source_url: Optional[str]  # Original URL
    info: Dict[str, Any]       # Metadata (dimensions, size, etc.)
    verification: Optional[Dict]  # CLIP/BLIP verification results
```

#### 2.2.3 Processing Statistics
Runtime metrics collected during execution.

**Structure:**
```python
class Stats:
    total: AtomicCounter        # Total products processed
    success: AtomicCounter      # Successfully processed
    failed: AtomicCounter       # Failed processing
    placeholder: AtomicCounter  # Placeholder images used
    bg_removed: AtomicCounter   # Backgrounds removed
    bg_skipped: AtomicCounter   # Background removal skipped
    cache_hits: AtomicCounter   # Cache hits
    dlq_retries: AtomicCounter  # Dead letter queue retries
```

### 2.3 Output Data

#### 2.3.1 Generated Advertisements
Final advertisement images in JPEG format.

**Naming Convention:**
```
ad_{index:04d}.jpg  # e.g., ad_0001.jpg, ad_0002.jpg
```

**Storage Location:**
```
data/output/images/ad_*.jpg
```

#### 2.3.2 Updated CSV
Original CSV with added image path column.

**Added Column:**
```csv
image_path
data/output/images/ad_0001.jpg
```

**Storage Location:**
```
data/output/ads_with_images.csv
```

#### 2.3.3 System Metadata
Persistent data for caching and progress tracking.

**Image Cache (SQLite):**
```
data/cache/images.db
```

**Progress Tracking (SQLite):**
```
data/temp/progress.db
```

**Log Files:**
```
data/logs/ad_generator.log
```

---

## 3. Data Flow Stages

### 3.1 Initialization Stage

#### 3.1.1 Configuration Loading
**Input:** `config/settings.py`
**Process:**
1. Load configuration dataclasses
2. Validate configuration parameters
3. Initialize path structures
4. Set up logging framework

**Output:** `AppConfig` instance

#### 3.1.2 CSV Parsing
**Input:** `data/input/main.csv`
**Process:**
1. Read CSV file using pandas
2. Validate required columns exist
3. Initialize image_path column if missing

**Output:** Pandas DataFrame

#### 3.1.3 Component Initialization
**Input:** `AppConfig`, DataFrame
**Process:**
1. Initialize search engines
2. Initialize image processing components
3. Initialize cache and progress tracking
4. Initialize notification system

**Output:** Initialized component instances

### 3.2 Processing Stage

#### 3.2.1 Product Iteration
**Input:** Product DataFrame, progress tracking
**Process:**
1. Determine processing range (start/end indices)
2. Identify already processed products (resume mode)
3. Create processing queue

**Output:** List of product indices to process

#### 3.2.2 Query Construction
**Input:** Product row data, `QueryConfig`
**Process:**
1. Apply column priority from configuration
2. Clean and normalize text (spacing, special characters)
3. Apply word limits if configured
4. Strip unwanted suffixes

**Output:** Cleaned search query string

**Transformation Example:**
```
Input:  "h e a d p h o n e s   w i r e l e s s"
Output: "headphones wireless"
```

#### 3.2.3 Cache Lookup
**Input:** Search query
**Process:**
1. Generate query hash
2. Query SQLite cache database
3. Validate cached file exists
4. Copy cached file to temporary location if found

**Output:** 
- Cache hit: Path to cached image
- Cache miss: None

#### 3.2.4 Image Search
**Input:** Search query, `SearchConfig`
**Process:**
1. Apply search engine priority order
2. Execute search on primary engine
3. Apply rate limiting and delays
4. Handle circuit breaker status
5. Fallback to secondary engines if needed

**Output:** List of `ImageResult` objects

**Multi-Engine Flow:**
```
Query: "wireless headphones"
│
├─ Google Engine (primary)
│  └─ Results: [ImageResult*, ImageResult*, ...]
│
├─ Bing Engine (fallback)
│  └─ Results: [ImageResult*, ImageResult*, ...]
│
└─ DuckDuckGo Engine (secondary fallback)
   └─ Results: [ImageResult*, ImageResult*, ...]
```

#### 3.2.5 Image Download
**Input:** List of `ImageResult` objects
**Process:**
1. Rank candidates by quality score
2. Iterate through candidates
3. Download image bytes
4. Validate file size minimum
5. Check for duplicate hashes
6. Open image with PIL
7. Validate dimensions and aspect ratio
8. Check for visual content (not blank)

**Output:** `DownloadResult` object

**Quality Scoring Factors:**
- File format (.png bonus)
- Source domain reputation
- Image dimensions (higher is better)
- URL indicators (thumbnail penalties)

#### 3.2.6 AI Verification
**Input:** Downloaded image, search query, `VerificationConfig`
**Process:**
1. Apply CLIP model for image-text similarity
2. Generate BLIP caption for the image
3. Calculate word overlap between caption and query
4. Compute combined verification score
5. Apply acceptance/rejection thresholds

**Output:** Verification results dictionary

**CLIP Process:**
```
Image: [pixel data]
Text:  "wireless headphones"
│
└─ CLIP Model
   └─ Similarity Score: 0.78
```

**BLIP Process:**
```
Image: [pixel data]
│
└─ BLIP Model
   └─ Caption: "black wireless headphones on white background"
   └─ Word Overlap: ["wireless", "headphones"] / ["wireless", "headphones"]
   └─ Overlap Score: 1.0
```

#### 3.2.7 Background Removal
**Input:** Downloaded image, search query, `BackgroundRemovalConfig`
**Process:**
1. Check if query contains scene keywords
2. Skip background removal for scenes
3. Apply rembg AI model
4. Validate object retention ratio
5. Compare with original if retention outside bounds

**Output:** Processed image with background removed

**Decision Logic:**
```
Query: "headphones"
Scene Keywords: [..., "headphones", ...]  # Not a scene keyword
│
└─ Apply Background Removal
   └─ Retention Ratio: 0.65 (within bounds 0.05-0.95)
      └─ Use Background Removed Image
```

#### 3.2.8 Ad Composition
**Input:** Processed image, product data, templates
**Process:**
1. Select appropriate template
2. Render product information text
3. Apply color scheme from dominant color
4. Add pricing and promotional information
5. Include call-to-action button
6. Apply final styling and effects

**Output:** Final advertisement image

**Template Application:**
```
Template: Product Showcase
Layout:
┌─────────────────────────────────────┐
│  [Product Image]                    │
│                                     │
│  Wireless Bluetooth Headphones      │
│  $89.99 • 20% OFF TODAY             │
│                                     │
│  [SHOP NOW]                         │
└─────────────────────────────────────┘
```

### 3.3 Persistence Stage

#### 3.3.1 Image Saving
**Input:** Final advertisement image
**Process:**
1. Determine output path (`ad_{index:04d}.jpg`)
2. Save image with JPEG compression
3. Apply quality settings from configuration

**Output:** Saved image file

#### 3.3.2 Cache Update
**Input:** Downloaded image, search query, metadata
**Process:**
1. Store image metadata in SQLite cache
2. Include query, URL, file path, hash
3. Record dimensions and source engine

**Output:** Updated cache database

#### 3.3.3 Progress Tracking
**Input:** Product index, processing results
**Process:**
1. Record success/failure status
2. Store metadata (source, verification scores)
3. Update completion timestamp
4. Increment attempt counter for failures

**Output:** Updated progress database

#### 3.3.4 CSV Update
**Input:** Product index, image path
**Process:**
1. Update DataFrame with image path
2. Periodically save to temporary file
3. Final save at completion

**Output:** Updated CSV file

### 3.4 Completion Stage

#### 3.4.1 Statistics Reporting
**Input:** Processing statistics
**Process:**
1. Calculate processing rates
2. Compile success/failure metrics
3. Generate cache hit ratios
4. Format human-readable report

**Output:** Console report and log entries

#### 3.4.2 Notification Sending
**Input:** Processing results, `NotificationConfig`
**Process:**
1. Check notification triggers
2. Format completion message
3. Send via webhook or email

**Output:** Sent notifications

#### 3.4.3 Cleanup
**Input:** Temporary files, `AppConfig`
**Process:**
1. Remove worker temporary directories
2. Clean up intermediate files
3. Close database connections

**Output:** Clean filesystem state

---

## 4. Data Transformations

### 4.1 Text Normalization
**Purpose:** Ensure consistent search queries
**Input:** Raw text from CSV columns
**Process:**
1. Strip whitespace
2. Fix character spacing issues
3. Remove special characters
4. Normalize whitespace
5. Apply word limits

**Example:**
```
Input:  "h e a d p h o n e s   w i r e l e s s"
Step 1: "h e a d p h o n e s   w i r e l e s s"
Step 2: "headphones wireless"
Step 3: "headphones wireless"
Step 4: "headphones wireless"
Output: "headphones wireless"
```

### 4.2 Image Quality Scoring
**Purpose:** Rank image candidates by quality
**Input:** `ImageResult` objects
**Process:**
1. Format bonus (.png = +10 points)
2. Domain reputation bonuses
3. Size penalty for thumbnails
4. Source engine weighting
5. Resolution scoring

**Formula:**
```
Score = format_bonus + domain_bonus - thumbnail_penalty 
        + engine_weight + (width × height) / 1,000,000
```

### 4.3 Verification Scoring
**Purpose:** Assess image relevance to query
**Input:** Image data, search query
**Process:**
1. CLIP cosine similarity (0.0-1.0)
2. BLIP word overlap (0.0-1.0)
3. Weighted combination

**Formula:**
```
Combined = (clip_score × clip_weight) + (blip_score × blip_weight)
```

### 4.4 Color Processing
**Purpose:** Extract dominant colors for styling
**Input:** Product image
**Process:**
1. Sample prominent colors
2. Match to predefined palette
3. Apply to template elements

**Mapping:**
```
Input Color: (25, 25, 25)
Closest Match: "Black" → (45, 45, 45)
```

---

## 5. Data Relationships

### 5.1 Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐
│   Product CSV   │◄──────┤  AppConfig      │
│                 │       │                 │
│ ┌─────────────┐ │       │ ┌─────────────┐ │
│ │ Product Row │ │       │ │ PathConfig  │ │
│ └─────────────┘ │       │ │ SearchConf  │ │
│ ┌─────────────┐ │       │ │ QualityConf │ │
│ │ Product Row │ │       │ │   ...       │ │
│ └─────────────┘ │       │ └─────────────┘ │
└─────────────────┘       └─────────────────┘
         │
         ▼
┌─────────────────┐       ┌─────────────────┐
│ Search Results  │◄──────┤ Search Engines  │
│                 │       │                 │
│ ┌─────────────┐ │       │ ┌─────────────┐ │
│ │ ImageResult │ │       │ │ GoogleEng   │ │
│ └─────────────┘ │       │ │ BingEng     │ │
│ ┌─────────────┐ │       │ │ DDGEng      │ │
│ │ ImageResult │ │       │ └─────────────┘ │
│ └─────────────┘ │       └─────────────────┘
└─────────────────┘                │
         │                         ▼
         ▼               ┌─────────────────┐
┌─────────────────┐      │  Rate Limiter   │
│ DownloadedImage │◄─────┤  & CircuitBrk   │
│                 │      └─────────────────┘
│ ┌─────────────┐ │
│ │ Image Bytes │ │
│ └─────────────┘ │
│ ┌─────────────┐ │
│ │ Metadata    │ │
│ └─────────────┘ │
└─────────────────┘
         │
         ▼
┌─────────────────┐       ┌─────────────────┐
│  ProcessedImage │◄──────┤   AI Models     │
│                 │       │                 │
│ ┌─────────────┐ │       │ ┌─────────────┐ │
│ │ CLIP Data   │ │       │ │ CLIP Model  │ │
│ │ BLIP Data   │ │       │ │ BLIP Model  │ │
│ └─────────────┘ │       │ └─────────────┘ │
└─────────────────┘       └─────────────────┘
         │
         ▼
┌─────────────────┐       ┌─────────────────┐
│   Ad Template   │◄──────┤ Template Defs   │
│                 │       │                 │
│ ┌─────────────┐ │       │ ┌─────────────┐ │
│ │ Rendered Ad │ │       │ │ Product Ad  │ │
│ └─────────────┘ │       │ │ Scene Ad    │ │
│ ┌─────────────┐ │       │ │ Banner Ad   │ │
│ │ Rendered Ad │ │       │ └─────────────┘ │
│ └─────────────┘ │       └─────────────────┘
└─────────────────┘
         │
         ▼
┌─────────────────┐       ┌─────────────────┐
│   Output Data   │◄──────┤  Databases      │
│                 │       │                 │
│ ┌─────────────┐ │       │ ┌─────────────┐ │
│ │ Final Ads   │ │       │ │ ImageCache  │ │
│ └─────────────┘ │       │ │ ProgressDB  │ │
│ ┌─────────────┐ │       │ └─────────────┘ │
│ │ Updated CSV │ │       └─────────────────┘
│ └─────────────┘ │
└─────────────────┘
```

### 5.2 Data Lifecycle

```
Creation → Processing → Validation → Transformation → Storage → Usage → Archival

Product Data:
CSV File ──► Query ──► Search ──► Download ──► Verify ──► Process ──► Compose ──► Save

Metadata:
Config ──► Initialize ──► Validate ──► Apply ──► Track ──► Report ──► Notify

Temporary Data:
Worker Files ──► Process ──► Use ──► Delete
```

---

## 6. Data Validation

### 6.1 Input Validation

#### 6.1.1 CSV Validation
**Checks:**
- File existence and readability
- Required column presence
- Data type consistency
- Row count limits

**Actions:**
- Reject invalid files at startup
- Log warnings for inconsistent data
- Skip malformed rows with error logging

#### 6.1.2 Configuration Validation
**Checks:**
- Required path accessibility
- Valid search engine names
- Reasonable numeric ranges
- Compatible feature combinations

**Actions:**
- Prevent system startup on critical errors
- Log warnings for suboptimal settings
- Apply sensible defaults where possible

### 6.2 Processing Validation

#### 6.2.1 Image Validation
**Checks:**
- Minimum dimensions (configurable)
- Aspect ratio bounds
- File size minimum
- Visual content presence

**Actions:**
- Skip images failing validation
- Log rejection reasons
- Try alternative candidates

#### 6.2.2 Verification Validation
**Checks:**
- Model loading success
- Score threshold compliance
- Confidence level assessment

**Actions:**
- Fallback to alternative verification
- Accept/reject based on thresholds
- Log model performance metrics

### 6.3 Output Validation

#### 6.3.1 File Validation
**Checks:**
- Successful file creation
- Correct file format
- Appropriate file size
- Readable content

**Actions:**
- Retry failed saves
- Log file system errors
- Mark products as failed

#### 6.3.2 Data Integrity
**Checks:**
- Cache consistency
- Progress tracking accuracy
- CSV update completeness

**Actions:**
- Database transaction rollback on errors
- Periodic integrity checks
- Automatic repair where possible

---

## 7. Data Security

### 7.1 Data Protection

#### 7.1.1 Temporary Files
- Secure deletion after use
- Restricted file permissions
- Isolated temporary directories

#### 7.1.2 Sensitive Configuration
- Environment variable support
- Secure credential storage
- Configuration encryption (future)

### 7.2 Privacy Considerations

#### 7.2.1 Product Data
- No personal information stored
- Transient processing only
- No external data sharing

#### 7.2.2 Image Data
- Temporary storage only
- No human review by default
- Compliance with image licensing

---

## 8. Data Retention

### 8.1 Cache Data
- **Retention:** Indefinite (configurable)
- **Cleanup:** Manual or automatic based on size
- **Location:** `data/cache/images.db`

### 8.2 Progress Data
- **Retention:** Until next full run (unless resume enabled)
- **Cleanup:** Automatic at startup when resume disabled
- **Location:** `data/temp/progress.db`

### 8.3 Log Data
- **Retention:** Configurable (default 30 days)
- **Cleanup:** Automatic rotation and archiving
- **Location:** `data/logs/ad_generator.log`

### 8.4 Output Data
- **Retention:** Indefinite (user managed)
- **Cleanup:** Manual by user
- **Location:** `data/output/`

---

## 9. Performance Implications

### 9.1 Memory Usage
- **Peak Usage:** ~1.5GB with 4 worker threads
- **Optimization:** Garbage collection after each product
- **Scaling:** Linear with worker count

### 9.2 Disk I/O
- **Reads:** CSV input, cache database, font files
- **Writes:** Image output, cache updates, progress tracking
- **Optimization:** Buffered I/O, batch operations

### 9.3 Network I/O
- **Volume:** Proportional to product count and candidate images
- **Optimization:** Connection pooling, rate limiting
- **Bandwidth:** ~50MB per 100 products (average)

---

*Document Version: 1.0*
*Last Updated: February 18, 2026*