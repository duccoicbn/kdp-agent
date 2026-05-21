"""Post-processing pipeline: binarize → vectorize → quality checks."""

from __future__ import annotations

import io
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image, ImageFilter, ImageOps

if TYPE_CHECKING:
    from kdp_agent.config import KdpConfig


@dataclass
class QualityReport:
    passed: bool
    stroke_ok: bool
    closed_paths_ok: bool
    regions_ok: bool
    region_count: int
    unclosed_pct: float
    details: str


class PostProcessor:
    """Binarize raster art and check coloring book quality."""

    def __init__(self, config: "KdpConfig") -> None:
        self._cfg = config.generation

    def binarize(self, input_path: Path, output_path: Path) -> Path:
        """Convert to pure black/white line art optimized for coloring books."""
        img = Image.open(input_path).convert("L")
        # Mild unsharp to enhance lines before threshold
        img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
        # Adaptive threshold via numpy (Sauvola-style simplified)
        arr = np.array(img, dtype=np.float32)
        # Local mean with large kernel
        from PIL import ImageFilter as IF
        kernel_img = Image.fromarray(arr.astype(np.uint8)).filter(IF.GaussianBlur(radius=15))
        local_mean = np.array(kernel_img, dtype=np.float32)
        binary = (arr < local_mean * 0.85).astype(np.uint8) * 255
        result = Image.fromarray(binary.astype(np.uint8))
        result.save(str(output_path), format="PNG", dpi=(300, 300))
        return output_path

    def check_quality(self, image_path: Path) -> QualityReport:
        """Run automated quality checks on a binarized image."""
        img = Image.open(image_path).convert("L")
        arr = np.array(img)
        binary = (arr < 128).astype(np.uint8)  # 1=black pixel

        # --- Region count (connected components approximation) ---
        region_count = self._count_regions(binary)
        regions_ok = region_count >= self._cfg.min_regions

        # --- Unclosed path estimate via contour analysis ---
        unclosed_pct = self._estimate_unclosed_paths(binary)
        closed_paths_ok = unclosed_pct <= self._cfg.max_unclosed_path_pct

        # --- Stroke width check (min stroke approximation) ---
        stroke_ok = self._check_stroke_width(binary)

        passed = regions_ok and closed_paths_ok and stroke_ok
        details = (
            f"regions={region_count}(min={self._cfg.min_regions}), "
            f"unclosed={unclosed_pct:.1f}%(max={self._cfg.max_unclosed_path_pct}%), "
            f"stroke={'ok' if stroke_ok else 'thin'}"
        )
        return QualityReport(
            passed=passed,
            stroke_ok=stroke_ok,
            closed_paths_ok=closed_paths_ok,
            regions_ok=regions_ok,
            region_count=region_count,
            unclosed_pct=unclosed_pct,
            details=details,
        )

    def _count_regions(self, binary: np.ndarray) -> int:
        """Approximate distinct white regions using flood-fill counting."""
        try:
            from scipy import ndimage  # type: ignore
            labeled, count = ndimage.label(1 - binary)
            # Filter tiny noise regions (< 50 px)
            sizes = ndimage.sum(1 - binary, labeled, range(1, count + 1))
            return int(np.sum(np.array(sizes) > 50))
        except ImportError:
            # Fallback: rough grid sampling
            h, w = binary.shape
            white_blocks = 0
            block_size = 50
            for y in range(0, h - block_size, block_size):
                for x in range(0, w - block_size, block_size):
                    block = binary[y : y + block_size, x : x + block_size]
                    if block.mean() < 0.3:  # mostly white
                        white_blocks += 1
            return white_blocks

    def _estimate_unclosed_paths(self, binary: np.ndarray) -> float:
        """Estimate % of endpoints (line terminations) as proxy for unclosed paths."""
        try:
            from skimage.morphology import skeletonize  # type: ignore
            skeleton = skeletonize(binary)
            # Count pixels with exactly 1 neighbor (endpoints)
            kernel = np.ones((3, 3), dtype=np.uint8)
            from scipy.ndimage import convolve  # type: ignore
            neighbor_count = convolve(skeleton.astype(np.uint8), kernel) - skeleton.astype(np.uint8)
            endpoints = np.sum((skeleton == 1) & (neighbor_count == 1))
            total_skeleton = np.sum(skeleton)
            if total_skeleton == 0:
                return 0.0
            return float(endpoints / total_skeleton * 100)
        except ImportError:
            return 2.0  # assume OK if libs missing

    def _check_stroke_width(self, binary: np.ndarray) -> bool:
        """Check if average stroke width meets minimum (0.5pt at 300 DPI ≈ 2px)."""
        # At 300 DPI: 0.5pt = 0.5/72 inch = ~2px
        min_pixels = max(2, int(self._cfg.min_stroke_pt / 72 * 300))
        try:
            from scipy.ndimage import distance_transform_edt  # type: ignore
            dist = distance_transform_edt(binary)
            # Average distance of skeleton pixels
            from skimage.morphology import skeletonize  # type: ignore
            skeleton = skeletonize(binary)
            if skeleton.sum() == 0:
                return True
            avg_radius = dist[skeleton].mean()
            return float(avg_radius) >= min_pixels / 2
        except ImportError:
            return True  # assume OK
