# Google Search Engine Component PRD

## 1. Purpose and Scope

### 1.1 Component Purpose
The `GoogleEngine` class implements a specialized search engine adapter for Google Images, providing the capability to search for product images using Google's search infrastructure. It handles URL cleaning, filtering of inappropriate content, and extraction of high-quality images.

### 1.2 Position in Architecture
This component is a concrete implementation of the `BaseSearchEngine` abstract class, positioned as one of the search engine adapters in the search subsystem. It integrates with the search manager to provide distributed search capabilities across multiple engines.

### 1.3 Key Responsibilities
- Implement Google Images search functionality using web scraping techniques
- Extract and parse image URLs from Google search results
- Filter out low-quality and inappropriate images
- Clean and normalize image URLs for reliable downloading
- Sort results by image dimensions to prioritize high-quality images

## 2. Functional Requirements

### 2.1 Google Images Search Implementation
- Construct proper Google Images search URLs with query parameters
- Execute HTTP requests to Google Images with appropriate headers
- Parse HTML responses to extract image URLs and metadata
- Handle multiple parsing methods for robustness against Google UI changes

### 2.2 Image Filtering
- Block domains associated with Google infrastructure (gstatic.com, etc.)
- Filter out thumbnails, icons, logos, and avatars
- Exclude images with specific size parameters indicating low quality
- Apply pattern-based filtering to remove unwanted image types

### 2.3 URL Cleaning and Normalization
- Decode escaped Unicode characters in URLs
- Remove trailing punctuation and brackets
- Normalize URL encoding for consistent handling

### 2.4 Result Quality Optimization
- Filter images based on minimum dimension requirements (300x300 pixels)
- Sort results by image area (width × height) in descending order
- Limit results to specified maximum count

## 3. Input/Output Specifications

### 3.1 Inputs
- `query`: String search term for finding product images
- `max_results`: Integer maximum number of results to return (default: 50)
- `SearchConfig`: Configuration object inherited from base class containing advanced search terms and filtering parameters

### 3.2 Outputs
- List of `ImageResult` objects containing:
  - `url`: String cleaned URL of the image resource
  - `source`: String identifier "google"
  - `title`: Empty string (not extracted in current implementation)
  - `width`: Integer pixel width of the image
  - `height`: Integer pixel height of the image
- Empty list on errors, insufficient results, or when response is too small

### 3.3 Configuration Parameters
- `adv_search_term`: Advanced search terms appended to queries
- Various filtering parameters used indirectly through base class

## 4. Dependencies

### 4.1 Internal Dependencies
- `search.base.BaseSearchEngine`: Inherits from base search engine class
- `search.base.ImageResult`: Data structure for search results
- `utils.log_config`: Provides structured logging capabilities
- `config.settings.DEFAULT_HEADERS`: Default HTTP headers for requests

### 4.2 External Dependencies
- `requests`: HTTP library for making Google Images requests
- `re`: Regular expressions for parsing HTML content
- `urllib.parse`: URL encoding and manipulation
- Standard Python libraries: `typing`, `__future__`

## 5. Error Handling and Fault Tolerance

### 5.1 HTTP Error Handling
- Handle HTTP request timeouts with appropriate error logging
- Raise HTTP exceptions for non-success status codes
- Return empty results on HTTP errors to prevent pipeline disruption

### 5.2 Response Validation
- Check response size and return empty results if below threshold (50KB)
- Handle cases where HTML parsing yields no results
- Gracefully handle malformed HTML or unexpected response formats

### 5.3 Fallback Mechanisms
- Implement dual parsing methods for robustness
- Use secondary regex pattern when primary method yields few results
- Continue processing despite individual URL parsing failures

## 6. Performance Criteria

### 6.1 Response Time Targets
- HTTP request completion: < 15 seconds (configured timeout)
- HTML parsing and URL extraction: < 100ms for typical responses
- Total search execution: < 200ms for normal operation

### 6.2 Resource Usage
- Memory: Proportional to HTML response size plus result list
- Network: Single HTTP request per search operation
- CPU: Moderate for HTML parsing and regex operations

### 6.3 Scalability Considerations
- Inherits thread safety from base class
- Connection reuse through thread-local session pooling
- Configurable timeouts preventing resource exhaustion

## 7. Security Considerations

### 7.1 Input Sanitization
- Properly encode search queries in URLs
- Validate and clean extracted URLs before returning
- Treat all external content as untrusted

### 7.2 Secure Communication
- Use HTTPS for all Google Images requests
- Validate SSL certificates in HTTP responses
- Configure secure HTTP headers through base class

### 7.3 Content Filtering
- Block domains known to host inappropriate content
- Filter out URLs matching patterns for low-quality images
- Prevent downloading of non-image content

## 8. Testing Requirements

### 8.1 Unit Tests
- Verify URL construction with various query inputs
- Test URL cleaning functions with different encoding scenarios
- Validate image filtering rules with sample URLs
- Check dimension filtering with various width/height combinations
- Test sorting algorithm with mixed dimension results

### 8.2 Integration Tests
- Validate actual Google Images search functionality
- Test response size validation with mocked small responses
- Verify dual parsing method fallback behavior
- Confirm proper integration with base class circuit breaker

### 8.3 Mocking Strategy
- Mock HTTP responses to test parsing logic without external dependencies
- Simulate various HTML response formats to test robustness
- Control response sizes to test validation logic
- Mock time delays to test timeout handling

## 9. Integration Points

### 9.1 Base Search Engine Integration
- Extends `BaseSearchEngine` to inherit circuit breaker and rate limiting
- Overrides `search` method to implement Google-specific logic
- Uses base class session property for HTTP requests

### 9.2 Search Manager Integration
- Registered in `ENGINE_REGISTRY` for dynamic instantiation
- Called by `SearchManager` as part of distributed search operations
- Contributes results to combined search result set

### 9.3 Logging Integration
- Uses structured logging for search operation tracing
- Logs debug information for query processing
- Reports result counts for monitoring and optimization

## 10. Implementation Details

### 10.1 Class Structure
```python
class GoogleEngine(BaseSearchEngine):
    name = "google"
    
    def search(self, query: str, max_results: int = 50) -> List[ImageResult]:
        # Construct search URL
        # Execute HTTP request
        # Parse HTML response with dual methods
        # Filter and sort results
        # Return ImageResult list
    
    @staticmethod
    def _clean(url: str) -> str:
        # Clean escaped characters and trailing punctuation
    
    @staticmethod
    def _valid(url: str) -> bool:
        # Apply domain and pattern filtering rules
```

### 10.2 Parsing Methods
- Primary method: Regex extraction of structured JSON-like data with dimensions
- Secondary method: General regex pattern matching for URLs
- Both methods apply the same filtering and cleaning logic

### 10.3 Filtering Logic
- Domain-based blocking using frozen set for performance
- Pattern-based filtering using frozen set of exclusion patterns
- Dimension filtering requiring minimum 300x300 pixel size
- Duplicate URL detection using set-based tracking