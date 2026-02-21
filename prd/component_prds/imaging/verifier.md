# Image Verifier Component PRD

## 1. Purpose and Scope

### 1.1 Component Purpose
The `ImageVerifier` class implements semantic image-text verification using CLIP and BLIP AI models to ensure downloaded images are relevant to their search queries. It provides a singleton architecture with thread-safe model access for efficient multi-threaded verification operations.

### 1.2 Position in Architecture
This component serves as the intelligence layer in the imaging subsystem, positioned between basic image validation and final acceptance. It integrates with the image downloader to provide semantic relevance checking that goes beyond simple visual quality assessment.

### 1.3 Key Responsibilities
- Load and manage CLIP and BLIP AI models with singleton pattern
- Provide thread-safe model inference through locking mechanisms
- Implement multi-model verification combining CLIP similarity and BLIP caption analysis
- Apply configurable scoring thresholds for acceptance/rejection decisions
- Offer graceful degradation when AI models are unavailable
- Track model performance and usage statistics

## 2. Functional Requirements

### 2.1 Model Management
- Implement singleton pattern for efficient model loading and sharing
- Support automatic device selection (CPU/GPU) with CUDA detection
- Provide thread-safe model initialization with locking
- Handle model loading failures gracefully with fallback behavior
- Support configurable model selection (CLIP, BLIP, or both)

### 2.2 CLIP Verification
- Compute cosine similarity between image embeddings and text embeddings
- Normalize similarity scores to 0.0-1.0 range for consistency
- Apply configurable acceptance and rejection thresholds for quick decisions
- Handle CLIP model failures gracefully without pipeline disruption

### 2.3 BLIP Verification
- Generate descriptive captions for images using BLIP model
- Compute word overlap scores between captions and search queries
- Apply stop word filtering for more meaningful comparisons
- Weight query coverage and Jaccard similarity for balanced scoring

### 2.4 Combined Scoring
- Weight CLIP and BLIP scores according to configuration
- Calculate final combined score for comprehensive assessment
- Make acceptance decisions based on combined threshold parameters
- Track best candidates for fallback when strict thresholds aren't met
- Provide detailed scoring breakdown for debugging and analysis

## 3. Input/Output Specifications

### 3.1 Inputs
- `image`: PIL Image object to verify
- `query`: Text query string for comparison
- `VerificationConfig`: Configuration object with model parameters and thresholds
- Device preference: Auto-detection, CPU, or GPU specification

### 3.2 Outputs
- `VerificationResult` object containing:
  - `accepted`: Boolean indicating verification success
  - `clip_score`: Float similarity score from CLIP model
  - `blip_score`: Float overlap score from BLIP analysis
  - `combined_score`: Weighted combination of individual scores
  - `blip_caption`: Generated caption from BLIP model
  - `reason`: String explanation for acceptance/rejection decision
  - `summary()`: Method for human-readable result description

### 3.3 Configuration Parameters
- Model selection: Enable/disable CLIP, BLIP independently
- Model names: Specific pre-trained model identifiers
- Device preference: Auto, CPU, or GPU
- Scoring weights: Relative importance of CLIP vs. BLIP scores
- Thresholds: Acceptance, rejection, and combined decision points
- Fallback behavior: Accept/reject when models unavailable

## 4. Dependencies

### 4.1 Internal Dependencies
- `config.settings.VerificationConfig`: Verification parameters and thresholds
- `utils.log_config`: Structured logging for model operations
- `imaging.verifier._word_overlap_score`: Text similarity calculation

### 4.2 External Dependencies
- `torch`: PyTorch framework for AI model execution
- `transformers`: Hugging Face library for CLIP and BLIP models
- `PIL.Image`: Image processing and format handling
- Standard Python libraries: `threading`, `dataclasses`, `io`

## 5. Error Handling and Fault Tolerance

### 5.1 Model Loading Failures
- Handle missing transformer library gracefully with informative errors
- Continue operation with reduced verification capabilities when models fail
- Log detailed error information for debugging model issues
- Provide fallback configuration when model loading fails

### 5.2 Inference Errors
- Catch exceptions during model inference operations
- Return neutral scores (0.0) for failed verifications
- Log inference errors without disrupting overall pipeline
- Implement timeouts to prevent hanging operations

### 5.3 Resource Management
- Use context managers for proper resource cleanup
- Implement garbage collection hints to manage GPU memory
- Apply image resizing for efficient inference without quality loss
- Handle thread-local storage appropriately

