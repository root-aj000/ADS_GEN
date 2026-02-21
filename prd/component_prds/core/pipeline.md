# Component PRD: Core Pipeline
## Ad Generator System

---

## 1. Purpose and Scope

### 1.1 Purpose
The Core Pipeline component serves as the central orchestrator of the advertisement generation workflow. It manages the end-to-end processing of product catalogs, coordinating all subordinate components to transform product data into professional advertisements while ensuring optimal performance through concurrent processing.

### 1.2 Scope
This component encompasses:
- Workflow orchestration and coordination
- Concurrent processing management
- Progress tracking and resumption
- Error handling and recovery
- Statistics collection and reporting
- Resource management and cleanup

### 1.3 Out of Scope
- Individual component implementation details
- User interface functionality
- External system integration
- Real-time processing capabilities

---

## 2. Functional Requirements

### 2.1 Workflow Orchestration
**FR-PIPELINE-001:** Coordinate all stages of advertisement generation
- **Priority:** Critical
- **Description:** The pipeline shall manage the complete flow from input processing to output generation
- **Acceptance Criteria:**
  - All processing stages executed in correct order
  - Component dependencies properly managed
  - Data flows correctly between stages

### 2.2 Concurrent Processing
**FR-PIPELINE-002:** Execute multiple product operations simultaneously
- **Priority:** Critical
- **Description:** The pipeline shall utilize thread pools to process multiple products concurrently
- **Acceptance Criteria:**
  - Configurable number of worker threads (1-16)
  - Thread-safe operations throughout
  - Optimal resource utilization

### 2.3 Progress Tracking
**FR-PIPELINE-003:** Monitor and persist processing progress
- **Priority:** High
- **Description:** The pipeline shall track completion status and enable job resumption
- **Acceptance Criteria:**
  - Progress persisted to SQLite database
  - Resume capability for interrupted jobs
  - Duplicate work prevention

### 2.4 Error Handling
**FR-PIPELINE-004:** Manage failures gracefully with recovery options
- **Priority:** High
- **Description:** The pipeline shall handle component failures without terminating the entire job
- **Acceptance Criteria:**
  - Individual product failures don't stop overall processing
  - Dead letter queue for repeated failures
  - Clear error reporting and logging

### 2.5 Resource Management
**FR-PIPELINE-005:** Efficiently manage system resources throughout processing
- **Priority:** Medium
- **Description:** The pipeline shall optimize memory, CPU, and disk usage
- **Acceptance Criteria:**
  - Memory usage remains within configured limits
  - Temporary files properly cleaned up
  - Database connections managed efficiently

---

## 3. Non-Functional Requirements

### 3.1 Performance
- Processing throughput: ≥ 1,000 products/hour with 4 workers
- Memory usage: ≤ 2GB peak with 4 workers
- Startup time: ≤ 2 seconds

### 3.2 Reliability
- Job completion rate: ≥ 95% under normal conditions
- Graceful degradation during component failures
- Data integrity maintained throughout processing

### 3.3 Scalability
- Linear performance scaling up to 8 worker threads
- Consistent memory usage regardless of catalog size
- Chunked processing for large datasets

### 3.4 Maintainability
- Clear separation of orchestration and business logic
- Comprehensive logging for debugging
- Modular design for component replacement

---

## 4. Dependencies

### 4.1 Internal Dependencies
- **Search Manager:** For image search operations
- **Image Downloader:** For image acquisition and validation
- **Background Remover:** For background elimination
- **Ad Compositor:** For final advertisement creation
- **Progress Manager:** For tracking completion status
- **Configuration:** For all pipeline settings

### 4.2 External Dependencies
- **SQLite:** For progress tracking database
- **File System:** For input/output operations
- **Network:** For search engine communication

### 4.3 Component Dependencies
- **Main Entry Point:** Instantiates and executes pipeline
- **All Processing Components:** Called during workflow execution

---

## 5. Error Handling

### 5.1 Processing Errors
- **Individual Product Failure:** Log error, continue with next product
- **Component Initialization Failure:** Terminate with clear error message
- **Resource Exhaustion:** Throttle processing, alert operator

### 5.2 Recovery Mechanisms
- **Job Resumption:** Skip already completed products
- **Dead Letter Queue:** Retry failed products at end of run
- **Graceful Shutdown:** Handle interruption signals properly

---

## 6. Performance Criteria

### 6.1 Throughput Requirements
- **Minimum:** 500 products/hour with 1 worker
- **Target:** 1,200 products/hour with 4 workers
- **Optimal:** 3,000+ products/hour with 16 workers

### 6.2 Resource Usage
- **Memory:** ≤ 500MB per worker thread
- **CPU:** 60-80% utilization during processing
- **Disk I/O:** ≤ 100MB/s average

### 6.3 Timing Constraints
- **Startup:** ≤ 2 seconds
- **Individual Product:** ≤ 10 seconds average
- **Shutdown:** ≤ 5 seconds

---

## 7. Security Considerations

### 7.1 Data Security
- Secure handling of temporary files
- Protection against malicious input data
- Validation of file paths and URLs

