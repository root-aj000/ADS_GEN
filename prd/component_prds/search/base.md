# Search Engine Base Component PRD

## 1. Purpose and Scope

### 1.1 Component Purpose
The `BaseSearchEngine` class provides an abstract foundation for all search engine implementations in the Ad Generator system. It defines a standardized interface for image searching while implementing common functionality such as circuit breaker protection, rate limiting, and connection pooling.

### 1.2 Position in Architecture
This component serves as the foundational abstraction layer in the search subsystem, located between the search manager orchestrator and concrete search engine implementations (Google, Bing, DuckDuckGo). It enforces architectural consistency and implements shared operational concerns.

### 1.3 Key Responsibilities
- Define the standard search interface contract for all search engines
- Implement circuit breaker pattern for fault tolerance
- Enforce rate limiting to prevent service abuse
- Manage thread-local HTTP sessions for efficient connection pooling
- Provide a safety wrapper for search operations with automatic error handling

## 2. Functional Requirements

### 2.1 Abstract Interface Definition
- Define the `search(query: str, max_results: int)` abstract method that all subclasses must implement
- Establish the `ImageResult` data structure for representing search results
- Provide a consistent initialization interface accepting `SearchConfig`

### 2.2 Circuit Breaker Implementation
- Implement automatic failure detection and tracking
- Provide configurable failure thresholds via `SearchConfig`
- Enable automatic cooldown periods after circuit opening
- Prevent further requests when circuit is open to protect downstream services

### 2.3 Rate Limiting
- Enforce configurable request rate limits per second
- Implement blocking delay mechanism to respect rate constraints
- Provide per-engine rate limiting based on configuration

### 2.4 Connection Management
- Implement thread-local HTTP session storage for connection reuse
- Configure default HTTP headers for all requests
- Manage session lifecycle automatically

### 2.5 Safe Search Wrapper
- Provide `safe_search` method wrapping actual search with operational safeguards
- Implement automatic success/failure recording for circuit breaker
- Handle exceptions gracefully and return empty results on failure

## 3. Input/Output Specifications

### 3.1 Inputs
- `query`: String search term for finding product images
- `max_results`: Integer maximum number of results to return
- `SearchConfig`: Configuration object containing rate limits, circuit breaker settings, and engine parameters

### 3.2 Outputs
- List of `ImageResult` objects containing:
  - `url`: String URL of the image resource
  - `source`: String identifier of the search engine
  - `title`: Optional string title of the image/page
  - `width`: Optional integer pixel width
  - `height`: Optional integer pixel height
- Empty list on errors or when circuit breaker is open

### 3.3 Data Structures
```python
@dataclass
class ImageResult:
    url: str
    source: str
    title: str = ""
    width: int = 0
    height: int = 0
```

## 4. Dependencies

### 4.1 Internal Dependencies
- `config.settings.SearchConfig`: Provides configuration parameters for rate limiting and circuit breaker behavior
- `utils.concurrency.CircuitBreaker`: Implements the circuit breaker pattern
- `utils.concurrency.RateLimiter`: Implements request rate limiting
- `utils.log_config`: Provides structured logging capabilities

### 4.2 External Dependencies
- `requests`: HTTP library for making search engine API calls
- Standard Python libraries: `threading`, `dataclasses`, `typing`

## 5. Error Handling and Fault Tolerance

### 5.1 Exception Handling
- Wrap all search operations in try/catch blocks
- Convert all exceptions to empty result lists to prevent pipeline interruption
- Log all exceptions with appropriate context for debugging

### 5.2 Circuit Breaker Protection
- Track success/failure of search operations
- Open circuit after configured failure threshold
- Automatically close circuit after cooldown period
- Return empty results immediately when circuit is open

### 5.3 Retry Strategy
- No explicit retry mechanism implemented (handled at higher levels)
- Delegate retry responsibility to callers for flexibility

## 6. Performance Criteria

### 6.1 Response Time Targets
- Session creation: < 1ms
- Circuit breaker checks: < 0.1ms
- Rate limiter waits: Configurable, typically < 100ms

### 6.2 Resource Usage
- HTTP connections: Reused via thread-local session pooling
- Memory: Minimal overhead per instance
- CPU: Negligible for circuit breaker/rate limiter operations

### 6.3 Scalability Considerations
- Thread-safe design enabling concurrent usage
- Efficient connection reuse minimizing resource consumption
- Configurable limits preventing resource exhaustion

## 7. Security Considerations

### 7.1 Input Validation
- No direct input validation (handled at higher levels)
- URLs returned by search engines should be treated as untrusted

### 7.2 Secure Communication
- Use HTTPS for all search engine communications
- Configure secure HTTP headers in session objects
- Validate SSL certificates in HTTP requests

### 7.3 Access Control
- No access control mechanisms implemented in this layer
- Relies on higher-level authorization mechanisms

## 8. Testing Requirements

### 8.1 Unit Tests
- Verify abstract method enforcement raises NotImplementedError
- Test circuit breaker transitions (closed→open→half-open→closed)
- Validate rate limiter behavior under various load conditions
- Confirm thread-local session isolation between threads
- Test safe_search wrapper exception handling

### 8.2 Integration Tests
- Validate proper interaction with concrete search engine implementations
- Test circuit breaker behavior with actual failing search engines
- Verify rate limiting effectiveness across multiple concurrent requests

### 8.3 Mocking Strategy
- Mock HTTP responses for testing search engine interactions
- Simulate network failures to test circuit breaker behavior
- Control time progression for testing rate limiter accuracy

## 9. Integration Points

### 9.1 Search Manager Integration
- Instantiated by `SearchManager` for each enabled search engine
- Called by `SearchManager.search()` method for distributed searching
- Shares `ThreadSafeSet` for cross-engine duplicate detection

### 9.2 Concrete Search Engine Implementations
- Inherited by `GoogleEngine`, `BingEngine`, and `DuckDuckGoEngine`
- Provides base functionality reducing implementation complexity
- Enforces consistent operational behavior across all engines

### 9.3 Configuration Integration
- Consumes `SearchConfig` for all operational parameters
- Allows runtime configuration of circuit breaker and rate limiting
- Supports engine-specific configuration overrides

## 10. Implementation Details

### 10.1 Class Structure
```python
class BaseSearchEngine:
    name: str = "base"
    
    def __init__(self, cfg: SearchConfig) -> None:
        # Initialize circuit breaker and rate limiter
        # Set up thread-local storage
    
    @property
    def session(self) -> requests.Session:
        # Return thread-local session with connection pooling
    
    def search(self, query: str, max_results: int = 50) -> List[ImageResult]:
        # Abstract method to be implemented by subclasses
    
    def safe_search(self, query: str, max_results: int = 50) -> List[ImageResult]:
        # Wrapper with circuit breaker and rate limiting
```

### 10.2 Thread Safety
- Uses thread-local storage for HTTP sessions ensuring isolation
- Circuit breaker and rate limiter instances are thread-safe
- No mutable shared state between threads

### 10.3 Performance Optimizations
- HTTP session reuse through thread-local storage
- Lazy session initialization only when needed
- Efficient circuit breaker state management