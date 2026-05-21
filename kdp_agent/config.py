"""Configuration loader for kdp-config.yaml."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


def _find_config() -> Path:
    """Locate kdp-config.yaml walking up from cwd."""
    candidates = [
        Path(os.environ.get("KDP_CONFIG", "kdp-config.yaml")),
        Path.cwd() / "kdp-config.yaml",
        Path(__file__).parent.parent / "kdp-config.yaml",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        "kdp-config.yaml not found. Run `python -m kdp_agent setup` first."
    )


@dataclass
class NicheResearchConfig:
    bsr_threshold: int = 50000
    competition_max: int = 300
    trend_min_score: float = 0.6
    top_opportunities: int = 20


@dataclass
class PublishingConfig:
    max_books_per_day: int = 2
    playwright_action_delay_ms: list[int] = field(default_factory=lambda: [3000, 8000])
    typing_delay_ms: list[int] = field(default_factory=lambda: [50, 150])
    kdp_dashboard_url: str = "https://kdp.amazon.com/en_US/bookshelf"
    playwright_cdp_port: int = 9222


@dataclass
class GenerationConfig:
    min_stroke_pt: float = 0.5
    max_unclosed_path_pct: float = 5.0
    min_regions: int = 20
    target_dpi: int = 300
    pages_per_book: int = 40
    image_size: int = 1024
    max_gen_retries: int = 3


@dataclass
class ImageGenConfig:
    provider: str = "replicate"
    replicate_model_space: str = "black-forest-labs/flux-1.1-pro"
    replicate_model_anime: str = "stability-ai/sdxl:39ed52f2319f9c703d0379b668aed8521d0e4b2a6893e06f21ee07a56b9ee64f"
    together_model: str = "black-forest-labs/FLUX.1-schnell-Free"
    ip_similarity_threshold: float = 0.75
    negative_prompts_baseline: str = (
        "known anime characters, naruto, goku, luffy, pikachu, existing IP, "
        "copyrighted characters, watermark, logo, text, brand names, "
        "famous fictional characters, trademarked characters, signature, "
        "low quality, blurry, jpeg artifacts"
    )


@dataclass
class CoverConfig:
    dall_e_model: str = "dall-e-3"
    dall_e_size: str = "1024x1024"
    dall_e_quality: str = "hd"
    templates_dir: str = "assets/cover-templates"
    bleed_inches: float = 0.125
    spine_width_per_page_inches: float = 0.002252
    spine_base_inches: float = 0.06


@dataclass
class MetadataConfig:
    ollama_model: str = "qwen3:8b"
    ollama_base_url: str = "http://localhost:11434"
    title_max_chars: int = 200
    subtitle_max_chars: int = 200
    description_target_words: int = 500
    keyword_max_chars: int = 50
    keyword_count: int = 7
    category_count: int = 2


@dataclass
class DashboardConfig:
    port: int = 8090
    host: str = "127.0.0.1"
    auto_open_browser: bool = True
    thumbnail_width: int = 200


@dataclass
class SurrealConfig:
    url: str = "ws://localhost:8000"
    namespace: str = "kdp"
    database: str = "agent"


@dataclass
class MarketingConfig:
    mockup_templates_dir: str = "assets/mockup-templates"
    output_formats: list[str] = field(
        default_factory=lambda: ["square_1080", "pinterest_pin", "tiktok_reel", "twitter_banner"]
    )
    video_duration_reel_s: int = 30
    video_duration_preview_s: int = 60
    music_dir: str = "assets/music"
    tts_enabled: bool = False
    tts_provider: str = "kokoro"
    ai_video_enabled: bool = False


@dataclass
class KdpConfig:
    niche_research: NicheResearchConfig = field(default_factory=NicheResearchConfig)
    publishing: PublishingConfig = field(default_factory=PublishingConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    image_gen: ImageGenConfig = field(default_factory=ImageGenConfig)
    cover: CoverConfig = field(default_factory=CoverConfig)
    metadata: MetadataConfig = field(default_factory=MetadataConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    surreal: SurrealConfig = field(default_factory=SurrealConfig)
    marketing: MarketingConfig = field(default_factory=MarketingConfig)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "KdpConfig":
        config_path = path or _find_config()
        with open(config_path) as f:
            raw = yaml.safe_load(f)

        def _build(dataclass_type, data: dict):
            if data is None:
                return dataclass_type()
            fields = {f.name: f for f in dataclass_type.__dataclass_fields__.values()}
            kwargs = {}
            for key, val in data.items():
                if key in fields:
                    kwargs[key] = val
            return dataclass_type(**kwargs)

        return cls(
            niche_research=_build(NicheResearchConfig, raw.get("niche_research", {})),
            publishing=_build(PublishingConfig, raw.get("publishing", {})),
            generation=_build(GenerationConfig, raw.get("generation", {})),
            image_gen=_build(ImageGenConfig, raw.get("image_gen", {})),
            cover=_build(CoverConfig, raw.get("cover", {})),
            metadata=_build(MetadataConfig, raw.get("metadata", {})),
            dashboard=_build(DashboardConfig, raw.get("dashboard", {})),
            surreal=_build(SurrealConfig, raw.get("surreal", {})),
            marketing=_build(MarketingConfig, raw.get("marketing", {})),
        )


_config: Optional[KdpConfig] = None


def get_config() -> KdpConfig:
    """Return the singleton config, loading from disk on first call."""
    global _config
    if _config is None:
        _config = KdpConfig.load()
    return _config
