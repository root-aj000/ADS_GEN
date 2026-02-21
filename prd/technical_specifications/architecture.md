# Technical Specification: System Architecture
## Ad Generator System

---

## 1. Overview

This document provides a comprehensive technical specification for the Ad Generator system architecture, detailing the design principles, component interactions, data flow, and implementation guidelines.

---

## 2. Architecture Principles

### 2.1 Modularity
The system is designed with a modular architecture where each component has a single responsibility and well-defined interfaces. This enables:
- Independent development and testing
- Easy replacement or upgrading of components
- Clear separation of concerns

### 2.2 Loose Coupling
Components interact through well-defined interfaces rather than direct dependencies, enabling:
- Flexible system configuration
- Easier maintenance and debugging
- Better testability

### 2.3 High Cohesion
Each module focuses on a specific domain, ensuring:
- Clear functionality boundaries
- Reduced complexity within modules
- Improved code organization

### 2.4 Resilience
The system incorporates multiple resilience patterns:
- Circuit breakers for external dependencies
- Retry mechanisms for transient failures
- Graceful degradation when components fail
- Fallback strategies for critical operations

---

## 3. System Architecture

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AD GENERATOR ARCHITECTURE                          │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────┐
                              │    main.py      │
                              │   (Entry Point) │
                              └────────┬────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │   AppConfig     │
                              │  (Settings)     │
                              └────────┬────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AD PIPELINE                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         THREAD POOL                                   │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │   │
│  │  │   Worker 1  │ │   Worker 2  │ │   Worker 3  │ │   Worker N  │    │   │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘    │   │
│  │         │               │               │               │           │   │
│  │         └───────────────┴───────────────┴───────────────┘           │   │
│  │                                 │                                   │   │
│  └─────────────────────────────────┼───────────────────────────────────┘   │
│                                    │                                       │
│                    ┌───────────────┼───────────────┐                      │
│                    │               │               │                      │
│                    ▼               ▼               ▼                      │
│           ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│           │   Search     │ │   Imaging    │ │   Compositor │             │
│           │   Manager    │ │   Pipeline   │ │              │             │
│           └──────────────┘ └──────────────┘ └──────────────┘             │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         SHARED STATE                                  │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                 │  │
│  │  │ ImageCache   │ │ ThreadSafeSet│ │ ProgressMgr  │                 │  │
│  │  │  (SQLite)    │ │   (Hashes)   │ │  (SQLite)    │                 │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘                 │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Layered Architecture

The system follows a layered architecture with the following layers:

1. **Presentation Layer** (CLI Interface)
   - Command-line argument parsing
   - User interaction and feedback

2. **Application Layer** (Core Pipeline)
   - Workflow orchestration
   - Business logic implementation
   - Error handling and recovery

3. **Service Layer** (Domain Services)
   - Search engine coordination
   - Image processing services
   - Notification services

4. **Data Access Layer** (Persistence)
   - Database interactions
   - File system operations
   - Cache management

5. **Infrastructure Layer** (External Systems)
   - Search engine APIs
   - AI model interfaces
   - Third-party services

---

## 4. Component Design

### 4.1 Configuration Layer

#### 4.1.1 Purpose
Centralize all application settings and provide type-safe configuration objects.

#### 4.1.2 Key Components
- `AppConfig`: Main configuration class aggregating all settings
- `PathConfig`: File system paths
- `SearchConfig`: Search engine settings
- `ImageQualityConfig`: Image validation parameters
- `BackgroundRemovalConfig`: Background removal settings
- `PipelineConfig`: Threading and processing parameters
- `NotificationConfig`: Notification settings
- `QueryConfig`: CSV column mapping and query settings

#### 4.1.3 Design Patterns
- Immutable dataclasses for configuration
- Factory pattern for default configurations
- Validation at startup

### 4.2 Pipeline Layer

#### 4.2.1 Purpose
Orchestrate the entire advertisement generation workflow.

#### 4.2.2 Key Components
- `AdPipeline`: Main orchestrator
- `Stats`: Processing statistics collector
- `build_query`: Query construction utility

#### 4.2.3 Design Patterns
- Thread pool pattern for concurrent processing
- Observer pattern for progress tracking
- Strategy pattern for processing variations

### 4.3 Search Layer

#### 4.3.1 Purpose
Find relevant product images from multiple search engines.

#### 4.3.2 Key Components
- `SearchManager`: Coordinates multiple search engines
- `BaseSearchEngine`: Abstract base class
- `GoogleEngine`: Google Images search implementation
- `BingEngine`: Bing Images search implementation
- `DuckDuckGoEngine`: DuckDuckGo Images search implementation

#### 4.3.3 Design Patterns
- Strategy pattern for search engine implementations
- Factory pattern for engine instantiation
- Circuit breaker for resilience

### 4.4 Imaging Layer

#### 4.4.1 Purpose
Download, validate, process, and enhance product images.

