# test_verifier.py
from pathlib import Path
from PIL import Image
import numpy as np

from config.settings import cfg
from imaging.verifier import ImageVerifier

# Create test image
img = Image.fromarray(np.random.randint(0, 255, (300, 300, 3), dtype=np.uint8))

# Initialize verifier with models_dir
verifier = ImageVerifier(cfg.verify, models_dir=cfg.paths.models_dir)

print("Status:", verifier.stats())

if verifier.is_available:
    result = verifier.verify(img, "red sports car")
    print("Result:", result.summary())
else:
    print("Models not loaded — check logs above")