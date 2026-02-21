# Component PRD: Progress Manager
## Ad Generator System

---

## 1. Purpose and Scope

### 1.1 Purpose
The Progress Manager component provides persistent tracking of advertisement generation progress, enabling job resumption, failure recovery, and operational monitoring. It ensures that long-running processing jobs can be interrupted and resumed without losing progress or duplicating work.

### 1.2 Scope
This component encompasses:
- Progress state persistence using SQLite
- Completion status tracking for individual products
- Dead letter queue management for failed operations
- Statistical reporting and monitoring
- Transactional integrity for status updates

### 1.3 Out of Scope
- User interface for progress visualization
- Real-time progress streaming
- External progress reporting systems
- Distributed progress coordination

---

## 2. Functional Requirements

### 2.1 Progress Tracking
**FR-PROGRESS-001:** Persistently track completion status of individual products
- **Priority:** Critical
- **Description:** The system shall maintain a record of which products have been successfully processed
- **Acceptance Criteria:**
  - Each product index has a tracked status
  - Status updates are immediately persistent
  - Duplicate processing is prevented
  - Historical attempt information is maintained

### 2.2 Job Resumption
**FR-PROGRESS-002:** Enable resumption of interrupted processing jobs
- **Priority:** Critical
- **Description:** The system shall skip already completed products when restarting a job
- **Acceptance Criteria:**
  - Previously completed products are identified and skipped
  - Partial progress is preserved
  - Resume option is configurable
  - Clear indication of resumption in logs

### 2.3 Failure Management
**FR-PROGRESS-003:** Track and manage failed processing attempts
- **Priority:** High
- **Description:** The system shall record failures and support retry mechanisms
- **Acceptance Criteria:**
  - Failed products are recorded with error information
  - Retry count is tracked for each failure
  - Dead letter queue accumulates repeatedly failed products
  - Maximum retry limits are enforced

### 2.4 Statistical Reporting
**FR-PROGRESS-004:** Provide operational statistics and metrics
- **Priority:** Medium
- **Description:** The system shall collect and report processing metrics
- **Acceptance Criteria:**
  - Success and failure counts are tracked
  - Retry statistics are maintained
  - Performance metrics are calculated
  - Summary reports are generated

---

## 3. Non-Functional Requirements

### 3.1 Performance
- Status update latency: ≤ 10ms
- Query performance: ≤ 5ms for status checks
- Database size: ≤ 100MB for 100K products
- Memory usage: ≤ 10MB

### 3.2 Reliability
- Data integrity: 99.99% with ACID compliance
- Failure recovery: Automatic after unexpected termination
- Consistency: No duplicate or lost status updates
- Availability: Always accessible during processing

### 3.3 Scalability
- Linear performance with product count
- Efficient storage for large datasets
- Concurrent access support
- Database connection pooling

### 3.4 Maintainability
- Clear database schema documentation
- Simple query operations
- Transactional boundary management
- Error handling and logging

---

## 4. Dependencies

### 4.1 Internal Dependencies
- **SQLite3:** For persistent storage
- **Configuration:** For database path and settings
- **Logging:** For operational visibility

### 4.2 External Dependencies
- **File System:** For database file storage
- **Operating System:** For file access permissions

### 4.3 Component Dependencies
- **AdPipeline:** Consumes progress tracking services
- **Main Entry Point:** Initializes progress manager

---

## 5. Error Handling

### 5.1 Database Errors
- **Connection Failures:** Retry with exponential backoff
- **Write Conflicts:** Transaction rollback and retry
- **Corruption:** Alert operator and halt processing
- **Disk Full:** Graceful shutdown with error reporting

### 5.2 Data Errors
- **Invalid States:** Validation and correction
- **Duplicate Entries:** Prevention through unique constraints
- **Missing Data:** Default value substitution
- **Constraint Violations:** Error reporting and handling

---

## 6. Performance Criteria

### 6.1 Database Performance
- **Write Operations:** ≤ 10ms per status update
- **Read Operations:** ≤ 5ms per status check
- **Batch Operations:** ≤ 100ms for 1000 updates
- **Query Efficiency:** Index-optimized queries

### 6.2 Storage Requirements
- **Database Size:** ≤ 1KB per product entry
- **Growth Rate:** Linear with product count
- **Index Overhead:** ≤ 20% of data size
- **Temporary Space:** Minimal transaction log usage

---

## 7. Security Considerations

### 7.1 Data Security
- Database file permissions restriction
- Prevention of SQL injection attacks
- Validation of all input data
- Secure handling of error messages

### 7.2 Access Security
- File system access controls
- Process isolation for database access
- Prevention of unauthorized database access
- Audit trail for critical operations

---

## 8. Testing Requirements

### 8.1 Unit Tests
- Status update and retrieval operations
- Transaction boundary management
- Error condition handling
- Database connection management

### 8.2 Integration Tests
- End-to-end progress tracking
- Job resumption scenarios
- Failure and retry handling
- Concurrent access validation

### 8.3 Performance Tests
- Status update throughput
- Query response times
- Storage efficiency
- Concurrent operation performance

---

## 9. Integration Points

### 9.1 Primary Integration
- **AdPipeline:** Consumes progress tracking services
- **Configuration:** Receives database settings
- **Main Entry Point:** Initializes progress manager

