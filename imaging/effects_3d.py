"""
TRUE 3D object generation from 2D product images.

Downloads models from HuggingFace to data/models/.
Uses AI to generate real 3D meshes with geometry + texture.

Model Toggles (set True/False):
    USE_TRIPOSR        → stabilityai/TripoSR
    USE_SHAP_E         → openai/shap-e  
    USE_STABLE_FAST_3D → stabilityai/stable-fast-3d
    USE_NUMPY_FALLBACK → always available

Install:
    pip install huggingface_hub torch trimesh pyvista rembg scipy

    # For TripoSR:
    pip install tsr

    # For Shap-E:  
    pip install shap-e

    # For Stable Fast 3D:
    pip install sf3d

Pre-download models:
    python -m imaging.effects_3d --download
"""

from __future__ import annotations

import gc
import hashlib
import io
import math
import os
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MODEL TOGGLES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USE_TRIPOSR:        bool = True
USE_SHAP_E:         bool = False
USE_STABLE_FAST_3D: bool = False
USE_NUMPY_FALLBACK: bool = True
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MODELS_DIR = Path("data/models")
MESH_CACHE_DIR = Path("data/cache/meshes")

# HuggingFace model repos
HF_MODELS = {
    "triposr":        "stabilityai/TripoSR",
    "shap_e":         "openai/shap-e",
    "stable_fast_3d": "stabilityai/stable-fast-3d",
}


def _ensure_dirs():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    MESH_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_rgba(img: Image.Image) -> Image.Image:
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    return img


