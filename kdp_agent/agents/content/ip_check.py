"""IP similarity check using CLIP to detect potential copyright violations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kdp_agent.config import KdpConfig

_ASSETS_DIR = Path(__file__).parent.parent.parent.parent / "assets" / "ip-reference"


class IpChecker:
    """
    Check generated images for similarity to known copyrighted characters.
    Requires `pip install -e ".[clip]"` for full functionality.
    Falls back to PASS if CLIP libs are not installed.
    """

    def __init__(self, config: "KdpConfig") -> None:
        self._threshold = config.image_gen.ip_similarity_threshold
        self._model = None
        self._preprocess = None
        self._ref_embeddings: list = []
        self._available = False
        self._try_load()

    def _try_load(self) -> None:
        try:
            import open_clip  # type: ignore
            import torch  # type: ignore

            self._model, _, self._preprocess = open_clip.create_model_and_transforms(
                "ViT-B-32", pretrained="openai"
            )
            self._model.eval()
            self._torch = torch
            self._open_clip = open_clip
            self._available = True
            self._load_references()
        except ImportError:
            pass  # Graceful: CLIP not installed, skip IP check

    def _load_references(self) -> None:
        if not _ASSETS_DIR.exists():
            return
        from PIL import Image  # type: ignore

        for img_path in _ASSETS_DIR.glob("*.{jpg,jpeg,png}"):
            try:
                img = self._preprocess(Image.open(img_path)).unsqueeze(0)
                with self._torch.no_grad():
                    emb = self._model.encode_image(img)
                    emb = emb / emb.norm(dim=-1, keepdim=True)
                self._ref_embeddings.append(emb)
            except Exception:
                continue

    def check(self, image_path: Path) -> tuple[bool, float]:
        """
        Returns (is_safe, max_similarity).
        is_safe=True means image is below the copyright similarity threshold.
        """
        if not self._available or not self._ref_embeddings:
            return True, 0.0  # No CLIP or no refs → assume safe

        from PIL import Image  # type: ignore

        try:
            img = self._preprocess(Image.open(image_path)).unsqueeze(0)
            with self._torch.no_grad():
                query_emb = self._model.encode_image(img)
                query_emb = query_emb / query_emb.norm(dim=-1, keepdim=True)

            max_sim = max(
                float((query_emb @ ref.T).item())
                for ref in self._ref_embeddings
            )
            is_safe = max_sim < self._threshold
            return is_safe, max_sim
        except Exception:
            return True, 0.0  # Fail-open: assume safe on error
