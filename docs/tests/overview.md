# Tests Module Overview

The `tests/` module contains unit tests for the Ad Generator application. These tests ensure the code works correctly and help catch regressions when changes are made.

## 📁 Module Structure

```
tests/
├── conftest.py         # Shared fixtures and configuration
├── test_downloader.py  # Tests for image downloader
├── test_pipeline.py    # Tests for pipeline
├── test_search.py      # Tests for search engines
├── text_cleaner.py     # Tests for text cleaning utilities
└── check.py            # Quick verification script
```

## 🎯 Test Coverage

| Module | Test File | What's Tested |
|--------|-----------|---------------|
| `imaging/downloader.py` | `test_downloader.py` | Download, validation, deduplication |
| `search/manager.py` | `test_search.py` | Engine selection, fallback, deduplication |
| `core/pipeline.py` | `test_pipeline.py` | Pipeline orchestration |
| `utils/text_cleaner.py` | `text_cleaner.py` | Query cleaning, validation |

## 🚀 Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run Specific Test File
```bash
pytest tests/test_downloader.py
```

### Run with Verbose Output
```bash
pytest tests/ -v
```

### Run with Coverage
```bash
pytest tests/ --cov=. --cov-report=html
```

## 📝 Test Details

### test_downloader.py

Tests for the [`ImageDownloader`](imaging/downloader.py) class:

```python
class TestImageDownloader:
    def test_empty_results(self, downloader, tmp_dir):
        """Test that empty results return failure."""
        result = downloader.download_best([], tmp_dir / "out.jpg")
        assert not result.success
    
    def test_valid_download(self, mock_fetch, downloader, valid_image_bytes, tmp_dir):
        """Test successful download of valid image."""
        # Tests that a valid image is downloaded and saved correctly
    
    def test_skips_small_images(self, mock_fetch, downloader, tmp_dir):
        """Test that small images are rejected."""
        # Tests that 10x10 image is rejected (< 100px minimum)
    
    def test_dedup_by_hash(self, mock_fetch, downloader, valid_image_bytes, tmp_dir):
        """Test that duplicate images are skipped."""
        # Tests hash-based deduplication
```

**Key Test Cases**:
- ✅ Empty results → failure
- ✅ Valid image → success
- ✅ Small images → rejected
- ✅ Duplicate hash → second download fails

### test_search.py

Tests for the [`SearchManager`](search/manager.py) and [`ImageResult`](search/base.py):

```python
class TestSearchManager:
    def test_returns_results_from_first_engine(self, mock_google):
        """Test that results come from first successful engine."""
    
    def test_falls_back_when_first_engine_empty(self, mock_ddg, mock_google):
        """Test fallback to second engine when first fails."""
    
    def test_deduplicates_urls(self):
        """Test URL deduplication across engines."""
    
    def test_stops_early_when_enough(self, mock_google):
        """Test that search stops when enough results found."""

class TestImageResult:
    def test_default_values(self):
        """Test ImageResult default values."""
        r = ImageResult(url="http://x.com/a.jpg", source="google")
        assert r.width == 0
        assert r.height == 0
        assert r.title == ""
```

**Key Test Cases**:
- ✅ First engine returns results
- ✅ Fallback to second engine
- ✅ URL deduplication
- ✅ Early stopping when enough results
- ✅ Default values for ImageResult

## 🔧 Test Fixtures

### Fixtures in conftest.py

Shared fixtures are defined in `conftest.py`:

```python
@pytest.fixture
def tmp_dir(tmp_path):
    """Create a temporary directory for test files."""
    return tmp_path

@pytest.fixture
def sample_config():
    """Return a sample configuration for testing."""
    return AppConfig()
```

### Fixtures in test_downloader.py

```python
@pytest.fixture
def downloader():
    """Create an ImageDownloader instance for testing."""
    return ImageDownloader(
        cfg=ImageQualityConfig(),
        hashes=ThreadSafeSet(),
        timeout=5,
    )

@pytest.fixture
def valid_image_bytes():
    """Generate a valid test image (500x500 with random colors)."""
    img = Image.new("RGB", (500, 500))
    arr = np.random.randint(0, 255, (500, 500, 3), dtype=np.uint8)
    img = Image.fromarray(arr)
    buf = BytesIO()
    img.save(buf, "JPEG", quality=95)
    return buf.getvalue()
```

## 🧪 Testing Patterns

### Mocking External Dependencies

Tests mock network requests to avoid hitting real servers:

```python
@patch("imaging.downloader.ImageDownloader._fetch")
def test_valid_download(self, mock_fetch, downloader, valid_image_bytes, tmp_dir):
    mock_fetch.return_value = valid_image_bytes  # Return fake image data
    # ... test code ...
```

### Using Fixtures for Setup

```python
def test_empty_results(self, downloader, tmp_dir):
    # `downloader` and `tmp_dir` are injected automatically
    result = downloader.download_best([], tmp_dir / "out.jpg")
    assert not result.success
```

### Testing Edge Cases

```python
def test_empty_results(self, downloader, tmp_dir):
    """Test with empty input."""
    
def test_skips_small_images(self, mock_fetch, downloader, tmp_dir):
    """Test with invalid (too small) images."""
    
def test_dedup_by_hash(self, mock_fetch, downloader, valid_image_bytes, tmp_dir):
    """Test duplicate detection."""
```

## 📊 Quick Verification Script

The `check.py` script provides a quick way to verify the setup:

```bash
python tests/check.py
```

This typically runs basic checks like:
- Can import all modules?
- Can load configuration?
- Are required files present?

## 🔄 Continuous Integration

For CI/CD pipelines, tests can be run with:

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov
      - run: pytest tests/ -v --cov=.
```

## ✅ Test Best Practices

1. **Use descriptive test names**: `test_skips_small_images` not `test_1`
2. **One assertion per test**: Keep tests focused
3. **Use fixtures for common setup**: Don't repeat setup code
4. **Mock external dependencies**: Don't hit real servers
5. **Test edge cases**: Empty input, invalid data, errors

## 🔗 Related Documentation

- [Image Downloader](../imaging/downloader.md)
- [Search Manager](../search/manager.md)
- [Text Cleaner](../utils/text-cleaner.md)

---

**Next**: [README.md](../README.md) → Project overview and quick start
