# Component PRD: Configuration Settings
## Ad Generator System

---

## 1. Purpose and Scope

### 1.1 Purpose
The Configuration Settings component provides a centralized, type-safe, and validated approach to managing all application parameters. It ensures consistent configuration across all system components while enabling easy customization without code changes.

### 1.2 Scope
This component encompasses:
- Definition of all configuration dataclasses
- Default value management
- Configuration validation
- Path management and creation
- Feature flag control
- Environment integration (future)

### 1.3 Out of Scope
- Runtime configuration changes
- External configuration file parsing (YAML/JSON)
- Configuration persistence
- Dynamic configuration reloading

---

## 2. Functional Requirements

### 2.1 Configuration Definition
**FR-CONFIG-001:** Define immutable dataclasses for all configuration aspects
- **Priority:** Critical
- **Description:** Each configuration aspect shall be represented by a frozen dataclass with type annotations
- **Acceptance Criteria:**
  - All configuration classes use `@dataclass(frozen=True)`
  - Type hints are provided for all fields
  - Default values are specified for all parameters

### 2.2 Default Configuration
**FR-CONFIG-002:** Provide sensible default values for all configuration parameters
- **Priority:** Critical
- **Description:** The system shall operate with default values requiring minimal setup
- **Acceptance Criteria:**
  - All required paths are set to reasonable defaults
  - Performance parameters are optimized for typical use cases
  - Feature flags represent recommended production settings

### 2.3 Configuration Validation
**FR-CONFIG-003:** Validate configuration parameters at startup
- **Priority:** High
- **Description:** Invalid configuration values shall be detected and reported before processing begins
- **Acceptance Criteria:**
  - Path existence is verified for required files/directories
  - Numeric parameters are checked for reasonable ranges
  - Enumerated values are validated against allowed options

### 2.4 Path Management
**FR-CONFIG-004:** Automate path creation and management
- **Priority:** High
- **Description:** Required directories shall be automatically created at startup
- **Acceptance Criteria:**
  - All output directories are created if missing
  - Parent directories are recursively created
  - Permission errors are clearly reported

### 2.5 Feature Flag Control
**FR-CONFIG-005:** Control system features through configuration flags
- **Priority:** Medium
- **Description:** Major system features shall be enabled/disabled through configuration
- **Acceptance Criteria:**
  - All optional features have corresponding flags
  - Flags are consistently named and organized
  - Default values reflect recommended production settings

---

## 3. Non-Functional Requirements

### 3.1 Performance
- Configuration loading time: ≤ 100ms
- Memory overhead: ≤ 10MB
- Validation time: ≤ 50ms

### 3.2 Reliability
- Configuration validation prevents 99%+ of startup errors
- Clear error messages for misconfiguration
- Graceful handling of missing optional components

### 3.3 Maintainability
- Configuration classes follow consistent naming conventions
- Default values are documented with rationale
- Changes to configuration require minimal code modifications

### 3.4 Security
- No sensitive credentials stored in code
- File permissions respected for configuration files
- Path traversal attacks prevented

---

## 4. Dependencies

### 4.1 Internal Dependencies
- Python 3.10+ (for dataclass features)
- pathlib for path management
- logging for error reporting

### 4.2 External Dependencies
- None (standard library only for this component)

### 4.3 Component Dependencies
- None (foundational component)

---

## 5. Error Handling

### 5.1 Configuration Errors
- **Missing Input File:** Report clear error with expected path
- **Invalid Parameter Values:** Provide specific validation error
- **Permission Denied:** Suggest corrective actions
- **Path Creation Failure:** Recommend manual directory creation

### 5.2 Validation Errors
- **Range Violations:** Show acceptable range
- **Invalid Enums:** List valid options
- **Path Issues:** Distinguish between missing and inaccessible

---

## 6. Performance Criteria

### 6.1 Loading Performance
- Cold start: ≤ 100ms
- Warm start: ≤ 50ms
- Memory footprint: ≤ 5MB

### 6.2 Validation Performance
- Full validation: ≤ 50ms
- Individual parameter checks: ≤ 5ms
- Path existence checks: ≤ 20ms

---

## 7. Security Considerations

### 7.1 Data Protection
- No hardcoded credentials
- Secure handling of file paths
- Prevention of path traversal attacks

### 7.2 Access Control
- Configuration files use appropriate permissions
- System paths respect OS access controls
- Temporary directories use secure permissions

---

## 8. Testing Requirements

### 8.1 Unit Tests
- Configuration class instantiation
- Default value verification
- Validation logic testing
- Path creation testing