### 9.2 Data Flow
```
Processing Request → Status Check → Processing Execution
         ↓                ↓                 ↓
   Status Update ←─── Result Recording ←── Completion Marking
         ↓                ↓                 ↓
    Progress Stats ←─ Failure Management ←─ Retry Handling
```

### 9.3 APIs
- **Input:** Product indices, status information, metadata
- **Output:** Status queries, statistics, dead letter queues

---

## 10. Detailed Design

### 10.1 Database Schema

#### 10.1.1 Progress Table
```sql
CREATE TABLE progress (
    idx INTEGER PRIMARY KEY,
    status TEXT NOT NULL,  -- 'pending', 'done', 'failed'
    meta TEXT,             -- JSON metadata about the operation
    attempts INTEGER DEFAULT 0,
    updated_at REAL,       -- Unix timestamp
    FOREIGN KEY(idx) REFERENCES input_products(idx)
);

CREATE INDEX idx_progress_status ON progress(status);
CREATE INDEX idx_progress_updated ON progress(updated_at);
```

#### 10.1.2 Dead Letters Table
```sql
CREATE TABLE dead_letters (
    idx INTEGER PRIMARY KEY,
    meta TEXT,             -- JSON error information
    error TEXT,            -- Error message
    created_at REAL,       -- Unix timestamp
    FOREIGN KEY(idx) REFERENCES input_products(idx)
);
```

### 10.2 Progress Manager Class

#### 10.2.1 Main Class Structure
```python
class ProgressManager:
    """Manages processing progress and state persistence."""
    
    def __init__(self, db_path: Path, max_retries: int = 2) -> None:
        """Initialize progress manager with database path."""
        self.db_path = db_path
        self.max_retries = max_retries
        self._init_db()
        
    def is_done(self, idx: int) -> bool:
        """Check if product index is already processed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT status FROM progress WHERE idx = ?", (idx,)
            )
            row = cursor.fetchone()
            return row and row[0] == "done"
            
    def mark_done(self, idx: int, meta: Dict[str, Any]) -> None:
        """Mark product index as completed."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO progress 
                   (idx, status, meta, attempts, updated_at)
                   VALUES (?, ?, ?, 
                          COALESCE((SELECT attempts FROM progress WHERE idx = ?), 0),
                          ?)""",
                (idx, "done", json.dumps(meta), idx, time.time())
            )
            conn.commit()
            
    def mark_failed(self, idx: int, meta: Dict[str, Any]) -> None:
        """Mark product index as failed and handle retries."""
        with sqlite3.connect(self.db_path) as conn:
            # Get current attempts
            cursor = conn.execute(
                "SELECT attempts FROM progress WHERE idx = ?", (idx,)
            )
            row = cursor.fetchone()
            attempts = (row[0] if row else 0) + 1
            
            if attempts > self.max_retries:
                # Move to dead letters
                error_msg = meta.get("error", "Unknown error")
                conn.execute(
                    """INSERT OR REPLACE INTO dead_letters 
                       (idx, meta, error, created_at)
                       VALUES (?, ?, ?, ?)""",
                    (idx, json.dumps(meta), error_msg, time.time())
                )
                # Remove from progress
                conn.execute("DELETE FROM progress WHERE idx = ?", (idx,))
            else:
                # Update progress with failure
                conn.execute(
                    """INSERT OR REPLACE INTO progress 
                       (idx, status, meta, attempts, updated_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (idx, "failed", json.dumps(meta), attempts, time.time())
                )
            conn.commit()
```

### 10.3 Status Management

#### 10.3.1 Status Values
- **pending:** Product not yet processed
- **done:** Product successfully processed
- **failed:** Product processing failed (retryable)

#### 10.3.2 Status Transitions
```
pending ──Success──→ done
   │                  ↑
   │                 Retry
   ↓                  │
failed ──MaxRetries──→ dead_letters
```

### 10.4 Retry Logic

#### 10.4.1 Retry Counting
- Each failure increments attempt counter
- Maximum retries configured (default: 2)
- Exponential backoff between retries (handled by pipeline)

#### 10.4.2 Dead Letter Queue
- Products exceeding max retries moved to DLQ
- Error information preserved for diagnosis
- DLQ processed at end of main job
- Separate reporting for DLQ items

### 10.5 Statistical Reporting

#### 10.5.1 Progress Statistics
```python
def stats(self) -> str:
    """Generate progress statistics report."""
    with sqlite3.connect(self.db_path) as conn:
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as done,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(attempts) as total_attempts
            FROM progress
        """)
        row = cursor.fetchone()
        # Generate formatted report
        pass
```

#### 10.5.2 Performance Metrics
- Processing rate calculation
- Success/failure ratios
- Average retry counts
- Database operation timing

---

## 11. Implementation Plan

### 11.1 Phase 1: Core Functionality
- Implement database schema and initialization
- Add basic status tracking operations
- Create progress query interfaces

### 11.2 Phase 2: Advanced Features
- Implement retry and dead letter queue logic
- Add statistical reporting capabilities
- Optimize database performance

### 11.3 Phase 3: Robustness
- Add comprehensive error handling
- Implement transaction safety
- Add performance monitoring

---

## 12. Monitoring and Logging

### 12.1 Operational Logging
- Status update operations
- Retry and failure events
- Database connection issues
- Transaction boundaries

### 12.2 Performance Monitoring
- Query response times
- Database size tracking
- Transaction success rates
- Concurrent access performance

---

*Document Version: 1.0*
*Last Updated: February 18, 2026*