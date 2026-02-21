# Image Cache Component PRD

## 1. Purpose and Scope

### 1.1 Component Purpose
The `ImageCache` class provides persistent, thread-safe caching of downloaded images using SQLite as the backing store. It enables reuse of previously downloaded images for identical search queries across different pipeline runs, significantly reducing network usage and processing time while maintaining data consistency.

### 1.2 Position in Architecture
This component serves as the persistence layer in the imaging subsystem, positioned between image acquisition and storage. It integrates with the image downloader to provide transparent caching functionality that accelerates repeated operations and reduces redundant processing.

### 1.3 Key Responsibilities
- Store and retrieve image metadata and file references using SQLite
- Implement thread-safe concurrent access through connection pooling
- Provide query-based caching with normalized key generation
- Validate cached file existence and integrity
- Track cache usage statistics for performance monitoring
- Support cache management operations (clear, statistics)

## 2. Functional Requirements

### 2.1 Persistent Storage
- Use SQLite database for reliable metadata storage
- Implement schema versioning for future compatibility
- Support atomic operations for data consistency
- Enable WAL (Write-Ahead Logging) for concurrent access
- Apply appropriate synchronization modes for performance

### 2.2 Query-Based Caching
- Generate normalized query hashes for consistent key generation
- Store complete image metadata including dimensions and source
- Maintain file path references for quick retrieval
- Track source URLs for attribution and debugging
- Record creation timestamps for cache aging analysis

### 2.3 Concurrent Access
- Implement thread-local database connections for isolation
- Use connection pooling to minimize overhead
- Apply appropriate locking for schema initialization
- Support concurrent read/write operations safely
- Handle connection timeouts gracefully

### 2.4 Cache Validation
- Verify file existence before returning cached entries
- Automatically remove stale entries with missing files
- Update hit counters for usage tracking
- Apply query normalization to maximize cache hits
- Handle edge cases like empty or corrupted cache entries

### 2.5 Cache Management
- Provide statistics on cache size, usage, and effectiveness
- Support cache clearing for maintenance operations
- Enable performance monitoring through hit/miss tracking
- Implement efficient indexing for fast lookups
- Support cache growth monitoring and capacity planning

## 3. Input/Output Specifications

### 3.1 Inputs
- `db_path`: Path to SQLite database file
- `query`: Search query string for cache operations
- Image metadata for storage operations:
  - `source_url`: Original image source URL
  - `file_path`: Path to stored image file
  - `file_hash`: Content hash for deduplication
  - `width`: Image width in pixels
  - `height`: Image height in pixels
  - `file_size`: File size in bytes
  - `source_engine`: Search engine that provided the image

### 3.2 Outputs
- `Optional[dict]`: Cached entry data or None if not found
- `None`: For put and management operations
- Statistics dictionary containing:
  - `total`: Total number of cached entries
  - `total_hits`: Cumulative cache hit count
  - `total_bytes`: Total storage consumed by cached images

### 3.3 Database Schema
- `image_cache` table with columns:
  - `query_hash`: Primary key, normalized query hash
  - `query`: Original search query text
  - `source_url`: Source image URL
  - `file_path`: Path to cached image file
  - `file_hash`: Content hash for deduplication
  - `width`: Image width in pixels
  - `height`: Image height in pixels
  - `file_size`: File size in bytes
  - `source_engine`: Search engine identifier
  - `created_at`: Timestamp of cache entry creation
  - `hit_count`: Number of times entry was accessed

## 4. Dependencies

### 4.1 Internal Dependencies
- `utils.log_config`: Structured logging for cache operations

### 4.2 External Dependencies
- `sqlite3`: SQLite database interface
- `hashlib`: Cryptographic hashing for query normalization
- `pathlib`: Path manipulation for file operations
- Standard Python libraries: `threading`, `time`

## 5. Error Handling and Fault Tolerance

### 5.1 Database Resilience
- Handle database connection failures gracefully
- Implement retry logic for transient database errors
- Continue operation with cache disabled on persistent failures
- Log detailed error information for debugging
- Apply timeouts to prevent hanging operations

### 5.2 Data Consistency
- Use transactions for atomic operations
- Validate data integrity before returning cached entries
- Handle corrupted or inconsistent cache entries
- Implement automatic cleanup of stale entries
- Apply appropriate isolation levels for concurrent access