#### 4.4.2 Key Components
- `ImageDownloader`: HTTP download and validation
- `ImageCache`: SQLite-based deduplication
- `ImageQualityScorer`: Multi-factor quality assessment
- `ImageVerifier`: CLIP/BLIP AI verification
- `BackgroundRemover`: rembg AI processing
- `FontManager`: Font loading and management

#### 4.4.3 Design Patterns
- Chain of responsibility for image processing pipeline
- Decorator pattern for verification
- Singleton pattern for AI models

### 4.5 Composition Layer

#### 4.5.1 Purpose
Create final advertisement images from processed product images.

#### 4.5.2 Key Components
- `AdCompositor`: Main composition engine
- `TemplateManager`: Ad layout templates
- `PlaceholderGenerator`: Fallback image generation

#### 4.5.3 Design Patterns
- Template method pattern for composition
- Builder pattern for complex layouts
- Factory pattern for template selection

### 4.6 Persistence Layer

#### 4.6.1 Purpose
Provide persistent storage for caching and progress tracking.

#### 4.6.2 Key Components
- `ImageCache`: Image deduplication cache
- `ProgressManager`: Processing progress tracker
- `HealthMonitor`: Engine health tracking

#### 4.6.3 Design Patterns
- Repository pattern for data access
- DAO pattern for database operations
- Observer pattern for health monitoring

### 4.7 Utility Layer

#### 4.7.1 Purpose
Provide shared utilities and cross-cutting concerns.

#### 4.7.2 Key Components
- `AtomicCounter`: Thread-safe counting
- `ThreadSafeSet`: Thread-safe deduplication
- `RateLimiter`: Request throttling
- `CircuitBreaker`: Fail-fast protection
- `@retry`: Automatic retry decorator
- `Logger`: Centralized logging

#### 4.7.3 Design Patterns
- Decorator pattern for retry logic
- Proxy pattern for rate limiting
- State pattern for circuit breaker

---

## 5. Data Flow

### 5.1 Overall Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA FLOW OVERVIEW                                  │
└─────────────────────────────────────────────────────────────────────────────┘

Input CSV → Query Builder → Image Cache → Search Engines → Image Downloader
    ↓           ↓              ↓              ↓                ↓
Progress   Clean Query    Cache Hit?    Search Results    Validate & Score
Tracker        ↑              ↓              ↓                ↓
    ↓          │         Cache Miss    Rank Results      Verify (CLIP/BLIP)
Output         │              ↓              ↓                ↓
CSV ←─────── Compositor ← Background ←──── Download ←────── Best Image
```

### 5.2 Detailed Processing Flow

For each product in the input CSV:

1. **Query Construction**
   - Extract product information from CSV row
   - Clean and normalize search query
   - Apply configured column priority

2. **Cache Check**
   - Generate query hash
   - Lookup in SQLite cache
   - Return cached image if found

3. **Image Search**
   - Execute search on primary engine
   - Fallback to secondary engines if needed
   - Apply rate limiting and circuit breakers

4. **Image Download**
   - Download candidate images
   - Validate file size and format
   - Check image dimensions and aspect ratio

5. **Quality Assessment**
   - Calculate multi-factor quality score
   - Assess visual content (not blank/monochrome)
   - Rank candidates by quality

6. **AI Verification**
   - Apply CLIP model for image-text matching
   - Generate BLIP caption for cross-check
   - Calculate combined verification score

7. **Background Removal**
   - Determine if background removal is needed
   - Apply rembg AI processing
   - Validate retention ratio

8. **Ad Composition**
   - Select appropriate template
   - Render product information
   - Apply branding elements
   - Generate final advertisement

9. **Persistence**
   - Save advertisement to disk
   - Update progress tracking
   - Update cache with new entry

---

## 6. Concurrency Model

### 6.1 Threading Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         THREADING MODEL                                     │
└─────────────────────────────────────────────────────────────────────────────┘

MainThread
    │
    ├─── setup_root() ─── Logging configuration
    │
    ├─── AppConfig() ─── Load configuration
    │
    └─── AdPipeline.run() ─── Start processing
              │
              ▼
        ThreadPoolExecutor (max_workers=N)
              │
    ┌─────────┼─────────┬─────────┬─────────┐
    │         │         │         │         │
    ▼         ▼         ▼         ▼         ▼
Worker-1  Worker-2  Worker-3  Worker-M  ...
    │         │         │         │
    │         │         │         │
    ▼         ▼         ▼         ▼         ▼
_process _process  _process  _process  ...
  (idx)    (idx)    (idx)    (idx)
    │         │         │         │
    │         │         │         │
    └─────────┴─────────┴─────────┴─────────┘
                        │
                        ▼
                Shared State:
                • ThreadSafeSet (hashes)
                • ImageCache (SQLite)
                • ProgressManager (SQLite)
                • HealthMonitor
```

### 6.2 Thread Safety Mechanisms

1. **Per-Thread Resources**
   - Each worker thread has its own HTTP session
   - Thread-local temporary directories
   - Isolated processing context

