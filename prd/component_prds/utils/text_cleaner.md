# Text Cleaner Utilities Component PRD

## 1. Purpose and Scope

### 1.1 Component Purpose
The text cleaner utilities module provides specialized text processing functions for cleaning and normalizing search queries and product descriptions in the ad generation system. It implements intelligent algorithms for fixing malformed text, removing search engine artifacts, and preparing textual data for effective image searching and ad composition.

### 1.2 Position in Architecture
This component serves as the text preprocessing layer in the system, positioned to sanitize and optimize textual input data before it's used for search queries or ad content generation. It acts as a utility library that ensures consistent text quality and format across all modules that consume textual data.

### 1.3 Key Responsibilities
- Fix character-separated text where spaces incorrectly separate letters
- Remove search engine junk suffixes and artifacts from queries
- Normalize whitespace and special characters for consistency
- Validate query text for meaningful content
- Provide configurable text cleaning parameters

## 2. Functional Requirements

### 2.1 Spaced Text Correction
- Detect and fix text where individual characters are separated by spaces
- Reconstruct words from character-by-character spaced formats
- Preserve legitimate multi-word phrases with normal spacing
- Handle varying degrees of text fragmentation
- Maintain original text meaning during reconstruction

### 2.2 Junk Suffix Removal
- Identify and remove search engine artifacts (filetype, site:, etc.)
- Support configurable suffix patterns for removal
- Handle case-insensitive pattern matching
- Preserve legitimate query content while removing artifacts
- Apply multiple suffix removal in appropriate order

### 2.3 Text Normalization
- Remove special characters that interfere with search effectiveness
- Normalize whitespace to single spaces between words
- Preserve meaningful punctuation and hyphens
- Convert text to consistent internal representation
- Support configurable word count limiting

### 2.4 Query Validation
- Check text validity for search query usage
- Filter out meaningless or placeholder values
- Apply configurable ignore value lists
- Validate minimum text length requirements
- Enable consistent query quality across system

## 3. Input/Output Specifications

### 3.1 Inputs
- `text`: String input text for cleaning and normalization
- `suffixes`: Tuple of junk suffix patterns for removal
- `max_words`: Integer maximum word count limit (0 = unlimited)
- `ignore_values`: Tuple of values to consider invalid
- Character-separated and normally formatted text

### 3.2 Outputs
- `str`: Cleaned and normalized text strings
- `bool`: Validity status for query validation
- Consistently formatted text ready for search or composition
- Removed artifacts and normalized special characters

### 3.3 Configuration Parameters
- Suffix patterns: Search engine artifacts to remove
- Ignore values: Text values considered invalid
- Word limits: Maximum words to preserve in queries
- Special character handling: Rules for punctuation removal
- Whitespace normalization: Standards for space handling

## 4. Dependencies

### 4.1 Internal Dependencies
- `utils.log_config`: Structured logging for processing events
- Standard Python regular expressions module
- Standard Python string and typing modules

### 4.2 External Dependencies
- Built-in Python standard library modules

## 5. Error Handling and Fault Tolerance

### 5.1 Text Processing Resilience
- Handle malformed or unexpected text input gracefully
- Continue processing with best-effort cleaning on errors
- Log processing issues for diagnostic purposes
- Apply fallback behaviors for problematic text
- Prevent text processing failures from disrupting operations

### 5.2 Data Validation
- Validate input text for processing suitability
- Handle None and empty string inputs appropriately
- Apply type checking for parameter validation
- Prevent crashes from unexpected data formats
- Maintain data integrity during transformation

### 5.3 Resource Protection
- Apply appropriate limits to prevent resource exhaustion
- Handle large text inputs efficiently
- Manage memory usage during text processing
- Prevent regular expression catastrophic backtracking
- Apply timeouts to prevent hanging operations

## 6. Performance Criteria

### 6.1 Response Time Targets
- Spaced text correction: < 1ms for typical queries
- Suffix removal: < 500μs per query
- Text normalization: < 200μs per query
- Query validation: < 100μs per query
- Complete cleaning pipeline: < 2ms for average queries