### 5.3 File System Protection
- Verify file existence before returning cache references
- Automatically remove entries with missing files
- Handle file permission errors appropriately
- Apply path validation to prevent directory traversal
- Manage disk space usage through monitoring

## 6. Performance Criteria

### 6.1 Response Time Targets
- Cache hit lookup: < 10ms
- Cache miss lookup: < 5ms
- Cache put operation: < 15ms
- File existence validation: < 5ms
- Statistics retrieval: < 5ms
- Cache clearing: < 100ms

### 6.2 Resource Usage
- Memory: Minimal, primarily SQLite page cache
- Disk: Proportional to database size and indexed data
- CPU: Low for query operations, moderate for hashing
- Connections: Thread-local pooling with minimal overhead

### 6.3 Scalability Considerations
- SQLite's single-file design simplifies deployment
- WAL mode enables high-concurrency read operations
- Indexing optimizes query performance
- Connection pooling minimizes overhead
- Efficient query normalization maximizes hit rates

## 7. Security Considerations

### 7.1 Data Integrity
- Use parameterized queries to prevent SQL injection
- Validate input data before database operations
- Apply appropriate file permissions for database files
- Implement proper error handling without information disclosure
- Use cryptographic hashing for query normalization

### 7.2 Access Control
- Limit database file permissions to application user
- Validate file paths to prevent directory traversal
- Apply timeouts to prevent resource exhaustion
- Log security-relevant events for audit purposes
- Sanitize inputs to prevent injection attacks

### 7.3 Privacy Protection
- Store only necessary metadata for caching
- Avoid storing sensitive query information
- Apply appropriate data retention policies
- Implement secure deletion when required
- Minimize data exposure in logs

## 8. Testing Requirements

### 8.1 Unit Tests
- Verify query hashing and normalization logic
- Test cache hit and miss scenarios
- Validate file existence checking
- Check automatic stale entry removal
- Test concurrent access with multiple threads
- Verify statistics collection accuracy
- Check cache clearing functionality
- Test error handling for database failures

### 8.2 Integration Tests
- Validate actual SQLite database operations
- Test concurrent access with real threads
- Verify file system integration
- Confirm proper indexing performance
- Test cache effectiveness with repeated queries
- Validate schema creation and migration

### 8.3 Mocking Strategy
- Mock file system operations for isolated testing
- Simulate database errors for failure handling tests
- Control timing to test concurrent access scenarios
- Mock hashing for consistent test results

## 9. Integration Points

### 9.1 Image Downloader Integration
- Called by `ImageDownloader` before initiating downloads
- Receives search queries for cache lookup
- Returns cached image metadata when available
- Accepts image metadata for cache storage
- Integrates with downloader's performance optimization

### 9.2 File System Integration
- Manages file paths for cached images
- Validates file existence and accessibility
- Coordinates with downloader's file storage
- Handles file system errors appropriately
- Tracks disk space usage for monitoring

### 9.3 Logging Integration
- Uses structured logging for cache operations
- Logs cache hit/miss statistics
- Records errors and warnings for monitoring
- Tracks performance metrics for optimization
- Reports maintenance operations

## 10. Implementation Details

### 10.1 Class Structure
```python
class ImageCache:
    def __init__(self, db_path: Path) -> None:
        # Initialize database connection and schema
    
    @property
    def _conn(self) -> sqlite3.Connection:
        # Thread-local connection management
    
    def _ensure_schema(self) -> None:
        # Database schema initialization with locking
    
    @staticmethod
    def _hash_query(query: str) -> str:
        # Query normalization and hashing
    
    def get(self, query: str) -> Optional[dict]:
        # Cache lookup with validation
    
    def put(self, ...) -> None:
        # Cache storage with metadata
    
    def stats(self) -> dict:
        # Statistics retrieval
    
    def clear(self) -> None:
        # Cache clearing operation
```

### 10.2 Database Design
- Single table design for simplicity and performance
- Primary key indexing on query hash for fast lookups
- Additional indexes on frequently queried fields
- WAL mode for concurrent read/write operations
- Automatic cleanup of stale entries during access

### 10.3 Caching Strategy
1. Query Normalization: Standardize text for consistent hashing
2. Cache Lookup: Check for existing entries with matching hash
3. File Validation: Verify referenced file still exists
4. Hit Tracking: Update access counters for statistics
5. Cache Storage: Insert or update metadata after successful download
6. Stale Detection: Remove entries with missing files automatically
7. Performance Monitoring: Track hit rates and access patterns