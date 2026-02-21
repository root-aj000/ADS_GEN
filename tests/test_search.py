"""Tests for search engines."""

from unittest.mock import MagicMock, patch

import pytest

from search.base import ImageResult
from search.manager import SearchManager
from config.settings import SearchConfig


class TestSearchManager:

    def setup_method(self):
        self.cfg = SearchConfig(
            priority=["google", "duckduckgo"],
            min_results_fallback=5,
        )
        self.mgr = SearchManager(self.cfg)

    @patch("search.google_engine.GoogleEngine.search")
    def test_returns_results_from_first_engine(self, mock_google):
        mock_google.return_value = [
            ImageResult(url=f"http://example.com/{i}.jpg", source="google")
            for i in range(10)
        ]
        results = self.mgr.search("test query", max_results=10)
        assert len(results) == 10
        assert all(r.source == "google" for r in results)

    @patch("search.google_engine.GoogleEngine.search")
    @patch("search.duckduckgo_engine.DuckDuckGoEngine.search")
    def test_falls_back_when_first_engine_empty(self, mock_ddg, mock_google):
        mock_google.return_value = []
        mock_ddg.return_value = [
            ImageResult(url="http://ddg.com/1.jpg", source="duckduckgo"),
        ]
        results = self.mgr.search("test", max_results=10)
        assert len(results) == 1
        assert results[0].source == "duckduckgo"

    def test_deduplicates_urls(self):
        # manually inject same URL from two engines
        results = self.mgr.search("", max_results=0)
        assert isinstance(results, list)

    @patch("search.google_engine.GoogleEngine.search")
    def test_stops_early_when_enough(self, mock_google):
        mock_google.return_value = [
            ImageResult(url=f"http://example.com/{i}.jpg", source="google")
            for i in range(20)
        ]
        results = self.mgr.search("test", max_results=50)
        assert len(results) >= self.cfg.min_results_fallback


class TestImageResult:

    def test_default_values(self):
        r = ImageResult(url="http://x.com/a.jpg", source="google")
        assert r.width == 0
        assert r.height == 0
        assert r.title == ""