### 8.2 Integration Tests
- End-to-end configuration loading
- Path validation with actual filesystem
- Error condition simulation

### 8.3 Performance Tests
- Configuration loading time measurement
- Memory usage profiling
- Validation performance under load

---

## 9. Integration Points

### 9.1 Primary Integration
- **AdPipeline:** Consumes AppConfig for all operations
- **All Components:** Receive specific configuration objects

### 9.2 Data Flow
```
Configuration Definition → Default Values → Validation → Component Distribution
```

### 9.3 APIs
- **Input:** None (passive component)
- **Output:** Configuration objects to all system components

---

## 10. Detailed Design

### 10.1 Configuration Classes

#### 10.1.1 AppConfig (Main Configuration)
```python
@dataclass
class AppConfig:
    paths: PathConfig
    quality: ImageQualityConfig
    bg: BackgroundRemovalConfig
    search: SearchConfig
    query: QueryConfig
    verify: VerificationConfig
    proxy: ProxyConfig
    notify: NotificationConfig
    output: OutputConfig
    pipeline: PipelineConfig
    
    # Feature flags
    resume: bool
    dry_run: bool
    verbose: bool
    remove_temp: bool
    start_index: Optional[int]
    end_index: Optional[int]
    enable_cache: bool
    enable_async: bool
    enable_health: bool
    enable_dlq: bool
    dlq_retries: int
    chunk_size: int
    multi_size: bool
    watermark: bool
```

#### 10.1.2 PathConfig
```python
@dataclass(frozen=True)
class PathConfig:
    root: Path
    csv_input: Path
    csv_output: Path
    images_dir: Path
    temp_dir: Path
    progress_db: Path
    cache_db: Path
    log_file: Path
    fonts_dir: Path
    proxy_file: Path
    models_dir: Path
```

#### 10.1.3 ImageQualityConfig
```python
@dataclass(frozen=True)
class ImageQualityConfig:
    min_width: int
    min_height: int
    min_file_bytes: int
    max_search_results: int
    min_aspect: float
    max_aspect: float
    min_unique_colours: int
    min_std_dev: float
    sharpness_weight: float
    contrast_weight: float
    resolution_weight: float
    source_weight: float
```

### 10.2 Validation Logic

#### 10.2.1 AppConfig.validate()
```python
def validate(self) -> None:
    """Validate configuration at startup."""
    if not self.paths.csv_input.exists():
        raise FileNotFoundError(f"Input CSV missing: {self.paths.csv_input}")
    if self.pipeline.max_workers < 1:
        raise ValueError("max_workers must be >= 1")
    for eng in self.search.priority:
        if eng not in ("google", "duckduckgo", "bing"):
            raise ValueError(f"Unknown engine: {eng}")
```

#### 10.2.2 PathConfig.ensure()
```python
def ensure(self) -> None:
    """Create required directories."""
    for d in (
        self.images_dir, self.temp_dir,
        self.csv_output.parent, self.progress_db.parent,
        self.cache_db.parent, self.log_file.parent,
        self.fonts_dir, self.models_dir,
    ):
        d.mkdir(parents=True, exist_ok=True)
```

### 10.3 Default Values

#### 10.3.1 Path Defaults
- `csv_input`: `data/input/main.csv`
- `images_dir`: `data/output/images/`
- `temp_dir`: `data/temp/workers/`
- `progress_db`: `data/temp/progress.db`

#### 10.3.2 Quality Defaults
- `min_width`: 60 pixels
- `min_height`: 60 pixels
- `min_file_bytes`: 30,000 bytes
- `min_aspect`: 0.3 ratio
- `max_aspect`: 3.0 ratio

#### 10.3.3 Feature Flags
- `enable_cache`: True
- `enable_health`: True
- `enable_dlq`: True
- `verbose`: True

---

## 11. Implementation Plan

### 11.1 Phase 1: Core Configuration
- Define all configuration dataclasses
- Implement default values
- Add basic validation

### 11.2 Phase 2: Advanced Features
- Implement path management
- Add comprehensive validation
- Create configuration documentation

### 11.3 Phase 3: Optimization
- Profile configuration loading
- Optimize memory usage
- Add performance tests

---

## 12. Monitoring and Logging

### 12.1 Configuration Logging
- Log configuration summary at startup
- Report any overridden defaults
- Warn about deprecated settings

### 12.2 Validation Logging
- Log validation errors with context
- Report path creation successes/failures
- Trace configuration inheritance

---

*Document Version: 1.0*
*Last Updated: February 18, 2026*