"""Integration test for the full pipeline."""

from unittest.mock import MagicMock, patch

import pytest

from core.pipeline import AdPipeline, build_query
import pandas as pd


class TestBuildQuery:

    def test_uses_keywords_first(self):
        row = pd.Series({
            "keywords": "red sneakers running",
            "object_detected": "shoes",
            "text": "Buy these amazing shoes now",
        })
        assert build_query(row) == "red sneakers running"

    def test_falls_back_to_object(self):
        row = pd.Series({
            "keywords": "",
            "object_detected": "laptop",
            "text": "Great computer for sale",
        })
        assert build_query(row) == "laptop"

    def test_falls_back_to_text(self):
        row = pd.Series({
            "keywords": "",
            "object_detected": "general",
            "text": "Amazing deal today only",
        })
        assert build_query(row) == "Amazing deal today"

    def test_ignores_nan(self):
        row = pd.Series({
            "keywords": "nan",
            "object_detected": "none",
            "text": "Buy now save more",
        })
        assert build_query(row) == "Buy now save"


class TestPipelineInit:

    def test_creates_directories(self, test_config):
        pipeline = AdPipeline(test_config)
        assert test_config.paths.images_dir.exists()
        assert test_config.paths.temp_dir.exists()

    def test_loads_csv(self, test_config):
        pipeline = AdPipeline(test_config)
        assert len(pipeline.df) == 3
        assert "image_path" in pipeline.df.columns