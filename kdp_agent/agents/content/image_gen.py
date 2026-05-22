"""Image generation: Replicate + Together.ai + Pollinations (pluggable providers, auto-fallback)."""

from __future__ import annotations

import asyncio
import base64
import io
import logging
import os
import random
import urllib.parse
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Protocol

import httpx
from PIL import Image

if TYPE_CHECKING:
    from kdp_agent.config import KdpConfig, ImageGenConfig, GenerationConfig

logger = logging.getLogger(__name__)


class ImageProvider(Protocol):
    """Provider contract: any backend must implement generate()."""

    name: str

    async def generate(
        self,
        prompt: str,
        negative_prompt: str,
        style: str,
        seed: Optional[int],
    ) -> bytes: ...


class ReplicateProvider:
    """Replicate API client — premium quality, paid per image."""

    name = "replicate"

    def __init__(self, cfg: "ImageGenConfig", gen_cfg: "GenerationConfig") -> None:
        self._cfg = cfg
        self._gen_cfg = gen_cfg

    def _model(self, style: str) -> str:
        if style == "anime":
            return self._cfg.replicate_model_anime
        return self._cfg.replicate_model_space

    async def generate(
        self,
        prompt: str,
        negative_prompt: str,
        style: str,
        seed: Optional[int],
    ) -> bytes:
        if not os.environ.get("REPLICATE_API_TOKEN"):
            raise RuntimeError("REPLICATE_API_TOKEN not set")

        import replicate  # type: ignore

        payload: dict = {
            "prompt": prompt,
            "width": self._gen_cfg.image_size,
            "height": self._gen_cfg.image_size,
            "num_inference_steps": 28,
            "guidance_scale": 3.5,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        if seed is not None:
            payload["seed"] = seed

        output = await asyncio.to_thread(
            replicate.run, self._model(style), input=payload
        )
        image_url = str(output[0]) if isinstance(output, list) else str(output)

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
            return resp.content


class TogetherProvider:
    """Together.ai client — free tier (Flux.1-schnell-Free), best for prototyping."""

    name = "together"
    API_URL = "https://api.together.xyz/v1/images/generations"

    def __init__(self, cfg: "ImageGenConfig", gen_cfg: "GenerationConfig") -> None:
        self._cfg = cfg
        self._gen_cfg = gen_cfg

    def _model(self, style: str) -> str:
        if style == "anime":
            return self._cfg.together_model_anime
        return self._cfg.together_model_space

    async def generate(
        self,
        prompt: str,
        negative_prompt: str,
        style: str,
        seed: Optional[int],
    ) -> bytes:
        api_key = os.environ.get("TOGETHER_API_KEY", "")
        if not api_key:
            raise RuntimeError("TOGETHER_API_KEY not set")

        full_prompt = prompt
        if negative_prompt:
            full_prompt = f"{prompt}. AVOID: {negative_prompt}"

        payload: dict = {
            "model": self._model(style),
            "prompt": full_prompt,
            "width": self._gen_cfg.image_size,
            "height": self._gen_cfg.image_size,
            "steps": self._cfg.together_steps,
            "n": 1,
        }
        if seed is not None:
            payload["seed"] = seed

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                self.API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
            item = data["data"][0]

            if "b64_json" in item:
                return base64.b64decode(item["b64_json"])

            image_url = item.get("url")
            if not image_url:
                raise RuntimeError(f"Together.ai response missing url/b64_json: {item}")
            img_resp = await client.get(image_url)
            img_resp.raise_for_status()
            return img_resp.content


class PollinationsProvider:
    """
    Pollinations.ai client — 100% free, no API key required.

    Best for: prototyping, demos, zero-budget mode.
    Quality: Flux-based, decent but not as polished as Replicate Flux.1-pro.
    Speed: ~30-90 seconds per image (no priority queue without key).

    Optional auth: set POLLINATIONS_TOKEN env var to bypass throttling / use private mode.
    """

    name = "pollinations"
    BASE_URL = "https://image.pollinations.ai/prompt"

    def __init__(self, cfg: "ImageGenConfig", gen_cfg: "GenerationConfig") -> None:
        self._cfg = cfg
        self._gen_cfg = gen_cfg

    def _model(self, style: str) -> str:
        if style == "anime":
            return self._cfg.pollinations_model_anime
        return self._cfg.pollinations_model_space

    async def generate(
        self,
        prompt: str,
        negative_prompt: str,
        style: str,
        seed: Optional[int],
    ) -> bytes:
        full_prompt = prompt
        if negative_prompt:
            full_prompt = f"{prompt}. AVOID: {negative_prompt}"

        actual_seed = seed if seed is not None else random.randint(1, 999_999_999)

        params = {
            "width": self._gen_cfg.image_size,
            "height": self._gen_cfg.image_size,
            "model": self._model(style),
            "seed": actual_seed,
            "nologo": "true",
            "private": "true",
            "enhance": "true",
        }

        token = os.environ.get("POLLINATIONS_TOKEN", "").strip()
        if token:
            params["token"] = token

        encoded_prompt = urllib.parse.quote(full_prompt, safe="")
        url = f"{self.BASE_URL}/{encoded_prompt}?{urllib.parse.urlencode(params)}"

        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                raise RuntimeError(
                    f"Pollinations returned non-image content-type: {content_type}"
                )
            return resp.content


class ImageGenerator:
    """
    Unified image gen facade.

    Routing strategy:
    1. Try `config.image_gen.provider` (primary)
    2. If primary fails AND `fallback_provider` is set → retry once on secondary
    3. Each provider has internal retry (`max_gen_retries` from generation config)
    """

    _PROVIDERS = {
        "replicate": ReplicateProvider,
        "together": TogetherProvider,
        "pollinations": PollinationsProvider,
    }

    def __init__(self, config: "KdpConfig") -> None:
        self._cfg = config.image_gen
        self._gen_cfg = config.generation

    def _build(self, name: str) -> ImageProvider:
        klass = self._PROVIDERS.get(name)
        if klass is None:
            raise ValueError(f"Unknown image provider: {name}")
        return klass(self._cfg, self._gen_cfg)

    async def generate(
        self,
        prompt: str,
        output_path: Path,
        negative_prompt: str = "",
        style: str = "space",
        seed: Optional[int] = None,
    ) -> Path:
        """Generate one image, save to output_path. Returns output_path."""
        primary = self._cfg.provider
        fallback = self._cfg.fallback_provider or None

        try:
            content = await self._try_with_retries(
                self._build(primary), prompt, negative_prompt, style, seed
            )
        except Exception as exc:
            if not fallback or fallback == primary:
                raise
            logger.warning(
                "Primary provider '%s' failed (%s) — falling back to '%s'",
                primary, exc, fallback,
            )
            content = await self._try_with_retries(
                self._build(fallback), prompt, negative_prompt, style, seed
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.open(io.BytesIO(content)).convert("RGB")
        img.save(str(output_path), format="PNG", dpi=(300, 300))
        return output_path

    async def _try_with_retries(
        self,
        provider: ImageProvider,
        prompt: str,
        negative_prompt: str,
        style: str,
        seed: Optional[int],
    ) -> bytes:
        attempts = max(1, self._gen_cfg.max_gen_retries)
        last_exc: Optional[Exception] = None
        for i in range(attempts):
            try:
                return await provider.generate(prompt, negative_prompt, style, seed)
            except Exception as exc:
                last_exc = exc
                if i < attempts - 1:
                    backoff = 2 ** i
                    logger.info(
                        "Provider '%s' attempt %d/%d failed (%s); retry in %ds",
                        provider.name, i + 1, attempts, exc, backoff,
                    )
                    await asyncio.sleep(backoff)
        raise RuntimeError(
            f"Provider '{provider.name}' failed after {attempts} attempts: {last_exc}"
        )
