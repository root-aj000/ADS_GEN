# Component PRD: Ad Compositor
## Ad Generator System

---

## 1. Purpose and Scope

### 1.1 Purpose
The Ad Compositor component is responsible for creating professional-quality advertisement images by combining processed product images with textual information, branding elements, and stylistic enhancements. It transforms raw image and data inputs into visually appealing, marketing-ready advertisements.

### 1.2 Scope
This component encompasses:
- Advertisement layout and composition
- Text rendering and styling
- Image manipulation and enhancement
- Placeholder generation for failed products
- Font management and text formatting
- Visual effect application (shadows, gradients, etc.)

### 1.3 Out of Scope
- Image acquisition and processing
- Template definition and management
- Color scheme selection logic
- Brand asset management

---

## 2. Functional Requirements

### 2.1 Advertisement Composition
**FR-COMPOSITOR-001:** Create advertisement images from product data and images
- **Priority:** Critical
- **Description:** The compositor shall generate final advertisement images using templates and product information
- **Acceptance Criteria:**
  - All required template elements populated
  - Product images correctly positioned and sized
  - Text content accurately rendered
  - Output saved in specified format

### 2.2 Text Rendering
**FR-COMPOSITOR-002:** Render text with professional styling and formatting
- **Priority:** Critical
- **Description:** The compositor shall support rich text rendering with various fonts, sizes, and colors
- **Acceptance Criteria:**
  - Multiple font families supported
  - Dynamic text sizing based on content length
  - Proper text alignment and wrapping
  - Unicode character support

### 2.3 Image Enhancement
**FR-COMPOSITOR-003:** Apply visual enhancements to improve advertisement quality
- **Priority:** High
- **Description:** The compositor shall add professional effects to increase visual appeal
- **Acceptance Criteria:**
  - Drop shadows for floating elements
  - Gradient backgrounds when appropriate
  - Image borders and outlines
  - Transparency and blending effects

### 2.4 Placeholder Generation
**FR-COMPOSITOR-004:** Generate informative placeholders for failed products
- **Priority:** High
- **Description:** The compositor shall create placeholder images when product processing fails
- **Acceptance Criteria:**
  - Clear indication of failure reason
  - Product information still visible
  - Consistent styling with successful ads
  - Distinct appearance from regular advertisements

### 2.5 Font Management
**FR-COMPOSITOR-005:** Manage font resources and ensure consistent rendering
- **Priority:** Medium
- **Description:** The compositor shall handle font loading and fallback gracefully
- **Acceptance Criteria:**
  - Custom fonts loaded from specified directory
  - System font fallback when needed
  - Font caching for performance
  - Error handling for missing fonts

---

## 3. Non-Functional Requirements

### 3.1 Performance
- Composition time: ≤ 100ms per advertisement
- Memory usage: ≤ 50MB per composition operation
- Font loading time: ≤ 200ms

### 3.2 Reliability
- Composition success rate: ≥ 99% for valid inputs
- Graceful degradation for missing assets
- Consistent output quality across platforms

### 3.3 Quality
- Professional appearance matching design specifications
- Accurate text representation
- Proper image quality preservation
- Consistent branding application

### 3.4 Maintainability
- Clear separation of layout and rendering logic
- Template-driven design for easy modification
- Comprehensive error handling and logging
- Modular architecture for feature additions

---

## 4. Dependencies

### 4.1 Internal Dependencies
- **PIL/Pillow:** For image manipulation and rendering
- **Font Management:** For font loading and text rendering
- **Configuration:** For compositor settings and paths
- **Templates:** For layout definitions

### 4.2 External Dependencies
- **Font Files:** TTF/OTF files for text rendering
- **System Fonts:** Fallback font resources
- **Image Libraries:** Underlying image processing libraries

### 4.3 Component Dependencies
- **AdPipeline:** Provides product data and images
- **Configuration:** Supplies compositor settings
- **Templates:** Defines layout specifications

---

## 5. Error Handling

### 5.1 Composition Errors
- **Missing Fonts:** Fallback to system defaults
- **Corrupt Images:** Skip problematic elements
- **Text Overflow:** Truncate with ellipsis
- **Layout Issues:** Adjust elements to fit

### 5.2 Asset Errors
- **Missing Assets:** Use placeholder equivalents
- **Unsupported Formats:** Convert to compatible formats
- **Permission Issues:** Report and continue processing

---

## 6. Performance Criteria

### 6.1 Rendering Performance
- Single advertisement: ≤ 100ms
- Batch processing: ≤ 50ms per advertisement (amortized)
- Peak memory usage: ≤ 50MB per operation

### 6.2 Resource Usage
- Font cache memory: ≤ 100MB
- Temporary file usage: ≤ 10MB
- CPU utilization: ≤ 20% during composition

---

## 7. Security Considerations

### 7.1 Content Security
- Text content sanitization
- No executable code in rendered output
- Protected against injection attacks
- File path validation

### 7.2 Asset Security
- Font files from trusted sources
- Image validation before processing
- No arbitrary file system access
- Secure temporary file handling

---

## 8. Testing Requirements

