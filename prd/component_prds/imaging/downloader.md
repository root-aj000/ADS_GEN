# Image Downloader Component PRD

## 1. Purpose and Scope

### 1.1 Component Purpose
The `ImageDownloader` class is responsible for downloading, validating, verifying, and persisting product images from search results. It implements a sophisticated multi-stage pipeline that ensures only high-quality, relevant images are selected and saved for ad generation.

### 1.2 Position in Architecture
This component sits at the core of the imaging subsystem, serving as the primary interface between search results and validated image assets. It integrates with search engines, image quality scorers, verifiers, and caching systems to provide a comprehensive image acquisition solution.

### 1.3 Key Responsibilities
- Download image candidates from multiple search engine results
- Perform multi-stage validation including file size, dimensions, and aspect ratio checks
- Apply visual content detection to filter blank or low-quality images
- Integrate with CLIP+BLIP verification for semantic relevance checking
- Manage intelligent candidate selection with configurable acceptance thresholds
- Implement efficient image saving with appropriate format selection (PNG/JPEG)
- Coordinate with shared hash tracking for cross-row deduplication

## 2. Functional Requirements

### 2.1 Image Acquisition Pipeline
- Execute HTTP requests to download image data from candidate URLs
- Implement retry logic with exponential backoff for transient failures
- Apply file size filtering based on minimum byte thresholds
- Handle various image formats through PIL library support

### 2.2 Quality Validation
- Validate image dimensions against minimum width and height requirements
- Check aspect ratio constraints to ensure appropriate proportions
- Apply visual content detection to identify and reject blank or uniform images
- Utilize configurable thresholds for standard deviation and unique color requirements

### 2.3 Semantic Verification
- Integrate with CLIP model for image-text similarity scoring
- Leverage BLIP model for image captioning and word overlap analysis
- Combine multiple verification scores with configurable weighting
- Implement threshold-based acceptance/rejection decisions
- Track best candidate fallback mechanism when no images meet strict thresholds

### 2.4 Candidate Selection Intelligence
- Rank candidates using either integrated scorer or simple heuristic scoring
- Implement configurable maximum verification candidate limits
- Apply minimum candidate evaluation before accepting best option
- Provide graceful degradation when verification models are unavailable
- Support skip logic for generating multiple images per product

### 2.5 Storage Management
- Save images in appropriate formats (PNG for RGBA, JPEG for RGB)
- Apply compression settings for optimal file size vs. quality trade-off
- Return comprehensive metadata including dimensions, file size, and verification results
- Implement garbage collection to manage memory during processing

## 3. Input/Output Specifications

### 3.1 Inputs
- `results`: List of `ImageResult` objects from search engines
- `dest`: Destination `Path` for saving the selected image
- `query`: Original search query string for verification purposes
- `skip`: Number of valid candidates to skip before selection
- `ImageQualityConfig`: Configuration for quality thresholds
- `VerificationConfig`: Configuration for verification parameters
- `ThreadSafeSet`: Shared set for cross-row hash deduplication

### 3.2 Outputs
- `DownloadResult` object containing:
  - `success`: Boolean indicating successful download and validation
  - `path`: Path to saved image file
  - `source_url`: URL of the selected image
  - `info`: Dictionary with metadata (dimensions, file size, source, hash)
  - `verification`: Dictionary with verification scores and captions

### 3.3 Configuration Parameters
- Quality thresholds: minimum dimensions, aspect ratios, file sizes
- Verification thresholds: acceptance/rejection scores for CLIP/BLIP
- Retry configuration: maximum attempts, backoff parameters
- Verification limits: maximum candidates to verify, minimum before best selection

## 4. Dependencies

### 4.1 Internal Dependencies
- `config.settings.ImageQualityConfig`: Quality validation parameters
- `config.settings.VerificationConfig`: Verification configuration
- `config.settings.DEFAULT_HEADERS`: HTTP headers for requests
- `imaging.helpers.has_visual_content`: Visual content detection
- `imaging.scorer.ImageQualityScorer`: (Optional) Advanced scoring
- `imaging.verifier.ImageVerifier`: (Optional) Semantic verification
- `search.base.ImageResult`: Search result data structure
- `utils.concurrency.ThreadSafeSet`: Cross-row deduplication
- `utils.log_config`: Structured logging
- `utils.retry.retry`: Retry decorator for HTTP requests

### 4.2 External Dependencies
- `requests`: HTTP library for image downloads
- `PIL.Image`: Image processing and format handling
- `hashlib`: Content hashing for deduplication
- Standard Python libraries: `threading`, `dataclasses`, `io`, `pathlib`, `gc`

## 5. Error Handling and Fault Tolerance

### 5.1 Network Resilience
- Implement retry mechanism with exponential backoff for HTTP failures
- Handle various HTTP status codes appropriately (404, 403, 5xx)
- Apply timeouts to prevent hanging requests
- Gracefully handle DNS resolution failures and connection errors

### 5.2 Data Validation
- Validate image integrity through PIL loading
- Handle corrupted or unsupported image formats gracefully
- Apply comprehensive metadata validation before processing
- Reject images failing any validation criteria without disrupting pipeline

