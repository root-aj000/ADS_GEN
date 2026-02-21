"""Tests for image downloader."""

from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from imaging.downloader import ImageDownloader, DownloadResult
from search.base import ImageResult
from config.settings import ImageQualityConfig
from utils.concurrency import ThreadSafeSet


@pytest.fixture
def downloader():
    return ImageDownloader(
        cfg=ImageQualityConfig(),
        hashes=ThreadSafeSet(),
        timeout=5,
    )


@pytest.fixture
def valid_image_bytes():
    """Generate a valid test image."""
    img = Image.new("RGB", (500, 500))
    arr = np.random.randint(0, 255, (500, 500, 3), dtype=np.uint8)
    img = Image.fromarray(arr)
    buf = BytesIO()
    img.save(buf, "JPEG", quality=95)
    return buf.getvalue()


class TestImageDownloader:

    def test_empty_results(self, downloader, tmp_dir):
        result = downloader.download_best([], tmp_dir / "out.jpg")
        assert not result.success

    @patch("imaging.downloader.ImageDownloader._fetch")
    def test_valid_download(self, mock_fetch, downloader, valid_image_bytes, tmp_dir):
        mock_fetch.return_value = valid_image_bytes
        results = [
            ImageResult(url="http://example.com/img.jpg", source="test"),
        ]
        dl = downloader.download_best(results, tmp_dir / "out.jpg")
        assert dl.success
        assert dl.path is not None
        assert dl.path.exists()

    @patch("imaging.downloader.ImageDownloader._fetch")
    def test_skips_small_images(self, mock_fetch, downloader, tmp_dir):
        # 10x10 image
        img = Image.new("RGB", (10, 10), (255, 0, 0))
        buf = BytesIO()
        img.save(buf, "JPEG")
        mock_fetch.return_value = buf.getvalue()

        results = [
            ImageResult(url="http://example.com/tiny.jpg", source="test"),
        ]
        dl = downloader.download_best(results, tmp_dir / "out.jpg")
        assert not dl.success

    @patch("imaging.downloader.ImageDownloader._fetch")
    def test_dedup_by_hash(self, mock_fetch, downloader, valid_image_bytes, tmp_dir):
        mock_fetch.return_value = valid_image_bytes
        results = [
            ImageResult(url="http://example.com/1.jpg", source="test"),
            ImageResult(url="http://example.com/2.jpg", source="test"),
        ]
        dl1 = downloader.download_best(results[:1], tmp_dir / "a.jpg")
        dl2 = downloader.download_best(results[1:], tmp_dir / "b.jpg")
        assert dl1.success
        assert not dl2.success  # same hash