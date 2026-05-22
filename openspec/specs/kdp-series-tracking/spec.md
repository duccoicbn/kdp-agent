# Spec: KDP Series Tracking

**Capability**: `kdp-series-tracking`
**Change**: kdp-amazon-ai-agent-system (Phase 11 extension)
**Status**: Draft — ready for implementation

---

## Overview

Hệ thống lưu trữ và tái sử dụng thông tin giữa các tập (Vol.1, Vol.2, ...) trong cùng 1 series sách, cho phép:

1. **Hybrid series model** — vừa hỗ trợ Volume series (cùng nhân vật, đánh số) vừa Anthology (chung brand, khác nhân vật)
2. **Style DNA reuse** — Vol.2 vẽ giống Vol.1 nhờ inherit prompt template + palette + reference images
3. **Content dedup** — không trùng seeds và themes giữa các tập

---

## Requirements

### REQ-SERIES-001: Series Data Model

Tạo table `kdp_series` lưu thông tin canonical của 1 series:

```surql
DEFINE TABLE kdp_series SCHEMAFULL;

DEFINE FIELD id ON kdp_series TYPE string;
DEFINE FIELD name ON kdp_series TYPE string;
DEFINE FIELD brand ON kdp_series TYPE string DEFAULT "";
DEFINE FIELD author ON kdp_series TYPE string DEFAULT "KDP Agent";
DEFINE FIELD style ON kdp_series TYPE string ASSERT $value IN ["space","anime","mandala","other"];
DEFINE FIELD status ON kdp_series TYPE string DEFAULT "active"
    ASSERT $value IN ["active","completed","archived"];

DEFINE FIELD style_dna ON kdp_series TYPE object;
DEFINE FIELD style_dna.prompt_template      ON kdp_series TYPE string DEFAULT "";
DEFINE FIELD style_dna.negative_prompt      ON kdp_series TYPE string DEFAULT "";
DEFINE FIELD style_dna.palette              ON kdp_series TYPE array  DEFAULT [];
DEFINE FIELD style_dna.character_descriptor ON kdp_series TYPE string DEFAULT "";
DEFINE FIELD style_dna.reference_image_paths ON kdp_series TYPE array DEFAULT [];
DEFINE FIELD style_dna.captured_at          ON kdp_series TYPE datetime;
DEFINE FIELD style_dna.captured_from_book_id ON kdp_series TYPE string DEFAULT "";

DEFINE FIELD used_seeds ON kdp_series TYPE array DEFAULT [];

-- used_prompts: list of {hash, theme, volume_number, book_id}
DEFINE FIELD used_prompts ON kdp_series TYPE array DEFAULT [];

DEFINE FIELD volume_count ON kdp_series TYPE int DEFAULT 0;
DEFINE FIELD created_at   ON kdp_series TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at   ON kdp_series TYPE datetime DEFAULT time::now();

DEFINE INDEX idx_series_name  ON kdp_series FIELDS name UNIQUE;
DEFINE INDEX idx_series_brand ON kdp_series FIELDS brand;
```

**Update `kdp_book` table** (backward compatible — all new fields optional with safe defaults):

```surql
DEFINE FIELD series_id         ON kdp_book TYPE string  DEFAULT "";
DEFINE FIELD volume_number     ON kdp_book TYPE int     DEFAULT 0;
DEFINE FIELD relationship_type ON kdp_book TYPE string  DEFAULT "standalone"
    ASSERT $value IN ["standalone","volume","anthology_entry"];

DEFINE INDEX idx_series_volume ON kdp_book FIELDS series_id, volume_number;
```

**Acceptance**:
- Existing books (không có `series_id`) vẫn load được sau migration
- `idx_series_name UNIQUE` enforces no duplicate series names
- `idx_series_volume` composite cho efficient volume lookup

---

### REQ-SERIES-002: Style DNA Capture & Apply

#### Capture (sau khi Vol.1 approved)

Command: `kdp-agent series freeze-dna <series_name> --from-book <book_id>`

Pipeline:
1. Load approved `KdpBook` (Vol.1) — yêu cầu `status=approved` hoặc `status=live`
2. Extract:
   - `prompt_template` = book's prompt template (từ `prompt_templates.py` hoặc lưu lại từ generate run)
   - `negative_prompt` = book's negative prompt
   - `character_descriptor` = LLM-extracted descriptor từ generate prompts (vd: "cute chibi ghost with sparkly purple eyes")
   - `palette` = top-5 dominant colors extract bằng PIL từ cover image
   - `reference_image_paths` = 5 trang đầu của Vol.1 (paths absolute)
3. Lưu vào `series.style_dna` với `captured_at = now()` và `captured_from_book_id = book.id`

#### Apply (khi gen Vol.N)

