# Search Manager Component PRD

## 1. Purpose and Scope

### 1.1 Component Purpose
The `SearchManager` class orchestrates searches across multiple search engines with priority ordering, circuit breaker protection, and cross-engine deduplication. It provides a unified interface for distributed image searching while managing operational concerns like engine selection, result aggregation, and duplicate elimination.

### 1.2 Position in Architecture
This component serves as the central orchestrator in the search subsystem, positioned between the core pipeline and individual search engine adapters. It coordinates the execution of searches across multiple engines and aggregates results into a unified response.

### 1.3 Key Responsibilities
- Manage instantiation and lifecycle of search engine adapters
- Orchestrate distributed searches across multiple engines with priority ordering
- Implement cross-engine duplicate detection and elimination
- Enforce configurable result thresholds for early termination
- Coordinate inter-engine delays to optimize resource utilization

## 2. Functional Requirements

### 2.1 Engine Management
- Dynamically instantiate enabled search engines based on configuration
- Maintain registry mapping of engine names to implementation classes
- Support addition of new search engine implementations through registration
- Share downloaded image hash tracking across all engine instances

### 2.2 Distributed Search Orchestration
- Execute searches across engines in priority order defined by configuration
- Implement early termination when sufficient results are obtained
- Apply configurable delays between engine executions
- Aggregate results from multiple engines into unified result set

### 2.3 Duplicate Elimination
- Track downloaded image hashes to prevent cross-row duplication
- Eliminate URL duplicates across engines during result aggregation
- Maintain thread-safe shared state for cross-engine deduplication

### 2.4 Result Threshold Management
- Monitor accumulated result count during distributed search
- Terminate search early when minimum result threshold is met
- Continue with remaining engines if threshold not yet reached
- Apply final limiting to respect maximum result count

## 3. Input/Output Specifications

### 3.1 Inputs
- `query`: String search term for finding product images
- `max_results`: Integer maximum number of results to return (default: 100)
- `SearchConfig`: Configuration object containing engine priorities, delays, and thresholds

### 3.2 Outputs
- List of `ImageResult` objects aggregated from all engines
- Results ordered by engine priority (not individual relevance)
- Empty list on errors or when all engines fail
- Limited to specified maximum result count

### 3.3 Configuration Parameters
- `priority`: Ordered list of engine names determining search execution order
- `min_results_fallback`: Minimum result count before early termination
- `inter_engine_delay`: Delay between engine executions
- Engine-specific configurations passed to individual engine instances

## 4. Dependencies

### 4.1 Internal Dependencies
- `config.settings.SearchConfig`: Provides configuration parameters
- `search.base.BaseSearchEngine`: Common interface for all search engines
- `search.base.ImageResult`: Data structure for search results
- `search.google_engine.GoogleEngine`: Google search implementation
- `search.bing_engine.BingEngine`: Bing search implementation
- `search.duckduckgo_engine.DuckDuckGoEngine`: DuckDuckGo search implementation
- `utils.concurrency.ThreadSafeSet`: Thread-safe set for hash tracking
- `utils.log_config`: Provides structured logging capabilities

### 4.2 External Dependencies
- Standard Python libraries: `typing`, `time`, `__future__`

## 5. Error Handling and Fault Tolerance

### 5.1 Engine Failure Resilience
- Continue with remaining engines when individual engines fail
- Handle missing engine implementations gracefully
- Log engine failures for diagnostic purposes
- Return partial results when some engines succeed

### 5.2 Configuration Validation
- Validate engine names against registered implementations
- Handle empty or invalid priority lists gracefully
- Continue with valid engines despite configuration issues

### 5.3 Result Aggregation Safety
- Handle empty result sets from individual engines
- Continue aggregation despite individual engine failures
- Apply result limiting safely regardless of input size

## 6. Performance Criteria

### 6.1 Response Time Targets
- Individual engine execution: Dependent on engine implementation
- Inter-engine delays: Configurable, typically 100-500ms
- Total distributed search: Sum of engine times plus delays
- Result aggregation: < 50ms for typical result sets

### 6.2 Resource Usage
- Memory: Proportional to aggregated result set size
- Network: Multiple HTTP requests across engines
- CPU: Minimal for result aggregation and deduplication
- Threads: Shared across engines with thread-safe operations

### 6.3 Scalability Considerations
- Thread-safe design enabling concurrent usage
- Efficient duplicate elimination using hash sets
- Configurable delays preventing resource exhaustion
- Early termination optimizing for sufficient results

## 7. Security Considerations

### 7.1 Input Validation
- No direct input validation (handled at higher levels)
- Trust engine implementations to handle query sanitization
- Validate result URLs before further processing

### 7.2 Secure Communication
- Rely on engine implementations for secure HTTP communication
- Ensure all engine connections use HTTPS
- Validate SSL certificates through engine implementations

### 7.3 Content Filtering
- Depend on engine implementations for content appropriateness
- Share downloaded hash tracking to prevent redundant downloads
- Treat all external image URLs as untrusted

## 8. Testing Requirements

### 8.1 Unit Tests
- Verify engine instantiation from configuration
- Test priority ordering in search execution
- Validate duplicate elimination across engines
- Check early termination with threshold configuration
- Test inter-engine delay implementation
- Verify result limiting with various input sizes

### 8.2 Integration Tests
- Validate distributed search across multiple engines
- Test failure resilience with failing engine mocks
- Verify cross-engine deduplication effectiveness
- Confirm early termination behavior with threshold settings
- Test configuration edge cases and error conditions

### 8.3 Mocking Strategy
- Mock individual engine implementations to isolate manager logic
- Simulate various result set sizes from engines
- Control timing to test delay behavior
- Simulate engine failures to test resilience

## 9. Integration Points

### 9.1 Core Pipeline Integration
- Called by `AdPipeline` during image acquisition phase
- Receives search queries derived from product data
- Returns aggregated results to pipeline for processing

### 9.2 Search Engine Integration
- Instantiates all enabled engines from `ENGINE_REGISTRY`
- Calls `safe_search` method on each engine for protected execution
- Shares `downloaded_hashes` for cross-engine deduplication

### 9.3 Configuration Integration
- Consumes `SearchConfig` for all operational parameters
- Dynamically configures engines based on enabled list
- Applies timing and threshold parameters from configuration

## 10. Implementation Details

### 10.1 Class Structure
```python
class SearchManager:
    def __init__(self, cfg: SearchConfig) -> None:
        # Initialize engines from configuration
        # Set up shared downloaded hash tracking
    
    def search(self, query: str, max_results: int = 100) -> List[ImageResult]:
        # Execute distributed search across engines
        # Aggregate and deduplicate results
        # Apply early termination and final limiting
```

### 10.2 Engine Registry Pattern
- Dictionary mapping engine names to implementation classes
- Dynamic instantiation based on configuration
- Support for extending with new engine types

### 10.3 Search Orchestration Flow
1. Initialize empty result list and URL tracking set
2. Iterate through engines in priority order
3. Execute search on each engine with safe wrapper
4. Add unique results to combined list
5. Check threshold for early termination
6. Apply inter-engine delays
7. Return limited final result set