2. **Shared Resources Protection**
   - SQLite databases use WAL mode for concurrent access
   - Critical sections protected by threading locks
   - Atomic operations for counters and sets

3. **State Management**
   - Immutable configuration objects
   - Thread-safe collections for shared data
   - Explicit synchronization for mutable state

---

## 7. Error Handling Strategy

### 7.1 Error Handling Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ERROR HANDLING FLOW                                 │
└─────────────────────────────────────────────────────────────────────────────┘

                    Operation
                        │
                        ▼
              ┌─────────────────┐
              │  Try Operation  │
              └────────┬────────┘
                       │
           ┌───────────┴───────────┐
           │                       │
           ▼                       ▼
        Success                 Failure
           │                       │
           ▼                       ▼
      Return Result    ┌─────────────────────┐
                        │ Is it retryable?    │
                        │ (network, timeout)  │
                        └──────────┬──────────┘
                                   │
                       ┌───────────┴───────────┐
                       │                       │
                       ▼                       ▼
                    Retry                  No Retry
                       │                       │
                       ▼                       ▼
              ┌─────────────────┐    ┌─────────────────┐
              │ Exponential     │    │ Record Failure  │
              │ Backoff         │    │ in Progress     │
              └────────┬────────┘    └────────┬────────┘
                       │                       │
                       ▼                       ▼
              Retry Operation          Continue to
              (up to max_attempts)     next product
```

### 7.2 Exception Hierarchy

```
AdGenError (base)
├── SearchExhaustedError    → Use placeholder image
├── ImageDownloadError      → Use placeholder image
├── BackgroundRemovalError  → Use original image
├── VerificationError       → Accept/reject based on config
└── ConfigurationError      → Exit application
```

### 7.3 Recovery Strategies

1. **Network Failures**
   - Exponential backoff retry mechanism
   - Fallback to alternative search engines
   - Temporary suspension of problematic engines

2. **Image Processing Failures**
   - Skip individual product and continue
   - Generate placeholder images as fallback
   - Log detailed error information

3. **System Resource Issues**
   - Graceful degradation of features
   - Automatic cleanup of temporary files
   - Memory pressure handling

---

## 8. Performance Considerations

### 8.1 Memory Management
- Explicit garbage collection after image processing
- Image data released immediately after use
- Large AI models loaded once (singletons)
- Chunked processing to control memory footprint

### 8.2 I/O Optimization
- ThreadPoolExecutor for parallel downloads
- SQLite WAL mode for concurrent access
- Image cache prevents re-downloads
- Asynchronous I/O where beneficial

### 8.3 Network Optimization
- Per-thread HTTP sessions (connection pooling)
- Rate limiting to avoid blocking
- Circuit breakers to fail fast
- Efficient search result ranking

### 8.4 CPU Optimization
- Batch processing for AI models
- Lazy loading of heavy components
- Efficient algorithms for quality scoring
- Parallel processing with configurable workers

---

## 9. Security Considerations

### 9.1 Data Security
- Secure handling of temporary files
- Protection against malicious image content
- Safe URL handling and validation
- Dependency on trusted libraries only

### 9.2 Network Security
- HTTPS-only connections where supported
- User agent rotation to avoid detection
- Request headers to mimic browser behavior
- Connection timeouts to prevent hanging

### 9.3 System Security
- Limited file system access permissions
- Input validation and sanitization
- Secure configuration file handling
- Regular dependency updates

---

## 10. Scalability Considerations

### 10.1 Horizontal Scaling
- Configurable thread pool size
- Chunked processing for memory control
- Stateless worker design
- Shared-nothing architecture where possible

### 10.2 Vertical Scaling
- Efficient resource utilization
- Memory-optimized algorithms
- CPU-bound task distribution
- I/O-bound task parallelization

### 10.3 Distributed Potential
- Message queue integration possibility
- Microservice decomposition readiness
- Database sharding support
- Load balancing compatibility

---

## 11. Monitoring and Observability

### 11.1 Logging
- Structured logging with consistent format
- Multiple log levels (DEBUG, INFO, WARNING, ERROR)
- Contextual information in log messages
- Performance metrics logging

### 11.2 Metrics
- Processing throughput (ads/second)
- Success and failure rates
- Cache hit ratios
- Resource utilization

### 11.3 Health Checks
- Search engine availability monitoring
- Database connectivity checks
- Disk space monitoring
- Memory usage tracking

---

## 12. Deployment Considerations

### 12.1 Environment Requirements
- Python 3.10+ runtime
- Sufficient disk space for temporary files
- Internet connectivity for search engines
- GPU support for optimal AI performance (optional)

### 12.2 Configuration Management
- Environment variable support
- Configuration file overrides
- Secure credential handling
- Runtime configuration validation

### 12.3 Containerization
- Docker image support
- Kubernetes deployment readiness
- Health check endpoints
- Resource limit specifications

---

*Document Version: 1.0*
*Last Updated: February 18, 2026*