Khi `generate run --series X --volume N`:
1. Load `series.style_dna`
2. Build prompt:
   ```
   <base_theme_prompt>
   in the SAME STYLE as the previous volumes: <character_descriptor>
   using color palette: <palette as hex list>
   <negative_prompt + series.style_dna.negative_prompt>
   ```
3. **Optional** (provider-dependent): nếu provider hỗ trợ image conditioning (Replicate Flux IP-Adapter, Pollinations với `ipadapter=true`), đính kèm `reference_image_paths[0:3]`

**Acceptance**:
- `freeze-dna` từ chối nếu book chưa approved
- Vol.2 prompt phải chứa `character_descriptor` và `palette` references
- Reference images chỉ attach nếu provider supports (graceful skip)

---

### REQ-SERIES-003: Content Dedup

#### Seed dedup

```python
def select_seed(series: KdpSeries, count: int) -> list[int]:
    """Pick `count` seeds NOT in series.used_seeds."""
    forbidden = set(series.used_seeds)
    selected = []
    while len(selected) < count:
        seed = random.randint(1, 2**32 - 1)
        if seed not in forbidden:
            selected.append(seed)
            forbidden.add(seed)
    return selected

# After successful gen:
async def commit_seeds(series_id: str, new_seeds: list[int]) -> None:
    """Append used seeds to series record (atomic)."""
    ...
```

#### Prompt dedup

```python
import hashlib

def prompt_fingerprint(theme: str, sub_theme: str = "") -> str:
    """Stable hash for theme deduplication (case/whitespace insensitive)."""
    normalized = f"{theme.lower().strip()}|{sub_theme.lower().strip()}"
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]

def check_theme_collision(series: KdpSeries, theme: str, sub_theme: str = "") -> bool:
    """Return True if this theme was already used in a previous volume."""
    fp = prompt_fingerprint(theme, sub_theme)
    return any(p["hash"] == fp for p in series.used_prompts)
```

**Behavior**:
- If theme collision → CLI prints WARNING + asks user to confirm or pick different theme
- If user `--force` → allow duplicate (lưu vào `used_prompts` với `forced=true` flag)

**Acceptance**:
- 100 volume gen consecutive → zero seed collision
- Re-running same `add-volume` with same theme → collision warning displayed

---

### REQ-SERIES-004: CLI Commands

#### Series management

```bash
kdp-agent series create <name> --style <style> [--brand <brand>] [--author <author>]
kdp-agent series list [--brand <brand>] [--status active|completed|archived]
kdp-agent series show <name>           # Display series info + all volumes
kdp-agent series archive <name>
```

#### Volume management

```bash
# Freeze DNA from approved Vol.1 (mandatory before adding Vol.2)
kdp-agent series freeze-dna <series_name> --from-book <book_id>

# Add new volume (auto-inherits DNA, auto-dedup)
kdp-agent series add-volume <series_name> \
    --theme <theme> [--sub-theme <sub>] [--pages 40] [--force]

# Path B (book-first): same effect as add-volume, but discoverable from generate command
kdp-agent generate run --series <series_name> --volume <N> --theme <theme>
```

**Acceptance**:
- `series create` rejects duplicate names (DB index UNIQUE)
- `add-volume` rejects if `style_dna` not frozen yet (with helpful error message)
- `--volume N` auto-computed if not specified (next available number)

---

### REQ-SERIES-005: Dashboard Series View

New route `/series/<name>`:
- Series header: name, brand, author, style, status, volume count
- Style DNA panel: character descriptor, palette swatches, 5 reference image thumbnails
- Volumes table: Vol.1 / Vol.2 / ... with cover thumbnail, status, ASIN, BSR
- "Add Volume" button → triggers `add-volume` flow with theme picker

**Acceptance**: Dashboard lists existing series, shows DNA, allows triggering new volume from UI.

---

### REQ-SERIES-006: Migration & Backward Compatibility

- New schema fields are **additive only** — no breaking changes to existing `kdp_book` records
- `migrate.surql` script idempotent (safe to re-run)
- Existing standalone books continue to work (treated as `relationship_type=standalone`)

**Acceptance**:
- After migration, demo book from Phase 0.5 (`geometric mandala`) still loads correctly
- `kdp-agent generate run` without `--series` flag works exactly as before

---

## Non-Requirements

- Không tự động sinh "Volume 2 theme" — user phải chỉ định `--theme`
- Không lock series sau khi publish — user có thể `archive` thủ công
- Không track Amazon series page metadata — KDP có riêng Series Settings, agent chỉ track internal

---

## Open Questions Resolved

| Question | Decision |
|----------|----------|
| Hybrid model? | ✓ Yes — `relationship_type` field phân biệt volume vs anthology_entry |
| Style DNA scope? | ✓ Full: prompt template + palette + character + 5 ref images + seeds |
| Dedup mechanism? | ✓ Both: seed-level + prompt-fingerprint-level |
| CLI surface? | ✓ Both: dedicated `series` subcommand + flags on `generate run` |