### 5.3 Verification Failures
- Continue processing despite individual verification model failures
- Fall back to basic scoring when AI models are unavailable
- Log verification errors for diagnostic purposes
- Maintain partial functionality even with reduced verification capabilities

### 5.4 Resource Management
- Implement garbage collection to prevent memory accumulation
- Use context managers for proper resource cleanup
- Apply connection pooling for efficient HTTP resource usage
- Handle thread-local storage appropriately

## 6. Performance Criteria

### 6.1 Response Time Targets
- HTTP downloads: Variable based on network and image size
- Image validation: < 50ms per image
- Verification (when enabled): 100-500ms per image (GPU dependent)
- Total candidate processing: < 2 seconds for typical configurations

### 6.2 Resource Usage
- Memory: Proportional to largest image being processed
- Network: One request per candidate evaluated
- CPU: Moderate for validation, high for AI verification
- Threads: Thread-safe with local session storage

### 6.3 Scalability Considerations
- Thread-safe design enabling concurrent downloads
- Connection pooling through thread-local session management
- Configurable limits preventing resource exhaustion
- Efficient garbage collection minimizing memory footprint

## 7. Security Considerations

### 7.1 Input Validation
- Validate all URLs before downloading
- Check content types and file extensions
- Apply size limits to prevent resource exhaustion
- Sanitize file paths to prevent directory traversal

### 7.2 Secure Communication
- Use HTTPS for all image downloads
- Validate SSL certificates in HTTP requests
- Apply appropriate User-Agent and Accept headers
- Implement timeouts to prevent denial of service

### 7.3 Content Safety
- Validate image integrity through PIL loading
- Apply visual content detection to filter inappropriate images
- Check file size limits to prevent oversized downloads
- Maintain hash tracking to prevent duplicate processing

## 8. Testing Requirements

### 8.1 Unit Tests
- Verify HTTP download functionality with mocked responses
- Test validation logic with various image inputs
- Validate verification integration with mocked model responses
- Check candidate ranking and selection algorithms
- Test skip functionality for multiple image generation
- Verify error handling for network and processing failures

### 8.2 Integration Tests
- Validate actual image downloading with real URLs
- Test verification model integration with sample images
- Verify cross-row deduplication effectiveness
- Confirm proper interaction with caching systems
- Test configuration edge cases and boundary conditions

### 8.3 Mocking Strategy
- Mock HTTP responses for network-independent testing
- Simulate verification model outputs for consistent testing
- Control timing to test timeout behavior
- Mock file system operations to isolate logic testing

## 9. Integration Points

### 9.1 Core Pipeline Integration
- Called by `AdPipeline` during image acquisition phase
- Receives search results from `SearchManager`
- Returns validated images for subsequent processing stages
- Integrates with progress tracking for resume capabilities

### 9.2 Verification Integration
- Accepts optional `ImageVerifier` for semantic validation
- Receives `VerificationConfig` for parameter tuning
- Returns verification metadata for logging and analysis
- Falls back to basic scoring when verification disabled

### 9.3 Cache Integration
- Works in conjunction with `ImageCache` for persistent storage
- Shares hash tracking with other downloader instances
- Supports cache hit scenarios through pipeline optimization
- Updates cache with new entries after successful downloads

## 10. Implementation Details

### 10.1 Class Structure
```python
class ImageDownloader:
    def __init__(
        self,
        cfg: ImageQualityConfig,
        hashes: ThreadSafeSet,
        timeout: int = 10,
        scorer: Optional["ImageQualityScorer"] = None,
        verifier: Optional["ImageVerifier"] = None,
        verify_cfg: Optional[VerificationConfig] = None,
    ) -> None:
        # Initialize configuration and dependencies
    
    def download_best(
        self,
        results: List[ImageResult],
        dest: Path,
        query: str = "",
        skip: int = 0,
    ) -> DownloadResult:
        # Main entry point implementing complete pipeline
    
    def _fetch(self, url: str) -> Optional[bytes]:
        # HTTP download with retry logic
    
    def _ok(self, img: Image.Image, raw: bytes) -> bool:
        # Quality validation implementation
    
    def _save(self, img: Image.Image, dest: Path) -> Path:
        # Format-appropriate image saving
    
    def _score(self, r: ImageResult) -> float:
        # Fallback scoring when scorer not available
    
    def _save_and_return(...) -> DownloadResult:
        # Helper for consistent result creation
```

### 10.2 Processing Pipeline
1. Candidate Ranking: Sort by quality score or heuristic
2. Sequential Evaluation: Process candidates in ranked order
3. Download & Hash Check: Fetch and deduplicate
4. Basic Validation: Size, dimensions, visual content
5. Semantic Verification: CLIP+BLIP analysis when enabled
6. Acceptance Decision: Threshold-based or best candidate
7. Storage & Metadata: Save and return comprehensive results

### 10.3 Verification Workflow
- Evaluate up to configured maximum candidates
- Score each with CLIP and/or BLIP models
- Combine scores with configurable weighting
- Accept first image meeting threshold criteria
- Track best candidate as fallback option
- Apply minimum evaluation count before fallback