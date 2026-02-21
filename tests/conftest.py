"""Shared test fixtures."""

import shutil
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from config.settings import AppConfig, PathConfig


@pytest.fixture
def tmp_dir():
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_csv(tmp_dir):
    csv_path = tmp_dir / "input" / "main.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame({
        "text": [
            "Buy Nike shoes now! 50% off",
            "Fresh organic coffee beans",
            "Samsung Galaxy S24 Ultra",
        ],
        "keywords": ["nike shoes", "coffee beans", "samsung galaxy"],
        "object_detected": ["shoes", "coffee", "phone"],
        "dominant_colour": ["Red", "Brown", "Black"],
        "monetary_mention": ["50% off", "", "$999"],
        "call_to_action": ["Shop Now", "Order Today", "Buy Now"],
    })
    df.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def test_config(tmp_dir, sample_csv):
    paths = PathConfig(
        root=tmp_dir,
        csv_input=sample_csv,
        csv_output=tmp_dir / "output" / "result.csv",
        images_dir=tmp_dir / "output" / "images",
        temp_dir=tmp_dir / "temp",
        progress_db=tmp_dir / "progress.db",
        cache_db=tmp_dir / "cache.db",
        log_file=tmp_dir / "test.log",
        fonts_dir=tmp_dir / "fonts",
        proxy_file=tmp_dir / "proxies.txt",
    )
    cfg = AppConfig(paths=paths)
    cfg.paths.ensure()
    return cfg