def _image_hash(img: Image.Image) -> str:
    arr = np.array(img.resize((64, 64)))
    return hashlib.md5(arr.tobytes()).hexdigest()[:12]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  HUGGINGFACE MODEL DOWNLOADER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ModelDownloader:
    """
    Downloads models from HuggingFace Hub to data/models/.
    
    All models are stored locally — no re-download on next run.
    """

    @staticmethod
    def _get_hf_hub():
        try:
            import huggingface_hub
            return huggingface_hub
        except ImportError:
            raise ImportError(
                "huggingface_hub not installed!\n"
                "  pip install huggingface_hub"
            )

    @classmethod
    def download(
        cls,
        repo_id: str,
        local_name: str,
        revision: str = "main",
        force: bool = False,
    ) -> Path:
        """
        Download a model from HuggingFace to data/models/<local_name>/.

        Args:
            repo_id:    HuggingFace repo (e.g. "stabilityai/TripoSR")
            local_name: Local folder name under data/models/
            revision:   Branch/tag
            force:      Re-download even if exists

        Returns:
            Path to local model directory
        """
        hf = cls._get_hf_hub()
        _ensure_dirs()

        local_dir = MODELS_DIR / local_name

        # Check if already downloaded
        if local_dir.exists() and not force:
            # Verify it has content
            files = list(local_dir.rglob("*"))
            model_files = [f for f in files if f.is_file() and f.suffix in (
                ".bin", ".pt", ".pth", ".ckpt", ".safetensors",
                ".json", ".yaml", ".yml", ".txt",
            )]
            if len(model_files) >= 2:
                print(f"  ✅ {repo_id} already downloaded → {local_dir}")
                return local_dir

        print(f"\n  📥 Downloading {repo_id}...")
        print(f"     Destination: {local_dir}")
        print(f"     This may take several minutes on first run...\n")

        try:
            downloaded_path = hf.snapshot_download(
                repo_id=repo_id,
                local_dir=str(local_dir),
                local_dir_use_symlinks=False,
                revision=revision,
                ignore_patterns=[
                    "*.md",
                    "*.txt",
                    ".gitattributes",
                    "*.git*",
                    "examples/*",
                    "docs/*",
                ],
            )

            # Verify download
            size = sum(
                f.stat().st_size
                for f in Path(downloaded_path).rglob("*")
                if f.is_file()
            )
            size_mb = size / (1024 * 1024)
            print(f"  ✅ Downloaded {repo_id} ({size_mb:.0f} MB) → {local_dir}")

            return Path(downloaded_path)

        except Exception as e:
            print(f"  ❌ Download failed: {e}")
            raise

    @classmethod
    def download_file(
        cls,
        repo_id: str,
        filename: str,
        local_name: str,
    ) -> Path:
        """Download a single file from HuggingFace."""
        hf = cls._get_hf_hub()
        _ensure_dirs()

        local_dir = MODELS_DIR / local_name
        local_dir.mkdir(parents=True, exist_ok=True)

        target = local_dir / filename
        if target.exists():
            print(f"  ✅ {filename} already exists")
            return target

        print(f"  📥 Downloading {repo_id}/{filename}...")

        path = hf.hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=str(local_dir),
            local_dir_use_symlinks=False,
        )

        print(f"  ✅ Downloaded → {path}")
        return Path(path)

    @classmethod
    def is_downloaded(cls, local_name: str) -> bool:
        """Check if a model is already downloaded."""
        local_dir = MODELS_DIR / local_name
        if not local_dir.exists():
            return False
        files = [
            f for f in local_dir.rglob("*")
            if f.is_file() and f.suffix in (
                ".bin", ".pt", ".pth", ".ckpt", ".safetensors",
                ".json", ".yaml",
            )
        ]
        return len(files) >= 2

    @classmethod
    def model_size(cls, local_name: str) -> str:
        """Get model size on disk."""
        local_dir = MODELS_DIR / local_name
        if not local_dir.exists():
            return "not downloaded"
        size = sum(f.stat().st_size for f in local_dir.rglob("*") if f.is_file())
        if size > 1e9:
            return f"{size / 1e9:.1f} GB"
        return f"{size / 1e6:.0f} MB"

    @classmethod
    def download_all(cls, force: bool = False):
        """Download all enabled models."""
        print("\n" + "=" * 60)
        print("  📦 DOWNLOADING 3D MODELS FROM HUGGINGFACE")
        print("=" * 60 + "\n")

        if USE_TRIPOSR:
            try:
                TripoSRGenerator.download(force=force)
                # Check deps
                TripoSRGenerator.install_deps()
            except Exception as e:
                print(f"  ⚠️  TripoSR download failed: {e}")

        if USE_SHAP_E:
            try:
                ShapEGenerator.download(force=force)
            except Exception as e:
                print(f"  ⚠️  Shap-E download failed: {e}")

        if USE_STABLE_FAST_3D:
            try:
                StableFast3DGenerator.download(force=force)
            except Exception as e:
                print(f"  ⚠️  Stable Fast 3D download failed: {e}")

        print("\n  ✅ Download complete!")
        print(f"  📁 Models stored in: {MODELS_DIR.absolute()}\n")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  IMAGE PREPROCESSOR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _preprocess_for_3d(
    img: Image.Image,
    target_size: int = 512,
    remove_bg: bool = True,
) -> Image.Image:
    """Prepare image for 3D model: remove BG, pad square, resize."""
    img = _ensure_rgba(img)

    if remove_bg:
        try:
            from rembg import remove as rembg_remove
            alpha = np.array(img.split()[3])
            transparent_ratio = (alpha < 30).sum() / alpha.size
            if transparent_ratio < 0.1:
                img_bytes = io.BytesIO()
                img.save(img_bytes, format="PNG")
                img_bytes.seek(0)
                result_bytes = rembg_remove(img_bytes.read())
                img = Image.open(io.BytesIO(result_bytes)).convert("RGBA")
        except ImportError:
            pass

    # Pad to square
    w, h = img.size
    max_dim = max(w, h)
    padded = Image.new("RGBA", (max_dim, max_dim), (0, 0, 0, 0))
    padded.paste(img, ((max_dim - w) // 2, (max_dim - h) // 2), img)
    padded = padded.resize((target_size, target_size), Image.Resampling.LANCZOS)

    return padded


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MESH RENDERER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MeshRenderer:
    """Renders trimesh.Trimesh → PIL Image using PyVista."""

    @staticmethod
    def render(
        mesh,
        rotation: Tuple[float, float, float] = (15, 20, 0),
        size: Tuple[int, int] = (1024, 1024),
        zoom: float = 1.3,
    ) -> Image.Image:
        try:
            return MeshRenderer._render_pyvista(mesh, rotation, size, zoom)
        except Exception as e:
            warnings.warn(f"PyVista render failed: {e}")
            try:
                return MeshRenderer._render_trimesh_fallback(mesh, rotation, size)
            except Exception:
                return Image.new("RGBA", size, (100, 100, 100, 255))

    @staticmethod
    # In MeshRenderer._render_pyvista()
    def _render_pyvista(mesh, rotation, size, zoom):
        import pyvista as pv
        import tempfile
        import os

        vertices = np.array(mesh.vertices, dtype=np.float64)
        faces_raw = np.array(mesh.faces, dtype=np.int64)
        faces_pv = np.column_stack([
            np.full(len(faces_raw), 3, dtype=np.int64), faces_raw,
        ]).ravel()

        pv_mesh = pv.PolyData(vertices, faces_pv)

        # === FIX: Handle UV Textures ===
        has_texture = False
        texture_path = None

        try:
            if hasattr(mesh.visual, 'image') and mesh.visual.image is not None:
                # Save texture to temp file for PyVista
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    mesh.visual.image.save(tmp.name)
                    texture_path = tmp.name
                    has_texture = True
                    print(f"  🎨 Texture loaded: {tmp.name}")
        except Exception as e:
            print(f"  ⚠️  Texture load failed: {e}")

        # Fallback to vertex colors
        has_colors = False
        if not has_texture:
            try:
                if hasattr(mesh.visual, 'vertex_colors') and mesh.visual.vertex_colors is not None:
                    vc = np.array(mesh.visual.vertex_colors)
                    if vc.shape[0] == len(vertices) and vc.shape[1] >= 3:
                        pv_mesh['RGB'] = vc[:, :3].astype(np.uint8)
                        has_colors = True
            except:
                pass

        # Center and normalize
        center = pv_mesh.center
        pv_mesh.points -= center
        bounds = pv_mesh.bounds
        max_extent = max(
            bounds[1] - bounds[0],
            bounds[3] - bounds[2],
            bounds[5] - bounds[4],
        )
        if max_extent > 0:
            pv_mesh.points /= (max_extent / 2)

        # Rotate
        rx, ry, rz = rotation
        if rx: pv_mesh = pv_mesh.rotate_x(rx, inplace=False)
        if ry: pv_mesh = pv_mesh.rotate_y(ry, inplace=False)
        if rz: pv_mesh = pv_mesh.rotate_z(rz, inplace=False)

        # Plot
        plotter = pv.Plotter(off_screen=True, window_size=list(size))
        plotter.set_background("white")  # Changed from black

        mesh_kwargs = {
            "smooth_shading": True,
            "lighting": True,
            "pbr": False,  # Disable PBR for better texture display
            "metallic": 0.0,
            "roughness": 0.5,
        }

        if has_texture and texture_path:
            mesh_kwargs["texture"] = pv.read_texture(texture_path)
            mesh_kwargs["color"] = "white"  # White base for texture
        elif has_colors:
            mesh_kwargs["scalars"] = "RGB"
            mesh_kwargs["rgb"] = True
        else:
            mesh_kwargs["color"] = [0.8, 0.8, 0.8]  # Light gray fallback

        plotter.add_mesh(pv_mesh, **mesh_kwargs)

        # Better lighting
        plotter.remove_all_lights()
        plotter.add_light(pv.Light(position=(3, 2, 5), focal_point=(0, 0, 0), intensity=1.0))
        plotter.add_light(pv.Light(position=(-2, -1, 3), focal_point=(0, 0, 0), intensity=0.6))
        plotter.add_light(pv.Light(position=(0, -3, 1), focal_point=(0, 0, 0), intensity=0.4))
        plotter.add_light(pv.Light(position=(0, 0, 5), focal_point=(0, 0, 0), intensity=0.5))

        plotter.camera_position = "xy"
        plotter.camera.zoom(zoom)

        rendered = plotter.screenshot(transparent_background=True, return_img=True)
        plotter.close()

        # Cleanup temp texture
        if texture_path and os.path.exists(texture_path):
            try:
                os.unlink(texture_path)
            except:
                pass

        if rendered.shape[2] == 4:
            result = Image.fromarray(rendered, "RGBA")
        else:
            result = Image.fromarray(rendered, "RGB").convert("RGBA")

        return _crop_to_content(result)
    @staticmethod
    def _render_trimesh_fallback(mesh, rotation, size):
        import trimesh
        scene = trimesh.Scene(mesh)
        rot = trimesh.transformations.euler_matrix(
            math.radians(rotation[0]),
            math.radians(rotation[1]),
            math.radians(rotation[2]),
        )
        scene.apply_transform(rot)
        png_data = scene.save_image(resolution=size)
        return Image.open(io.BytesIO(png_data)).convert("RGBA")


def _crop_to_content(img: Image.Image, padding: int = 20) -> Image.Image:
    if img.mode != "RGBA":
        return img
    alpha = np.array(img.split()[3])
    rows = np.any(alpha > 10, axis=1)
    cols = np.any(alpha > 10, axis=0)
    if not rows.any() or not cols.any():
        return img
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    rmin = max(0, rmin - padding)
    rmax = min(img.height - 1, rmax + padding)
    cmin = max(0, cmin - padding)
    cmax = min(img.width - 1, cmax + padding)
    return img.crop((cmin, rmin, cmax + 1, rmax + 1))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TRIPOSR GENERATOR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TripoSRGenerator:
    """
    stabilityai/TripoSR — Single image → 3D mesh.

    Code:    GitHub  → VAST-AI-Research/TripoSR
    Weights: HuggingFace → stabilityai/TripoSR (already downloaded)

    Deps: pip install torch einops omegaconf transformers trimesh PyMCubes
    """

    _model = None
    _device = None
    MODEL_REPO = "stabilityai/TripoSR"
    GITHUB_ZIP = "https://github.com/VAST-AI-Research/TripoSR/archive/refs/heads/main.zip"
    LOCAL_NAME = "TripoSR"

    @classmethod
    def _code_dir(cls) -> Path:
        """Where tsr/ source code lives."""
        return MODELS_DIR / cls.LOCAL_NAME / "code"

    @classmethod
    def _weights_dir(cls) -> Path:
        """Where model.ckpt + config.yaml live."""
        return MODELS_DIR / cls.LOCAL_NAME

    @classmethod
    def _download_code(cls, force: bool = False) -> Path:
        """Download tsr/ source code from GitHub."""
        import zipfile
        import requests

        code_dir = cls._code_dir()
        tsr_dir = code_dir / "tsr"

        if tsr_dir.exists() and (tsr_dir / "system.py").exists() and not force:
            print(f"  ✅ TripoSR code already exists → {code_dir}")
            return code_dir

        print(f"  📥 Downloading TripoSR source code from GitHub...")

        code_dir.mkdir(parents=True, exist_ok=True)
        zip_path = code_dir / "triposr.zip"

        # Download zip
        resp = requests.get(cls.GITHUB_ZIP, stream=True, timeout=60)
        resp.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"  📦 Extracting...")

        # Extract
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(code_dir)

        # GitHub zips have a root folder like "TripoSR-main/"
        # Move contents up
        extracted_dirs = [
            d for d in code_dir.iterdir()
            if d.is_dir() and d.name.startswith("TripoSR")
        ]

        if extracted_dirs:
            src = extracted_dirs[0]
            # Move tsr/ folder to code_dir/tsr/
            src_tsr = src / "tsr"
            dst_tsr = code_dir / "tsr"
            if dst_tsr.exists():
                import shutil
                shutil.rmtree(dst_tsr)
            if src_tsr.exists():
                src_tsr.rename(dst_tsr)
                print(f"  ✅ tsr/ source code extracted")

            # Also copy requirements.txt if useful
            src_req = src / "requirements.txt"
            if src_req.exists():
                import shutil
                shutil.copy2(src_req, code_dir / "requirements.txt")

            # Clean up extracted folder
            import shutil
            shutil.rmtree(src, ignore_errors=True)

        # Clean up zip
        zip_path.unlink(missing_ok=True)

        # Verify
        if (code_dir / "tsr" / "system.py").exists():
            print(f"  ✅ TripoSR code ready → {code_dir}")
        else:
            print(f"  ❌ Failed — tsr/system.py not found!")
            print(f"     Contents of {code_dir}:")
            for f in sorted(code_dir.iterdir())[:10]:
                print(f"       {'📁' if f.is_dir() else '📄'} {f.name}")

        return code_dir

    @classmethod
    def _ensure_on_path(cls) -> bool:
        """Add code dir to sys.path so 'from tsr.system import TSR' works."""
        code_dir = cls._code_dir()
        tsr_check = code_dir / "tsr" / "system.py"

        if not tsr_check.exists():
            return False

        code_str = str(code_dir)
        if code_str not in sys.path:
            sys.path.insert(0, code_str)

        return True

    @classmethod
    def is_available(cls) -> bool:
        """Check if code downloaded + deps installed."""
        if not cls._ensure_on_path():
            return False
        try:
            from tsr.system import TSR
            return True
        except ImportError:
            return False
        except Exception:
            return False

    @classmethod
    def is_downloaded(cls) -> bool:
        """Check code + weights both exist."""
        has_code = (cls._code_dir() / "tsr" / "system.py").exists()
        weights_dir = cls._weights_dir()
        has_weights = (weights_dir / "model.ckpt").exists() or \
                      (weights_dir / "model.safetensors").exists()
        return has_code and has_weights

    @classmethod
    def download(cls, force: bool = False) -> Path:
        """Download both code (GitHub) and weights (HuggingFace)."""
        model_dir = cls._weights_dir()

        if cls.is_downloaded() and not force:
            print(f"  ✅ TripoSR fully downloaded")
            print(f"     Code:    {cls._code_dir()}")
            print(f"     Weights: {model_dir / 'model.ckpt'}")
            cls._ensure_on_path()
            return model_dir

        # 1. Download weights from HuggingFace (if not already)
        weights_exist = (model_dir / "model.ckpt").exists()
        if not weights_exist or force:
            print(f"\n  📥 Step 1/2: Downloading weights from HuggingFace...")
            ModelDownloader.download(cls.MODEL_REPO, cls.LOCAL_NAME, force=force)
        else:
            print(f"  ✅ Step 1/2: Weights already downloaded ({model_dir / 'model.ckpt'})")

        # 2. Download code from GitHub
        print(f"\n  📥 Step 2/2: Downloading code from GitHub...")
        cls._download_code(force=force)

        cls._ensure_on_path()
        return model_dir

    @classmethod
    def check_deps(cls) -> dict:
        deps = {}
        for pkg, mod in [
            ("torch", "torch"),
            ("torchvision", "torchvision"),
            ("einops", "einops"),
            ("omegaconf", "omegaconf"),
            ("transformers", "transformers"),
            ("trimesh", "trimesh"),
            ("PyMCubes", "mcubes"),
        ]:
            try:
                __import__(mod)
                deps[pkg] = True
            except ImportError:
                deps[pkg] = False
        return deps

    @classmethod
    def install_deps(cls):
        deps = cls.check_deps()
        missing = [k for k, v in deps.items() if not v]
        if not missing:
            print("  ✅ All TripoSR dependencies installed")
            return
        print(f"\n  ⚠️  Missing TripoSR dependencies:")
        for pkg in missing:
            print(f"     ❌ {pkg}")
        print(f"\n  Run: pip install {' '.join(missing)}\n")

    @classmethod
    def load_model(cls):
        if cls._model is not None:
            return cls._model

        # Download everything if needed
        cls.download()
        cls._ensure_on_path()

        # Check deps
        deps = cls.check_deps()
        missing = [k for k, v in deps.items() if not v]
        if missing:
            raise ImportError(
                f"Missing: {', '.join(missing)}\n"
                f"  pip install {' '.join(missing)}"
            )

        import torch
        from tsr.system import TSR

        cls._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        weights_dir = cls._weights_dir()
        print(f"  📦 Loading TripoSR")
        print(f"     Config:  {weights_dir / 'config.yaml'}")
        print(f"     Weights: {weights_dir / 'model.ckpt'}")
        print(f"     Device:  {cls._device}")

        cls._model = TSR.from_pretrained(
            str(weights_dir),
            config_name="config.yaml",
            weight_name="model.ckpt",
        )
        cls._model.renderer.set_chunk_size(8192)
        cls._model.to(cls._device)

        print(f"  ✅ TripoSR loaded and ready")
        return cls._model


    @classmethod
    # In TripoSRGenerator.generate_mesh()

    def generate_mesh(cls, img, resolution=256, use_cache=True):
        import torch
        import trimesh
        from PIL import Image
        import numpy as np
        import os

        _ensure_dirs()

        img_id = _image_hash(img)
        cache_path = MESH_CACHE_DIR / f"triposr_{img_id}.obj"
        texture_path = MESH_CACHE_DIR / f"triposr_{img_id}.png"

        if use_cache and cache_path.exists():
            print(f"  💾 Mesh cache hit: {cache_path.name}")
            mesh = trimesh.load(str(cache_path))
            # Load texture if exists
            if texture_path.exists():
                try:
                    tex = Image.open(texture_path)
                    mesh.visual = trimesh.visual.TextureVisuals(
                        uv=mesh.visual.uv,
                        image=tex
                    )
                except:
                    pass
            return mesh

        processed = _preprocess_for_3d(img, target_size=512)
        rgb_img = processed.convert("RGB")

        model = cls.load_model()

        with torch.no_grad():
            scene_codes = model([rgb_img], device=cls._device)

            # Generate mesh WITH texture
            meshes = model.extract_mesh(scene_codes, True, resolution=resolution)
            mesh = meshes[0]

        # Fix: Ensure normals face outward
        mesh.fix_normals()

        # Fix: Flip normals if needed (common TripoSR issue)
        if hasattr(mesh, 'face_normals'):
            # Check if majority of normals point inward
            center = mesh.vertices.mean(axis=0)
            face_centers = mesh.triangles_center
            to_center = center - face_centers
            dots = (mesh.face_normals * to_center).sum(axis=1)
            if (dots > 0).mean() > 0.5:  # Most faces point inward
                mesh.invert()
                print("  🔧 Flipped mesh normals")

        # Save mesh + texture
        if use_cache:
            # Export with materials
            mesh.export(str(cache_path))

            # Save texture separately if available
            if hasattr(mesh.visual, 'image') and mesh.visual.image is not None:
                mesh.visual.image.save(str(texture_path))
                print(f"  💾 Texture saved → {texture_path.name}")

            print(f"  💾 Mesh cached → {cache_path.name}")

        return mesh



    @classmethod
    def render(cls, img, rotation=(15, 20, 0), resolution=256,
               render_size=(1024, 1024), zoom=1.3):
        mesh = cls.generate_mesh(img, resolution=resolution)
        return MeshRenderer.render(mesh, rotation, render_size, zoom)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SHAP-E GENERATOR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ShapEGenerator:
    """
    openai/shap-e — Image → 3D via diffusion.

    Install:  pip install shap-e huggingface_hub trimesh
    Model:    ~2GB, auto-downloaded from HuggingFace
    Speed:    ~10s GPU, ~120s CPU
    """

    _xm = None
    _model = None
    _diffusion = None
    _device = None
    MODEL_REPO = "openai/shap-e"
    LOCAL_NAME = "shap-e"

    @classmethod
    def is_available(cls) -> bool:
        try:
            from shap_e.models.download import load_model
            return True
        except ImportError:
            return False

    @classmethod
    def is_downloaded(cls) -> bool:
        return ModelDownloader.is_downloaded(cls.LOCAL_NAME)

    @classmethod
    def download(cls, force: bool = False) -> Path:
        """Download Shap-E model weights from HuggingFace."""
        hf = ModelDownloader._get_hf_hub()
        _ensure_dirs()

        local_dir = MODELS_DIR / cls.LOCAL_NAME
        local_dir.mkdir(parents=True, exist_ok=True)

        # Shap-E has specific weight files
        weight_files = [
            "transmitter.pt",
            "image300M.pt",
            "diffusion_config.yaml",
        ]

        for filename in weight_files:
            target = local_dir / filename
            if target.exists() and not force:
                print(f"  ✅ {filename} exists")
                continue

            print(f"  📥 Downloading {cls.MODEL_REPO}/{filename}...")
            try:
                hf.hf_hub_download(
                    repo_id=cls.MODEL_REPO,
                    filename=filename,
                    local_dir=str(local_dir),
                    local_dir_use_symlinks=False,
                )
                print(f"  ✅ {filename} downloaded")
            except Exception as e:
                print(f"  ⚠️  {filename} failed: {e}")
                # Try snapshot download as fallback
                ModelDownloader.download(cls.MODEL_REPO, cls.LOCAL_NAME, force=force)
                break

        return local_dir

    @classmethod
    def load_model(cls):
        if cls._model is not None:
            return cls._model, cls._xm, cls._diffusion

        import torch
        from shap_e.models.download import load_model, load_config
        from shap_e.diffusion.gaussian_diffusion import diffusion_from_config

        # Download if needed
        model_dir = cls.download()

        # Point shap-e to our local dir
        os.environ["SHAP_E_MODEL_DIR"] = str(model_dir)

        cls._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"  📦 Loading Shap-E from {model_dir}")
        print(f"     Device: {cls._device}")

        cls._xm = load_model("transmitter", device=cls._device)
        cls._model = load_model("image300M", device=cls._device)
        cls._diffusion = diffusion_from_config(load_config("diffusion"))

        print(f"  ✅ Shap-E loaded")
        return cls._model, cls._xm, cls._diffusion

    @classmethod
    def generate_mesh(cls, img, resolution=256, use_cache=True):
        import torch
        import trimesh

        _ensure_dirs()

        img_id = _image_hash(img)
        cache_path = MESH_CACHE_DIR / f"triposr_{img_id}.obj"

        if use_cache and cache_path.exists():
            print(f"  💾 Mesh cache hit: {cache_path.name}")
            return trimesh.load(str(cache_path))

        processed = _preprocess_for_3d(img, target_size=512)
        rgb_img = processed.convert("RGB")

        model = cls.load_model()

        with torch.no_grad():
            scene_codes = model([rgb_img], device=cls._device)

            # WORKING: True as 2nd positional arg
            meshes = model.extract_mesh(scene_codes, True, resolution=resolution)

        mesh_data = meshes[0]

        # Convert to trimesh.Trimesh
        if isinstance(mesh_data, trimesh.Trimesh):
            mesh = mesh_data
        elif isinstance(mesh_data, (list, tuple)):
            if len(mesh_data) == 3:
                verts, faces, colors = mesh_data
            else:
                verts, faces = mesh_data[:2]
                colors = None

            if hasattr(verts, 'detach'):
                verts = verts.detach().cpu().numpy()
            if hasattr(faces, 'detach'):
                faces = faces.detach().cpu().numpy()
            if colors is not None and hasattr(colors, 'detach'):
                colors = colors.detach().cpu().numpy()
                if colors.max() <= 1.0:
                    colors = (colors * 255).astype(np.uint8)

            mesh = trimesh.Trimesh(vertices=verts, faces=faces, vertex_colors=colors)
        else:
            # Object with .vertices, .faces attributes
            verts = mesh_data.vertices
            faces = mesh_data.faces
            colors = getattr(mesh_data, 'vertex_colors', None)

            if hasattr(verts, 'detach'):
                verts = verts.detach().cpu().numpy()
            if hasattr(faces, 'detach'):
                faces = faces.detach().cpu().numpy()
            if colors is not None and hasattr(colors, 'detach'):
                colors = colors.detach().cpu().numpy()
                if colors.max() <= 1.0:
                    colors = (colors * 255).astype(np.uint8)

            mesh = trimesh.Trimesh(vertices=verts, faces=faces, vertex_colors=colors)

        if use_cache:
            mesh.export(str(cache_path))
            print(f"  💾 Mesh cached → {cache_path.name}")

        return mesh  
    
    
    
    
    @classmethod
    def render(cls, img, rotation=(15, 20, 0), render_size=(1024, 1024), zoom=1.3):
        mesh = cls.generate_mesh(img)
        return MeshRenderer.render(mesh, rotation, render_size, zoom)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STABLE FAST 3D GENERATOR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class StableFast3DGenerator:
    """
    stabilityai/stable-fast-3d — Fastest image → 3D.

    Install:  pip install sf3d huggingface_hub trimesh
    Model:    ~2GB, auto-downloaded from HuggingFace
    Speed:    ~1s GPU (fastest!)
    """

    _model = None
    _device = None
    MODEL_REPO = "stabilityai/stable-fast-3d"
    LOCAL_NAME = "stable-fast-3d"

    @classmethod
    def is_available(cls) -> bool:
        try:
            from sf3d.system import SF3D
            return True
        except ImportError:
            return False

    @classmethod
    def is_downloaded(cls) -> bool:
        return ModelDownloader.is_downloaded(cls.LOCAL_NAME)

    @classmethod
    def download(cls, force: bool = False) -> Path:
        return ModelDownloader.download(cls.MODEL_REPO, cls.LOCAL_NAME, force=force)

    @classmethod
    def load_model(cls):
        if cls._model is not None:
            return cls._model

        import torch
        from sf3d.system import SF3D

        model_path = cls.download()

        cls._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"  📦 Loading Stable Fast 3D from {model_path}")
        print(f"     Device: {cls._device}")

        cls._model = SF3D.from_pretrained(
            str(model_path),
            config_name="config.yaml",
            weight_name="model.safetensors",
        )
        cls._model.to(cls._device)

        print(f"  ✅ Stable Fast 3D loaded")
        return cls._model

    @classmethod
    def generate_mesh(cls, img, resolution=256, use_cache=True):
        import torch
        import trimesh

        _ensure_dirs()

        img_id = _image_hash(img)
        cache_path = MESH_CACHE_DIR / f"sf3d_{img_id}.obj"
        if use_cache and cache_path.exists():
            print(f"  💾 Mesh cache hit: {cache_path.name}")
            return trimesh.load(str(cache_path))

        processed = _preprocess_for_3d(img, target_size=512)
        rgb_img = processed.convert("RGB")

        model = cls.load_model()

        with torch.no_grad():
            mesh = model.run_image(rgb_img, bake_resolution=resolution, remesh="none")

        if use_cache:
            mesh.export(str(cache_path))

        return mesh

    @classmethod
    def render(cls, img, rotation=(15, 20, 0), render_size=(1024, 1024), zoom=1.3):
        mesh = cls.generate_mesh(img)
        return MeshRenderer.render(mesh, rotation, render_size, zoom)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NUMPY FALLBACK (no AI, object-aware)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class NumpyFallbackEngine:
    """Object-aware extrusion. No AI, no download. Always works."""

    @staticmethod
    def _rotation_matrix(rx, ry, rz):
        rx, ry, rz = math.radians(rx), math.radians(ry), math.radians(rz)
        Rx = np.array([[1, 0, 0], [0, math.cos(rx), -math.sin(rx)], [0, math.sin(rx), math.cos(rx)]])
        Ry = np.array([[math.cos(ry), 0, math.sin(ry)], [0, 1, 0], [-math.sin(ry), 0, math.cos(ry)]])
        Rz = np.array([[math.cos(rz), -math.sin(rz), 0], [math.sin(rz), math.cos(rz), 0], [0, 0, 1]])
        return Rz @ Ry @ Rx

    @staticmethod
    def _project(pts, focal, cx, cy):
        z = pts[:, 2] + focal
        z = np.where(z < 1, 1, z)
        return np.stack([pts[:, 0] * focal / z + cx, pts[:, 1] * focal / z + cy], axis=1), z

    @classmethod
    def render(
        cls, img, rotation=(15, 20, 0), depth=30,
        focal_length=800, light_dir=(-0.5, -0.5, 1.0), ambient=0.3,
    ) -> Image.Image:
        from scipy.ndimage import binary_erosion, sobel

        img = _ensure_rgba(img)
        arr = np.array(img, dtype=np.float64)
        h, w = arr.shape[:2]
        alpha = arr[:, :, 3]

        R = cls._rotation_matrix(*rotation)
        light = np.array(light_dir, dtype=np.float64)
        light /= np.linalg.norm(light)

        obj_mask = alpha > 30
        eroded = binary_erosion(obj_mask, iterations=2)
        edge_mask = obj_mask & ~eroded
        gx = sobel(obj_mask.astype(np.float64), axis=1)
        gy = sobel(obj_mask.astype(np.float64), axis=0)

        pad = int(max(w, h) * 0.4) + depth
        out_w, out_h = w + pad * 2, h + pad * 2
        ctr_x, ctr_y = out_w / 2, out_h / 2
        hw, hh = w / 2, h / 2

        canvas = np.zeros((out_h, out_w, 4), dtype=np.float64)
        z_buf = np.full((out_h, out_w), -1e9)

        # Extrude edges
        edge_rows, edge_cols = np.where(edge_mask)
        if len(edge_rows) > 0:
            edge_nx = gx[edge_rows, edge_cols]
            edge_ny = gy[edge_rows, edge_cols]
            edge_colors = arr[edge_rows, edge_cols]

            for d in range(depth, -1, -1):
                depth_fade = 0.4 + 0.35 * (1.0 - d / max(depth, 1))
                pts = np.stack([
                    edge_cols.astype(np.float64) - hw,
                    edge_rows.astype(np.float64) - hh,
                    np.full(len(edge_rows), -float(d)),
                ], axis=1)
                rotated = (R @ pts.T).T
                proj, zz = cls._project(rotated, focal_length, ctr_x, ctr_y)
                normals_3d = np.stack([edge_nx, edge_ny, np.zeros(len(edge_nx))], axis=1)
                rot_normals = (R @ normals_3d.T).T
                dots = np.sum(rot_normals * light[None, :], axis=1)
                shade = np.clip(ambient + (1 - ambient) * np.maximum(0, dots), 0, 1) * depth_fade

                ox = np.round(proj[:, 0]).astype(int)
                oy = np.round(proj[:, 1]).astype(int)
                valid = (ox >= 0) & (ox < out_w) & (oy >= 0) & (oy < out_h) & (edge_colors[:, 3] > 10)

                for i in np.where(valid)[0]:
                    x, y, z = ox[i], oy[i], zz[i]
                    if z > z_buf[y, x]:
                        z_buf[y, x] = z
                        s = shade[i]
                        canvas[y, x] = [
                            min(255, edge_colors[i, 0] * s),
                            min(255, edge_colors[i, 1] * s),
                            min(255, edge_colors[i, 2] * s),
                            edge_colors[i, 3],
                        ]

        # Front face
        obj_rows, obj_cols = np.where(obj_mask)
        if len(obj_rows) > 0:
            pts_f = np.stack([
                obj_cols.astype(np.float64) - hw,
                obj_rows.astype(np.float64) - hh,
                np.zeros(len(obj_rows)),
            ], axis=1)
            rotated_f = (R @ pts_f.T).T
            proj_f, z_f = cls._project(rotated_f, focal_length, ctr_x, ctr_y)
            front_n = R @ np.array([0, 0, 1.0])
            front_shade = max(ambient, min(1.0, ambient + (1 - ambient) * max(0, np.dot(front_n, light))))
            front_colors = arr[obj_rows, obj_cols]
            ox = np.round(proj_f[:, 0]).astype(int)
            oy = np.round(proj_f[:, 1]).astype(int)
            valid = (ox >= 0) & (ox < out_w) & (oy >= 0) & (oy < out_h) & (front_colors[:, 3] > 10)

            for i in np.where(valid)[0]:
                x, y, z = ox[i], oy[i], z_f[i]
                if z > z_buf[y, x]:
                    z_buf[y, x] = z
                    canvas[y, x] = [
                        min(255, front_colors[i, 0] * front_shade),
                        min(255, front_colors[i, 1] * front_shade),
                        min(255, front_colors[i, 2] * front_shade),
                        front_colors[i, 3],
                    ]

        result = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8), "RGBA")
        return _crop_to_content(result, padding=25)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SHARED EFFECTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SharedEffects:

    @classmethod
    def add_reflection(cls, img, height_ratio=0.3, start_opacity=0.35, gap=6):
        img = _ensure_rgba(img)
        w, h = img.size
        ref_h = int(h * height_ratio)
        ref = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM).crop((0, 0, w, ref_h))
        gradient = np.linspace(start_opacity * 255, 0, ref_h, dtype=np.uint8)
        fade = np.tile(gradient[:, None], (1, w))
        if ref.mode == "RGBA":
            a = np.array(ref.split()[3], dtype=np.float64)
            combined = (a * fade.astype(np.float64) / 255).astype(np.uint8)
            ref.putalpha(Image.fromarray(combined, "L"))
        else:
            ref.putalpha(Image.fromarray(fade, "L"))
        total_h = h + gap + ref_h
        result = Image.new("RGBA", (w, total_h), (0, 0, 0, 0))
        result.paste(img, (0, 0), img)
        result.paste(ref, (0, h + gap), ref)
        return result

    @classmethod
    def perspective_shadow(cls, product, canvas, x, y, blur=25, opacity=100, offset_y=30, spread=1.15):
        try:
            alpha = product.split()[3]
        except IndexError:
            return
        w, h = product.size
        sw, sh = int(w * spread), int(h * 0.3)
        a_resized = alpha.resize((sw, sh), Image.Resampling.LANCZOS)
        a_arr = (np.array(a_resized, np.float64) * opacity / 255).astype(np.uint8)
        shadow = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        shadow.putalpha(Image.fromarray(a_arr, "L"))
        off = int(sw * 0.08)
        src = [(0, 0), (sw, 0), (sw, sh), (0, sh)]
        dst = [(-off, 0), (sw + off, 0), (sw - off, sh), (off, sh)]
        A_m, B_v = [], []
        for (xs, ys), (xt, yt) in zip(src, dst):
            A_m.append([xt, yt, 1, 0, 0, 0, -xs * xt, -xs * yt])
            A_m.append([0, 0, 0, xt, yt, 1, -ys * xt, -ys * yt])
            B_v.extend([xs, ys])
        coeffs = np.linalg.solve(np.array(A_m, np.float64), np.array(B_v, np.float64)).tolist()
        shadow = shadow.transform((sw, sh), Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BICUBIC)
        shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
        canvas.paste(shadow, (x - (sw - w) // 2, y + h - sh // 2 + offset_y), shadow)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CAMERA PRESETS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EFFECT_CAMERAS: Dict[str, dict] = {
    "perspective_tilt":  {"rotation": (25, 0, 0),    "depth": 30, "zoom": 1.3},
    "rotate_y":          {"rotation": (5, 30, 0),    "depth": 30, "zoom": 1.2},
    "rotate_y_left":     {"rotation": (5, -30, 0),   "depth": 30, "zoom": 1.2},
    "hero_angle":        {"rotation": (20, 15, 3),   "depth": 40, "zoom": 1.2},
    "float_3d":          {"rotation": (10, 8, 0),    "depth": 20, "zoom": 1.3},
    "isometric":         {"rotation": (35, 45, 0),   "depth": 50, "zoom": 1.0},
    "product_showcase":  {"rotation": (18, 12, -2),  "depth": 35, "zoom": 1.15},
    "dramatic_tilt":     {"rotation": (30, 20, -5),  "depth": 50, "zoom": 1.0},
    "box_view":          {"rotation": (25, 30, 0),   "depth": 60, "zoom": 0.95},
    "card_stand":        {"rotation": (12, 5, 0),    "depth": 12, "zoom": 1.3},
    "front":             {"rotation": (0, 0, 0),     "depth": 30, "zoom": 1.3},
    "top_down":          {"rotation": (60, 0, 0),    "depth": 30, "zoom": 1.0},
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENGINE SELECTOR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _select_engine() -> str:
    """Select best available engine based on toggles."""
    if USE_TRIPOSR:
        if TripoSRGenerator.is_available():
            return "triposr"
        elif TripoSRGenerator.is_downloaded():
            # Code downloaded but deps missing
            deps = TripoSRGenerator.check_deps()
            missing = [k for k, v in deps.items() if not v]
            warnings.warn(
                f"TripoSR downloaded but missing packages: {', '.join(missing)}\n"
                f"  pip install {' '.join(missing)}"
            )
        else:
            warnings.warn(
                "USE_TRIPOSR=True but not downloaded yet!\n"
                "  Run: python -m imaging.effects_3d --download\n"
                "  Then: pip install torch einops omegaconf transformers trimesh PyMCubes"
            )

    if USE_SHAP_E:
        if ShapEGenerator.is_available():
            return "shap_e"
        warnings.warn(
            "USE_SHAP_E=True but not installed!\n"
            "  pip install git+https://github.com/openai/shap-e.git"
        )

    if USE_STABLE_FAST_3D:
        if StableFast3DGenerator.is_available():
            return "stable_fast_3d"
        warnings.warn(
            "USE_STABLE_FAST_3D=True but not installed!\n"
            "  pip install git+https://github.com/Stability-AI/stable-fast-3d.git"
        )

    if USE_NUMPY_FALLBACK:
        return "numpy"

    raise RuntimeError("No 3D engine available! Set USE_NUMPY_FALLBACK = True")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAIN API — Product3DEffect
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Product3DEffect:
    """
    Main API — TRUE 3D from flat images.

    Models download from HuggingFace Hub to data/models/.
    Meshes are cached in data/cache/meshes/.

    Config:
        USE_TRIPOSR        = True/False  (stabilityai/TripoSR)
        USE_SHAP_E         = True/False  (openai/shap-e)
        USE_STABLE_FAST_3D = True/False  (stabilityai/stable-fast-3d)
        USE_NUMPY_FALLBACK = True/False  (no AI, always works)

    Usage:
        result = Product3DEffect.apply(img, "hero_angle", strength=10)
    """

    _engine_name: Optional[str] = None

    @classmethod
    def _get_engine(cls) -> str:
        if cls._engine_name is None:
            cls._engine_name = _select_engine()
            cls._print_status()
        return cls._engine_name

    @classmethod
    def _print_status(cls):
        print(f"\n  {'=' * 58}")
        print(f"  🎨 3D ENGINE STATUS")
        print(f"  {'─' * 58}")

        engines = [
            ("TripoSR",        USE_TRIPOSR,        TripoSRGenerator.is_available(),
             TripoSRGenerator.LOCAL_NAME,  "stabilityai/TripoSR"),
            ("Shap-E",         USE_SHAP_E,         ShapEGenerator.is_available(),
             ShapEGenerator.LOCAL_NAME,    "openai/shap-e"),
            ("Stable Fast 3D", USE_STABLE_FAST_3D, StableFast3DGenerator.is_available(),
             StableFast3DGenerator.LOCAL_NAME, "stabilityai/stable-fast-3d"),
            ("NumPy fallback",  USE_NUMPY_FALLBACK, True,
             "—", "—"),
        ]

        for name, toggled, available, local_name, hf_repo in engines:
            toggle = "✅ ON " if toggled else "⬜ OFF"
            avail = "✅ ready" if available else "❌ need pip install"
            downloaded = ""
            if local_name != "—":
                if ModelDownloader.is_downloaded(local_name):
                    downloaded = f"📦 {ModelDownloader.model_size(local_name)}"
                else:
                    downloaded = "📥 not downloaded yet"
            active = " ← ACTIVE" if (cls._engine_name and name.lower().replace(" ", "_").replace("-", "_") in cls._engine_name) else ""

            print(f"  {toggle}  {name:20s}  {avail:18s}  {downloaded}  {active}")
            if toggled and not available:
                print(f"         HF: {hf_repo}")

        print(f"  {'─' * 58}")
        print(f"  📁 Models: {MODELS_DIR.absolute()}")
        print(f"  💾 Cache:  {MESH_CACHE_DIR.absolute()}")

        try:
            import torch
            gpu = torch.cuda.is_available()
            name = torch.cuda.get_device_name(0) if gpu else "CPU only"
            vram = f"{torch.cuda.get_device_properties(0).total_mem / 1e9:.1f}GB" if gpu else ""
            print(f"  🖥️  Device: {'✅ GPU ' + name + ' ' + vram if gpu else '❌ ' + name}")
        except ImportError:
            print(f"  🖥️  Device: ❌ PyTorch not installed")

        print(f"  🎯 Active: {cls._engine_name}")
        print(f"  {'=' * 58}\n")

    @classmethod
    def apply(
        cls,
        img: Image.Image,
        effect_name: str = "hero_angle",
        strength: int = 10,
        **kwargs,
    ) -> Image.Image:
        """Apply 3D effect. Auto-downloads model on first use."""
        if effect_name == "none":
            return _ensure_rgba(img)
        if effect_name == "reflection":
            return SharedEffects.add_reflection(img)

        engine = cls._get_engine()

        preset = EFFECT_CAMERAS.get(effect_name, EFFECT_CAMERAS["hero_angle"])
        scale = strength / 10.0
        rotation = tuple(r * scale for r in preset["rotation"])
        depth = int(preset["depth"] * scale)
        zoom = preset["zoom"]

        if engine == "triposr":
            return TripoSRGenerator.render(img, rotation=rotation, zoom=zoom)
        elif engine == "shap_e":
            return ShapEGenerator.render(img, rotation=rotation, zoom=zoom)
        elif engine == "stable_fast_3d":
            return StableFast3DGenerator.render(img, rotation=rotation, zoom=zoom)
        elif engine == "numpy":
            return NumpyFallbackEngine.render(img, rotation=rotation, depth=max(5, depth))
        else:
            return _ensure_rgba(img)

    @classmethod
    def add_reflection(cls, img, **kwargs):
        return SharedEffects.add_reflection(img, **kwargs)

    @classmethod
    def perspective_shadow(cls, product, canvas, x, y, **kwargs):
        SharedEffects.perspective_shadow(product, canvas, x, y, **kwargs)

    @classmethod
    def get_engine_name(cls) -> str:
        return cls._get_engine()

    @classmethod
    def get_backend_name(cls) -> str:
        return cls._get_engine()

    @classmethod
    def list_effects(cls) -> List[str]:
        return list(EFFECT_CAMERAS.keys()) + ["reflection", "none"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STATUS + DOWNLOAD CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def check_3d_status():
    """Print status of all engines + downloads."""
    Product3DEffect._engine_name = _select_engine()
    Product3DEffect._print_status()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CLI ENTRYPOINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    args = sys.argv[1:]

    if "--download" in args:
        # Pre-download all enabled models
        force = "--force" in args
        ModelDownloader.download_all(force=force)

    elif "--status" in args:
        check_3d_status()

    elif "--help" in args or "-h" in args:
        print("""
  3D Effects Engine — Model Manager

  Usage:
    python -m imaging.effects_3d --download          Download enabled models
    python -m imaging.effects_3d --download --force   Re-download all
    python -m imaging.effects_3d --status             Show engine status

  Toggle models in effects_3d.py:
    USE_TRIPOSR        = True/False    stabilityai/TripoSR
    USE_SHAP_E         = True/False    openai/shap-e
    USE_STABLE_FAST_3D = True/False    stabilityai/stable-fast-3d
    USE_NUMPY_FALLBACK = True/False    (no download needed)

  Install packages:
    pip install huggingface_hub torch trimesh pyvista rembg scipy
    pip install tsr          # for TripoSR
    pip install shap-e       # for Shap-E
    pip install sf3d         # for Stable Fast 3D
        """)

    else:
        check_3d_status()
        print("  Use --download to download models")
        print("  Use --help for all options")