### 8.1 Unit Tests
- Text rendering with various fonts and sizes
- Image placement and sizing calculations
- Color and transparency handling
- Effect application (shadows, gradients)

### 8.2 Integration Tests
- Complete advertisement composition
- Placeholder generation scenarios
- Font fallback mechanisms
- Error condition handling

### 8.3 Visual Tests
- Output quality verification
- Cross-platform rendering consistency
- Text accuracy and readability
- Layout integrity validation

---

## 9. Integration Points

### 9.1 Primary Integration
- **AdPipeline:** Receives product data and images for composition
- **Configuration:** Gets compositor settings and paths
- **Templates:** Uses layout definitions for rendering

### 9.2 Data Flow
```
Product Data + Processed Images → Layout Application → Text Rendering
              ↓                        ↓                  ↓
         Visual Effects ←─────── Image Enhancement ←─── Font Management
              ↓                        ↓                  ↓
        Final Advertisement ←─── Quality Assurance ←─── Output Generation
```

### 9.3 APIs
- **Input:** Product data (DataFrame row), image paths, template selection
- **Output:** Saved advertisement image files

---

## 10. Detailed Design

### 10.1 Compositor Architecture

#### 10.1.1 Main Compositor Class
```python
class AdCompositor:
    """Creates advertisement images from product data."""
    
    def __init__(self, fonts_dir: Path) -> None:
        """Initialize compositor with fonts directory."""
        self.fonts_dir = fonts_dir
        self.font_cache: Dict[str, ImageFont.FreeTypeFont] = {}
        self._load_fonts()
        
    def compose(
        self,
        product_path: Path,
        nobg_path: Optional[Path],
        use_original: bool,
        row: pd.Series,
        output: Path,
        template_name: str = "default",
    ) -> None:
        """Compose advertisement image."""
        # Composition logic
        pass
        
    def placeholder(self, query: str, dest: Path) -> Path:
        """Generate placeholder image for failed products."""
        # Placeholder logic
        pass
```

#### 10.1.2 Composition Stages
1. **Template Selection**
   - Choose appropriate layout based on product type
   - Load template definition and parameters

2. **Background Preparation**
   - Create base canvas with specified dimensions
   - Apply background colors or gradients
   - Add decorative elements

3. **Image Integration**
   - Load and position product image
   - Apply background removal if applicable
   - Add visual effects (shadows, borders)

4. **Text Rendering**
   - Render product title and description
   - Add pricing and promotional information
   - Include call-to-action elements
   - Apply styling and formatting

5. **Branding Application**
   - Add logo or watermark
   - Apply brand color schemes
   - Ensure consistent styling

6. **Quality Assurance**
   - Verify layout integrity
   - Check text readability
   - Validate image quality
   - Ensure proper sizing

### 10.2 Text Handling

#### 10.2.1 Text Rendering Engine
```python
def _render_text(
    self,
    canvas: Image.Image,
    text: str,
    position: Tuple[int, int],
    font_family: str,
    font_size: int,
    color: Tuple[int, int, int],
    max_width: Optional[int] = None,
) -> None:
    """Render text with automatic sizing and wrapping."""
    # Text rendering logic
    pass
```

#### 10.2.2 Font Management
- Font loading from custom directory
- System font fallback mechanisms
- Font caching for performance
- Dynamic font sizing based on content

### 10.3 Visual Effects

#### 10.3.1 Shadow Generation
```python
def _add_shadow(
    self,
    image: Image.Image,
    offset: Tuple[int, int] = (5, 5),
    blur_radius: int = 5,
    color: Tuple[int, int, int] = (0, 0, 0)
) -> Image.Image:
    """Add drop shadow to image."""
    # Shadow implementation
    pass
```

#### 10.3.2 Gradient Backgrounds
```python
def _create_gradient_background(
    self,
    size: Tuple[int, int],
    color1: Tuple[int, int, int],
    color2: Tuple[int, int, int],
    direction: str = "vertical"
) -> Image.Image:
    """Create gradient background."""
    # Gradient implementation
    pass
```

### 10.4 Placeholder Generation

#### 10.4.1 Placeholder Design
- Clear "ADVERTISEMENT FAILED" indicator
- Reason for failure (e.g., "NO IMAGE FOUND")
- Product information still visible
- Distinct color scheme to differentiate from real ads

#### 10.4.2 Error Information
- Search query used
- Failure timestamp
- Error category (search, download, processing)
- Attempt count

---

## 11. Implementation Plan

### 11.1 Phase 1: Core Composition
- Implement basic image and text composition
- Add template support
- Create placeholder generation

### 11.2 Phase 2: Visual Enhancements
- Add shadow and gradient effects
- Implement advanced text formatting
- Add font management system

### 11.3 Phase 3: Optimization
- Profile and optimize rendering performance
- Add visual regression testing
- Enhance error handling and logging

---

## 12. Monitoring and Logging

### 12.1 Composition Logging
- Log composition success/failure
- Report rendering performance metrics
- Track common error conditions
- Monitor font loading issues

### 12.2 Quality Metrics
- Output file size and quality
- Text rendering accuracy
- Layout consistency
- Placeholder usage frequency

---

*Document Version: 1.0*
*Last Updated: February 18, 2026*