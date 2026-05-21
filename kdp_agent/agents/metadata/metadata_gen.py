"""Metadata generation via Ollama (local LLM)."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import httpx

from kdp_agent.db import BookMetadata

if TYPE_CHECKING:
    from kdp_agent.config import KdpConfig


class MetadataGenerator:
    """Generate KDP book metadata using a local Ollama model."""

    def __init__(self, config: "KdpConfig") -> None:
        self._cfg = config.metadata

    async def generate(self, niche: str, theme: str, style: str) -> BookMetadata:
        """Generate complete metadata for a KDP coloring book."""
        title = await self._generate_title(niche, theme, style)
        subtitle = await self._generate_subtitle(niche, theme)
        description = await self._generate_description(niche, theme, style)
        keywords = await self._generate_keywords(niche, theme, style)
        categories = self._select_categories(style)

        return BookMetadata(
            title=title[: self._cfg.title_max_chars],
            subtitle=subtitle[: self._cfg.subtitle_max_chars],
            description=description,
            keywords=keywords[: self._cfg.keyword_count],
            categories=categories[: self._cfg.category_count],
            price_usd=8.99,
        )

    async def _chat(self, prompt: str) -> str:
        payload = {
            "model": self._cfg.ollama_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 500},
        }
        async with httpx.AsyncClient(timeout=60, base_url=self._cfg.ollama_base_url) as client:
            resp = await client.post("/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json()["message"]["content"].strip()

    async def _generate_title(self, niche: str, theme: str, style: str) -> str:
        style_label = "Anime" if style == "anime" else "Space & Galaxy"
        prompt = (
            f"Write a short, catchy Amazon KDP book title for a coloring book.\n"
            f"Theme: {theme}\nNiche: {niche}\nStyle: {style_label}\n"
            f"Requirements:\n"
            f"- Under 60 characters\n"
            f"- SEO-optimized with main keyword first\n"
            f"- No quotes, no punctuation except colon\n"
            f"- Examples: 'Space Coloring Book for Adults', 'Anime Fantasy Coloring Pages'\n"
            f"Reply with the title only."
        )
        return await self._chat(prompt)

    async def _generate_subtitle(self, niche: str, theme: str) -> str:
        prompt = (
            f"Write a subtitle for an Amazon KDP coloring book about '{theme}' in the '{niche}' niche.\n"
            f"Requirements:\n"
            f"- Under 80 characters\n"
            f"- Describes who it's for and the benefit\n"
            f"- Example: '50 Intricate Designs for Stress Relief and Relaxation'\n"
            f"Reply with the subtitle only."
        )
        return await self._chat(prompt)

    async def _generate_description(self, niche: str, theme: str, style: str) -> str:
        prompt = (
            f"Write an Amazon KDP book description for a coloring book.\n"
            f"Theme: {theme}\nNiche: {niche}\nStyle: {style}\n"
            f"Requirements:\n"
            f"- About 300-500 words\n"
            f"- Start with a hook sentence\n"
            f"- Describe the art style, who it's for, stress-relief benefits\n"
            f"- Include 40 unique designs, single-sided pages\n"
            f"- End with a call to action\n"
            f"- Plain text, no markdown\n"
            f"Reply with the description only."
        )
        return await self._chat(prompt)

    async def _generate_keywords(self, niche: str, theme: str, style: str) -> list[str]:
        prompt = (
            f"Generate 7 Amazon KDP search keywords for a coloring book.\n"
            f"Theme: {theme}\nNiche: {niche}\nStyle: {style}\n"
            f"Requirements:\n"
            f"- Each keyword under 50 characters\n"
            f"- Use long-tail phrases buyers actually search\n"
            f"- No keyword stuffing, each must be distinct\n"
            f"- Example keywords: 'space coloring book adults', 'galaxy mandala coloring pages'\n"
            f"Reply with a JSON array of 7 strings only. Example: [\"kw1\", \"kw2\"]"
        )
        raw = await self._chat(prompt)
        # Extract JSON array
        match = re.search(r'\[.*?\]', raw, re.DOTALL)
        if match:
            try:
                kws = json.loads(match.group())
                return [str(k)[: self._cfg.keyword_max_chars] for k in kws[:7]]
            except json.JSONDecodeError:
                pass
        # Fallback: split lines
        lines = [ln.strip().lstrip("-•*").strip().strip('"') for ln in raw.splitlines() if ln.strip()]
        return [ln[: self._cfg.keyword_max_chars] for ln in lines[:7]]

    def _select_categories(self, style: str) -> list[str]:
        """Return 2 BISAC categories based on style."""
        if style == "anime":
            return [
                "Crafts & Hobbies / Coloring Books / Fantasy",
                "Comics & Graphic Novels / Manga / General",
            ]
        return [
            "Crafts & Hobbies / Coloring Books / Stress Relieving",
            "Science Fiction / Space Opera",
        ]