### 5.4 Degraded Operation
- Continue functioning when one model type fails
- Fall back to basic acceptance when both models unavailable
- Provide configuration options for operation without verification
- Log warnings when operating in degraded mode

## 6. Performance Criteria

### 6.1 Response Time Targets
- Model loading: 5-30 seconds depending on model size and device
- CLIP inference: 50-200ms per image (GPU dependent)
- BLIP inference: 100-500ms per image (GPU dependent)
- Combined verification: 150-700ms per image (GPU dependent)

### 6.2 Resource Usage
- Memory: 1-4GB for model loading (GPU dependent)
- GPU: Utilization during inference operations
- CPU: Moderate usage for preprocessing and postprocessing
- Threads: Thread-safe with locking around model inference

### 6.3 Scalability Considerations
- Singleton design prevents multiple model instantiations
- Thread-local storage for connection isolation
- Locking mechanisms ensure safe concurrent access
- Model sharing across threads maximizes resource efficiency

## 7. Security Considerations

### 7.1 Model Integrity
- Use trusted pre-trained models from Hugging Face
- Validate model sources and versions
- Apply appropriate permissions for model files
- Monitor for model updates and security patches

### 7.2 Input Validation
- Validate image formats before processing
- Check image dimensions to prevent resource exhaustion
- Apply timeouts to prevent denial of service
- Sanitize text inputs to prevent injection attacks

### 7.3 Secure Communication
- Use HTTPS for model downloads when applicable
- Validate SSL certificates for remote model access
- Apply appropriate network timeouts
- Log security-relevant events for audit purposes

## 8. Testing Requirements

### 8.1 Unit Tests
- Verify singleton pattern implementation
- Test model loading with various configurations
- Validate CLIP scoring with sample images and queries
- Check BLIP captioning and overlap scoring
- Test combined scoring with different weight configurations
- Verify threshold-based acceptance decisions
- Check error handling for model loading failures

### 8.2 Integration Tests
- Validate actual model loading and inference
- Test multi-threaded verification scenarios
- Verify proper resource cleanup after inference
- Confirm device selection works correctly
- Test fallback behavior with missing models

### 8.3 Mocking Strategy
- Mock transformer library for isolated logic testing
- Simulate model outputs for consistent scoring tests
- Control timing to test timeout behavior
- Mock device detection for cross-platform testing

## 9. Integration Points

### 9.1 Image Downloader Integration
- Accepts `ImageVerifier` instance from downloader configuration
- Called during candidate evaluation phase
- Receives PIL images and query strings for verification
- Returns scores and decisions to influence candidate selection

### 9.2 Configuration Integration
- Consumes `VerificationConfig` for all operational parameters
- Supports runtime configuration of models and thresholds
- Allows disabling of verification for performance testing
- Enables logging of detailed verification statistics

### 9.3 Logging Integration
- Uses structured logging for model loading events
- Logs inference timing and performance metrics
- Records verification decisions for analysis
- Reports errors and warnings for operational monitoring

## 10. Implementation Details

### 10.1 Class Structure
```python
class ImageVerifier:
    def __new__(cls, cfg: VerificationConfig):
        # Singleton implementation with thread-safe initialization
    
    def __init__(self, cfg: VerificationConfig) -> None:
        # Initialize models and configuration
    
    def _setup_device(self) -> None:
        # Determine compute device (CPU/GPU)
    
    def _load_models(self) -> None:
        # Load CLIP and/or BLIP models
    
    def _clip_score(self, image: Image.Image, query: str) -> float:
        # Compute CLIP similarity score
    
    def _blip_caption(self, image: Image.Image) -> str:
        # Generate image caption with BLIP
    
    def _blip_score(self, image: Image.Image, query: str) -> Tuple[float, str]:
        # Compute BLIP word overlap score
    
    def verify(self, image: Image.Image, query: str) -> VerificationResult:
        # Main verification entry point
    
    @property
    def is_available(self) -> bool:
        # Check if models are loaded
    
    def stats(self) -> Dict:
        # Return model status information
```

### 10.2 Singleton Pattern
- Thread-safe initialization with double-checked locking
- Shared model instances across all threads
- Proper cleanup and resource management
- Configuration consistency across all usages

### 10.3 Verification Workflow
1. Image Preprocessing: Resize for efficient inference
2. CLIP Analysis: Compute similarity score with quick thresholds
3. BLIP Analysis: Generate caption and compute word overlap
4. Score Combination: Weight scores according to configuration
5. Decision Making: Apply thresholds for acceptance/rejection
6. Result Creation: Package scores and metadata for caller