### 7.2 System Security
- Prevention of resource exhaustion attacks
- Safe handling of external dependencies
- Protection against injection attacks

---

## 8. Testing Requirements

### 8.1 Unit Tests
- Pipeline initialization with various configurations
- Progress tracking functionality
- Error handling scenarios
- Resource cleanup procedures

### 8.2 Integration Tests
- End-to-end workflow execution
- Concurrent processing validation
- Progress persistence and resumption
- Failure recovery scenarios

### 8.3 Performance Tests
- Throughput benchmarking
- Memory usage profiling
- Stress testing with large datasets
- Resource contention scenarios

---

## 9. Integration Points

### 9.1 Primary Integration
- **Main Entry Point:** Pipeline instantiation and execution
- **Processing Components:** Workflow stage execution
- **Progress Manager:** Status tracking and persistence

### 9.2 Data Flow
```
Input CSV → Query Building → Component Coordination → Output Generation
     ↓           ↓                  ↓                    ↓
Progress Tracking ← Error Handling ← Resource Management ← Cleanup
```

### 9.3 APIs
- **Input:** AppConfig, Product DataFrame
- **Output:** Processed advertisements, updated CSV, statistics

---

## 10. Detailed Design

### 10.1 Pipeline Architecture

#### 10.1.1 Main Pipeline Class
```python
class AdPipeline:
    """Main orchestrator for advertisement generation."""
    
    def __init__(self, cfg: AppConfig) -> None:
        """Initialize pipeline with configuration."""
        self.cfg = cfg
        self.search = SearchManager(cfg.search)
        self.download = ImageDownloader(...)
        self.bg = BackgroundRemover(cfg.bg)
        self.comp = AdCompositor(cfg.paths.fonts_dir)
        self.progress = ProgressManager(...)
        # ... other components
        
    def run(self) -> None:
        """Execute the advertisement generation pipeline."""
        # Workflow orchestration logic
        pass
```

#### 10.1.2 Processing Stages
1. **Initialization**
   - Configuration validation
   - Component initialization
   - Path preparation

2. **Workflow Execution**
   - Product iteration
   - Concurrent processing
   - Progress tracking

3. **Completion**
   - Final output generation
   - Resource cleanup
   - Statistics reporting

### 10.2 Concurrency Management

#### 10.2.1 Thread Pool Implementation
```python
def _run_indices(self, indices: List[int]) -> None:
    """Process a list of indices with the thread pool."""
    with ThreadPoolExecutor(
        max_workers=self.cfg.pipeline.max_workers,
        thread_name_prefix="adgen",
    ) as pool:
        futs = {pool.submit(self._process, i): i for i in indices}
        for fut in as_completed(futs):
            # Handle completed tasks
            pass
```

#### 10.2.2 Worker Coordination
- Thread-safe shared resources
- Per-thread temporary directories
- Atomic progress updates
- Graceful shutdown handling

### 10.3 Progress Tracking

#### 10.3.1 Progress Data Model
```python
class ProgressManager:
    """Manages processing progress and state."""
    
    def is_done(self, idx: int) -> bool:
        """Check if product index is already processed."""
        pass
        
    def mark_done(self, idx: int, meta: Dict[str, Any]) -> None:
        """Mark product index as completed."""
        pass
        
    def mark_failed(self, idx: int, meta: Dict[str, Any]) -> None:
        """Mark product index as failed."""
        pass
```

#### 10.3.2 Resumption Logic
- Identify unprocessed products
- Skip completed work
- Handle partial failures

### 10.4 Error Recovery

#### 10.4.1 Dead Letter Queue
```python
def _process_dlq(self) -> None:
    """Process dead letter queue for failed products."""
    dlq = self.progress.get_dead_letters()
    if dlq:
        self.stats.dlq_retries.increment(len(dlq))
        self._run_indices(dlq)
```

#### 10.4.2 Graceful Shutdown
```python
def _on_signal(self, signum: int, _: Any) -> None:
    """Handle shutdown signals gracefully."""
    log.warning("Signal %d — shutting down gracefully", signum)
    self._shutdown.set()
```

---

## 11. Implementation Plan

### 11.1 Phase 1: Core Orchestration
- Implement basic workflow coordination
- Add sequential processing capability
- Create progress tracking foundation

### 11.2 Phase 2: Concurrency Features
- Add thread pool management
- Implement concurrent processing
- Add progress persistence

### 11.3 Phase 3: Advanced Features
- Implement error recovery mechanisms
- Add performance optimization
- Enhance monitoring and logging

---

## 12. Monitoring and Logging

### 12.1 Processing Metrics
```python
class Stats:
    """Processing statistics collector."""
    total: AtomicCounter        # Total products processed
    success: AtomicCounter      # Successfully processed
    failed: AtomicCounter       # Failed processing
    placeholder: AtomicCounter  # Placeholder images used
    # ... other counters
```

### 12.2 Diagnostic Information
- Detailed logging for each processing stage
- Performance metrics collection
- Error pattern analysis
- Resource utilization tracking

---

*Document Version: 1.0*
*Last Updated: February 18, 2026*