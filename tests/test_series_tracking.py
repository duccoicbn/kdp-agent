from __future__ import annotations

from kdp_agent.agents.series.dedup import (
    check_theme_collision,
    prompt_fingerprint,
    select_seeds,
)
from kdp_agent.agents.series.style_dna import apply_dna
from kdp_agent.db import KdpSeries, PromptFingerprint, StyleDna


def test_prompt_fingerprint_is_stable_and_normalized() -> None:
    assert prompt_fingerprint(" Black Holes ", "Vol 2") == prompt_fingerprint(
        "black   holes", "vol 2"
    )


def test_seed_selection_excludes_existing_series_seeds() -> None:
    series = KdpSeries(name="Ghost Anime Galaxy", used_seeds=[1, 2, 3])
    seeds = select_seeds(series, 100)

    assert len(seeds) == 100
    assert len(set(seeds)) == 100
    assert not ({1, 2, 3} & set(seeds))


def test_theme_collision_detects_existing_prompt_hash() -> None:
    record = PromptFingerprint(
        hash=prompt_fingerprint("saturn ghosts"),
        theme="saturn ghosts",
        volume_number=1,
        book_id="book-1",
    )
    series = KdpSeries(name="Ghost Anime Galaxy", used_prompts=[record])

    assert check_theme_collision(series, " Saturn   Ghosts ") == record
    assert check_theme_collision(series, "black holes") is None


def test_apply_dna_injects_descriptor_and_palette() -> None:
    dna = StyleDna(
        character_descriptor="cute chibi ghost with sparkly purple eyes",
        palette=["#7B2FBE", "#3D1A8B"],
    )
    prompt = apply_dna("space line art coloring page", dna)

    assert "SAME STYLE" in prompt
    assert "cute chibi ghost" in prompt
    assert "#7B2FBE" in prompt