### 6.2 Resource Usage
- Memory: Minimal for text processing operations
- CPU: Low for regular expression and string operations
- Disk: No persistent storage requirements
- Network: No external dependencies
- Objects: Lightweight string manipulation

### 6.3 Scalability Considerations
- Efficient algorithms for common text operations
- Minimal memory allocation during processing
- Configurable complexity for performance tuning
- Thread-safe design enabling concurrent usage
- Linear scaling with input text size

## 7. Security Considerations

### 7.1 Input Validation
- Validate text inputs to prevent injection attacks
- Apply appropriate length limits to prevent DoS
- Sanitize inputs to prevent regex injection
- Check character encodings for consistency
- Handle international text appropriately

### 7.2 Regular Expression Safety
- Prevent catastrophic backtracking in regex patterns
- Apply appropriate regex compilation and caching
- Limit regex complexity to prevent performance issues
- Validate regex patterns for security implications
- Use safe regex practices for text processing

### 7.3 Data Integrity
- Preserve text meaning during cleaning operations
- Prevent accidental data loss during processing
- Maintain consistent text encoding
- Handle edge cases in text transformation
- Validate output quality for correctness

## 8. Testing Requirements

### 8.1 Unit Tests
- Verify spaced text correction with various input patterns
- Test suffix removal with different artifact types
- Validate text normalization with special characters
- Check query validation with various input values
- Test word limiting with different count settings
- Verify handling of edge cases and empty inputs

### 8.2 Integration Tests
- Validate actual text cleaning with real query data
- Test performance characteristics with large inputs
- Confirm proper interaction with configuration system
- Verify logging integration for processing events
- Test error handling with malformed inputs

### 8.3 Mocking Strategy
- Mock text inputs for consistent testing scenarios
- Simulate different text patterns for validation
- Control configuration parameters for boundary testing
- Mock timing to test performance characteristics
- Simulate error conditions for resilience testing

## 9. Integration Points

### 9.1 System-Wide Integration
- Used by search components for query preparation
- Integrated with pipeline for data cleaning
- Applied to CSV input processing for quality assurance
- Utilized in ad composition for text optimization
- Employed in configuration for value validation

### 9.2 Data Processing Integration
- Processes raw text from CSV input files
- Cleans search queries before engine submission
- Normalizes product descriptions for consistency
- Prepares text for AI processing and analysis
- Ensures quality input for downstream operations

### 9.3 Configuration Integration
- Consumes suffix patterns from configuration
- Applies ignore value lists from settings
- Supports runtime adjustment of cleaning parameters
- Enables operational control of text quality
- Allows customization for different data sources

## 10. Implementation Details

### 10.1 Function Structure
```python
def clean_spaced_text(text: str) -> str:
    """Fix text where characters are separated by spaces."""

def _reconstruct_spaced_text(text: str) -> str:
    """Reconstruct from character-by-character format."""

def strip_junk_suffixes(text: str, suffixes: Tuple[str, ...]) -> str:
    """Remove search-engine junk from the end of queries."""

def clean_query(
    text: str,
    max_words: int = 0,
    strip_suffixes: Optional[Tuple[str, ...]] = None,
) -> str:
    """Clean and normalize a search query."""

def is_valid_query(text: str, ignore_values: tuple) -> bool:
    """Check if a query value is valid."""
```

### 10.2 Text Cleaning Pipeline
1. Spaced Text Detection: Analyze character spacing patterns
2. Word Reconstruction: Rebuild words from separated characters
3. Junk Removal: Strip search engine artifacts and suffixes
4. Character Filtering: Remove special characters that interfere
5. Whitespace Normalization: Standardize space usage
6. Word Limiting: Apply maximum word count when configured
7. Quality Validation: Check result for meaningful content

### 10.3 Implementation Details
- Ratio-based detection for spaced text identification
- Regular expression patterns for suffix removal
- Character class filtering for special character removal
- Whitespace consolidation for consistent formatting
- Configurable word counting with preservation logic
- Case-insensitive pattern matching for robustness
- Efficient string operations for performance
- Comprehensive logging for operational visibility