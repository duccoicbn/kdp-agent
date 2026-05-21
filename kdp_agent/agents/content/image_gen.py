"""Image generation via Replicate API (Flux.1 for space, SDXL for anime)."""

from __future__ import annotations

import asyncio
import io
import os
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import httpx
from PIL import Image

if TYPE_CHECKING:
    from kdp_agent.config import KdpConfig


class ImageGenerator:
    """Async image generator backed by Replicate or Together.ai."""

    def __init__(self, config: "KdpConfig") -> None:
        self._cfg = config.image_gen
        self._gen_cfg = config.generation

    def _get_model(self, style: str) -> str:
        if style == "anime":
            return self._cfg.replicate_model_anime
        return self._cfg.replicate_model_space

    async def generate(
        self,
        prompt: str,
        output_path: Path,
        negative_prompt: str = "",
        style: str = "space",
        seed: Optional[int] = None,
        retries: int = 0,
    ) -> Path:
        """Generate one image and save to output_path. Returns output_path."""
        provider = self._cfg.provider
        if provider == "replicate":
            return await self._generate_replicate(
                prompt=prompt,
                negative_prompt=negative_prompt,
                style=style,
                output_path=output_path,
                seed=seed,
                retries=retries,
            )
        elif provider == "together":
            return await self._generate_together(prompt, output_path, seed)
        else:
            raise ValueError(f"Unknown image_gen provider: {provider}")

    async def _generate_replicate(
        self,
        prompt: str,
        negative_prompt: str,
        style: str,
        output_path: Path,
        seed: Optional[int],
        retries: int,
    ) -> Path:
        import replicate  # type: ignore

        model = self._get_model(style)
        input_payload: dict = {
            "prompt": prompt,
            "width": self._gen_cfg.image_size,
            "height": self._gen_cfg.image_size,
            "num_inference_steps": 28,
            "guidance_scale": 3.5,
        }
        if negative_prompt:
            input_payload["negative_prompt"] = negative_prompt
        if seed is not None:
            input_payload["seed"] = seed

        max_attempts = self._gen_cfg.max_gen_retries
        for attempt in range(max_attempts):
            try:
                output = await asyncio.to_thread(
                    replicate.run, model, input=input_payload
                )
                # output is a URL or file-like object
                if isinstance(output, list):
                    image_url = str(output[0])
                else:
                    image_url = str(output)

                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.get(image_url)
                    resp.raise_for_status()
                    img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                    img.save(str(output_path), format="PNG", dpi=(300, 300))
                return output_path

            except Exception as exc:
                if attempt < max_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise RuntimeError(
                    f"Image generation failed after {max_attempts} attempts: {exc}"
                ) from exc

        return output_path  # unreachable

    async def _generate_together(
        self, prompt: str, output_path: Path, seed: Optional[int]
    ) -> Path:
        api_key = os.environ.get("TOGETHER_API_KEY", "")
        if not api_key:
            raise RuntimeError("TOGETHER_API_KEY not set in environment")

        payload = {
            "model": self._cfg.together_model,
            "prompt": prompt,
            "width": self._gen_cfg.image_size,
            "height": self._gen_cfg.image_size,
            "steps": 4,
            "n": 1,
        }
        if seed is not None:
            payload["seed"] = seed

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.together.xyz/v1/images/generations",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
            image_url = data["data"][0]["url"]
            img_resp = await client.get(image_url)
            img = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
            img.save(str(output_path), format="PNG", dpi=(300, 300))

        return output_path
