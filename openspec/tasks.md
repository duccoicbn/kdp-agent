# Tasks — KDP Amazon AI Agent System

**Change**: kdp-amazon-ai-agent-system  
**Generated**: 2026-05-21  
**Status**: Ready for implementation

---

## Phase 0: Foundation (1–2 days)

- [x] **T-001**: Tạo Python project structure `kdp_agent/` với `pyproject.toml`, dependencies (playwright, replicate, reportlab, pillow, surrealdb-py, ollama, pyyaml, fastapi, uvicorn, img2vector, rembg, torch, clip)
- [x] **T-002**: Tạo `kdp-config.yaml` với tất cả thresholds từ spec REQ-CORE-002
- [x] **T-003**: Implement `kdp_agent/config.py` — dataclass loader cho `kdp-config.yaml`
- [x] **T-004**: Implement SurrealDB client wrapper `kdp_agent/db.py` với `KdpBook` model (REQ-CORE-001)
- [x] **T-005**: Tạo SurrealDB schema cho `kdp_book` table với index trên `status` field
- [x] **T-006**: Implement CLI entry point `kdp_agent/__main__.py` với Click/Typer (REQ-CORE-003)

## Phase 0.5: Setup & Onboarding (1 day)

- [x] **T-007**: Implement `kdp_agent/commands/setup.py` — setup wizard với health checks (REQ-CORE-004)
  - Check Ollama, Replicate API key, SurrealDB, tạo config nếu thiếu
- [ ] **T-008**: Implement `python -m kdp_agent demo` command — generate 5-page demo book (REQ-CORE-005)
  - Sử dụng hardcoded niche "geometric mandala", không upload KDP
- [x] **T-009**: Tạo `QUICKSTART.md` hướng dẫn từ clone → first book

## Phase 1: Content Agent (3–5 days)

- [x] **T-010**: Implement `kdp_agent/agents/content/prompt_templates.py` — Space + Anime templates (REQ-CONTENT-001)
  - Template engine với theme variable, NEGATIVE_PROMPTS_BASELINE từ config
- [x] **T-011**: Implement `kdp_agent/agents/content/image_gen.py` — multi-provider client (REQ-CONTENT-002)
  - Flux.1-dev cho space, SDXL+LoRA cho anime
  - Parallel providers: Replicate (primary) + Together.ai (fallback) with auto-failover
  - Pluggable `ImageProvider` protocol for adding new backends
- [x] **T-012**: Implement `kdp_agent/agents/content/postprocess.py` — binarize + vectorize pipeline (REQ-CONTENT-003)
  - rembg → threshold → img2vector → quality checks (stroke, closed paths, regions)
- [ ] **T-013**: Implement `kdp_agent/agents/content/ip_check.py` — CLIP similarity check (REQ-CONTENT-004)
  - Download IP reference library (50+ thumbnails) → `assets/ip-reference/`
  - CLIP cosine similarity, threshold từ config
- [x] **T-014**: Implement `kdp_agent/agents/content/pdf_builder.py` — KDP PDF assembly (REQ-CONTENT-005)
  - ReportLab: 8.5×11, 300 DPI, CMYK, 0.125" bleed, single-sided layout
- [x] **T-015**: Implement `kdp_agent/commands/generate.py` — CLI command kết nối T-010 → T-014
  - Args: `--book-id`, `--style [space|anime]`, `--theme`, `--pages`

## Phase 2: Cover Agent (2–3 days)

- [x] **T-016**: Tạo cover template library: 5 SVG templates tại `assets/cover-templates/`
  - Templates: `space-dark`, `space-light`, `anime-vibrant`, `anime-minimal`, `universal`
  - Slots: central_art (placeholder), title_area, author_area, back_description_area
- [x] **T-017**: Implement `kdp_agent/agents/cover/cover_gen.py`
  - Replicate API (Flux.1-pro) → generate central art image (switched from DALL-E 3 per config)
  - Rasterize SVG template → composite with AI art → add typography via Pillow
  - KDP spine calculator: width = pages × 0.002252" + 0.06"
- [x] **T-018**: Implement cover PDF export: front+spine+back single PDF, CMYK, correct dimensions
- [x] **T-019**: Implement `kdp_agent/commands/cover.py` — CLI command

## Phase 3: Metadata Agent (1–2 days)

- [x] **T-020**: Implement `kdp_agent/agents/metadata/metadata_gen.py`
  - Ollama client → `ollama.chat()` với model từ config (mặc định: qwen3:8b)
  - Prompts cho: title generation (SEO-optimized), description (500 words), 7 keywords, 2 BISAC categories
  - KDP character limits: title < 200 chars, keywords < 50 chars each
- [x] **T-021**: Implement metadata validation: check all fields non-empty, within limits
- [x] **T-022**: Implement `kdp_agent/commands/metadata.py` — CLI command

## Phase 4: Review Dashboard (2–3 days)

- [x] **T-023**: Implement `kdp_agent/dashboard/app.py` — FastAPI app
  - Routes: `/`, `/books`, `/book/{id}`, `/book/{id}/review`, `/preflight/{id}`, `/health`
- [x] **T-024**: Implement dashboard home page: book queue with status badges, queue summary stats
- [x] **T-025**: Implement book review page: interior page thumbnails (4×5 grid), cover preview, metadata fields (editable), Approve/Reject/Edit buttons
- [x] **T-026**: Implement pre-flight KDP compliance checker (REQ-PUBLISH-004): visual checklist với pass/fail per item
- [x] **T-027**: Implement API health page (`/health`): Ollama, Replicate, SurrealDB status với response time
- [x] **T-028**: Implement `kdp_agent/commands/dashboard.py` — start FastAPI server + open browser

## Phase 5: Publisher Agent (3–5 days)

- [x] **T-029**: Implement `kdp_agent/agents/publisher/session.py` — Playwright CDP session connect (REQ-PUBLISH-002)
  - Connect to existing Chrome via `http://localhost:9222`
  - Instructions cho user về cách start Chrome với `--remote-debugging-port=9222`
- [x] **T-030**: Implement `kdp_agent/agents/publisher/kdp_navigator.py` — KDP form navigation
  - Selectors cho KDP Bookshelf → Create → Paperback form
  - Implement anti-detection: random delays, character-by-character typing (REQ-PUBLISH-006)
- [x] **T-031**: Implement form fill sections: book details, content upload, pricing (REQ-PUBLISH-003)
  - Each section saves progress to SurrealDB (REQ-PUBLISH-005)
  - Pause before Submit button với dashboard notification
- [x] **T-032**: Implement `kdp_agent/commands/publish.py` — CLI command
  - Args: `--book-id`, requires `approved` status
- [ ] **T-033**: Test toàn bộ upload flow với KDP Sandbox (hoặc real account với draft-only)

## Phase 6: Niche Research Agent (2–3 days)

- [ ] **T-034**: Integrate `kdp-scout` CLI hoặc implement tương đương:
  - Amazon autocomplete sweep (A–Z) cho seed keywords: "coloring book", "space coloring", "anime coloring"
  - Extract long-tail keywords, estimated BSR, competition count
- [ ] **T-035**: Implement opportunity scoring: BSR threshold + competition max + trend check → `opportunity_score` float
- [ ] **T-036**: Implement `kdp_agent/agents/niche/niche_agent.py` — save top 20 opportunities/week to SurrealDB
- [ ] **T-037**: Implement niche browser page trong dashboard: `/niches` với opportunity score, trend chart, BSR history
- [ ] **T-038**: Implement `kdp_agent/commands/research.py` — CLI command

## Phase 7: Monitor Agent (1–2 days)

- [ ] **T-039**: Implement `kdp_agent/agents/monitor/kdp_monitor.py`
  - Poll KDP Bookshelf (Playwright headless) cho status: `in_review | live | rejected`
  - Check BSR weekly cho `live` books
  - Alert if: book rejected (show reason), BSR > 500k (low sales warning)
- [ ] **T-040**: Implement monitor dashboard page: `/monitor` với ASIN list, BSR chart, alerts
- [ ] **T-041**: Implement `kdp_agent/commands/monitor.py` — CLI command + scheduler (APScheduler)

## Phase 8: IP Safety Pipeline (1–2 days)

- [ ] **T-042**: Download và organize IP reference library: 50+ character thumbnails → `assets/ip-reference/`
  - Script: `python scripts/download_ip_refs.py`
- [ ] **T-043**: Implement CLIP model loading (`openai/clip-vit-base-patch32`) và embedding cache
- [ ] **T-044**: Integration test: generate với prompt chứa character names → confirm agent rejects và regenerates

## Phase 10: Marketing Agent (3–4 days)

### Sub-phase A: Promotional Images

- [ ] **T-049**: Implement `kdp_agent/agents/marketing/mockup.py` — 3D book mockup generator
  - Dùng Pillow composite: flat cover image → perspective transform → lay lên mockup template PNG
  - Templates: `assets/mockup-templates/` (hardcover, paperback, desk-scene variants)
  - Output: 1200×1200 PNG (square, transparent background option)
- [ ] **T-050**: Implement `kdp_agent/agents/marketing/social_images.py` — social media assets
  - **Instagram/Facebook post** (1080×1080): 4-page collage + cover + title overlay
  - **Pinterest pin** (1000×1500): vertical layout, "Color This!" CTA text
  - **TikTok/Reels thumbnail** (1080×1920): vertical mockup + title + "Available on Amazon"
  - **Twitter/X** (1200×675): horizontal mockup + short headline
  - Font: Google Fonts (Montserrat, Nunito) via `fonttools`
- [ ] **T-051**: Add Marketing tab vào Review Dashboard (`/book/{id}/marketing`)
  - Preview tất cả assets (thumbnails)
  - Download button per asset (individual + ZIP all)
  - "Regenerate" button cho từng asset

### Sub-phase B: Promotional Video

- [ ] **T-052**: Implement `kdp_agent/agents/marketing/video_builder.py` — FFmpeg slideshow pipeline
  - Input: 6–10 page thumbnails + cover image
  - Ken-burns effect (slow pan/zoom) per image via FFmpeg `zoompan` filter
  - Fade transitions between images
  - Duration: 30s reel (9:16) và 60s preview (16:9)
  - Background music: random pick từ `assets/music/` (royalty-free MP3s)
- [ ] **T-053**: Implement title/CTA text overlay
  - Animated text fade-in: book title (0–3s), "Available on Amazon" (ở cuối 3s)
  - FFmpeg `drawtext` filter với custom font
- [ ] **T-054**: Implement optional TTS voiceover (`kdp_agent/agents/marketing/tts.py`)
  - Kokoro TTS (local, free) hoặc ElevenLabs API (paid, better quality)
  - Script: 2–3 câu mô tả book, đọc bằng giọng Anh US
  - Config flag: `marketing.tts_enabled: false` (off by default)
- [ ] **T-055**: Implement `kdp_agent/commands/marketing.py` — CLI command
  - Args: `--book-id`, `--output-dir`, `--variants [all|images|video|reel]`
  - Example: `python -m kdp_agent marketing --book-id abc123 --variants all`
- [ ] **T-056**: Add video preview vào Marketing tab trong dashboard (HTML5 `<video>` tag)

### Sub-phase C: Optional — AI Animated Video (nâng cao)

- [ ] **T-057** *(optional)*: Implement `kdp_agent/agents/marketing/ai_video.py`
  - Kling AI API hoặc Pika Labs API: animate 1 cover image → 5s cinemagraph loop
  - Effect: crayons/ colored pencils "drawing" animation
  - Use case: TikTok organic, high-engagement format

## Phase 11: Series Tracking (3–5 days)

Cho phép publish sách nhiều tập với style consistency + content dedup giữa các volumes.

- [x] **T-067**: Add `kdp_series` table to `kdp_agent/schema.surql` (REQ-SERIES-001)
  - Fields: id, name (UNIQUE), brand, author, style, status, style_dna, used_seeds, used_prompts, volume_count
  - Indexes: idx_series_name UNIQUE, idx_series_brand
- [x] **T-068**: Update `kdp_book` table for series linkage (REQ-SERIES-001)
  - Add: series_id, volume_number, relationship_type
  - Add composite index: idx_series_volume on (series_id, volume_number)
  - Migration script `kdp_agent/migrations/001_add_series.surql` (idempotent)
- [x] **T-069**: Add `KdpSeries` + `StyleDna` Pydantic models to `kdp_agent/db.py`
  - Backward compatible: new fields on `KdpBook` default to safe values
- [x] **T-070**: Implement `kdp_agent/agents/series/series_repo.py` (REQ-SERIES-001/004)
  - CRUD: `create_series`, `get_series`, `list_series`, `update_series`, `archive_series`
  - Volume helpers: `next_volume_number`, `list_volumes`
- [x] **T-071**: Implement `kdp_agent/agents/series/style_dna.py` (REQ-SERIES-002)
  - `capture_dna(book) -> StyleDna`: extract palette (PIL), character_descriptor (Ollama), 5 ref images
  - `apply_dna(prompt, dna) -> str`: inject character/palette/style hints into base prompt
- [x] **T-072**: Implement `kdp_agent/agents/series/dedup.py` (REQ-SERIES-003)
  - `select_seeds(series, count) -> list[int]`: random seeds excluding used_seeds
  - `prompt_fingerprint(theme, sub) -> str`: SHA256 hash (case/whitespace insensitive)
  - `check_theme_collision(series, theme) -> bool`
  - `commit_dedup_record(series_id, seeds, prompt_hash, volume_id)`: atomic update
- [x] **T-073**: Implement `kdp_agent/commands/series.py` CLI (REQ-SERIES-004)
  - Subcommands: `create`, `list`, `show`, `archive`, `freeze-dna`, `add-volume`
  - Register in `__main__.py` as `kdp-agent series ...`
- [x] **T-074**: Wire `generate run --series <name> --volume <N>` flag (REQ-SERIES-004 path B)
  - Auto-pull DNA, auto-dedup seeds + theme
  - Auto-compute volume_number if not specified
- [x] **T-075**: Add series view to dashboard at `/series/<name>` (REQ-SERIES-005)
  - Series header, DNA panel (palette swatches + 5 ref thumbnails), volumes table
  - "Add Volume" button + theme picker form
- [x] **T-076**: E2E test for series flow
  - Create series → publish Vol.1 → freeze DNA → gen Vol.2 → verify:
    - Vol.2 uses no seeds from Vol.1
    - Vol.2 prompt contains character_descriptor + palette
    - Vol.2 cover visually consistent with Vol.1

## Phase 9: Integration & Config (2–3 days)

- [ ] **T-045**: Refactor: verify tất cả thresholds đọc từ `kdp-config.yaml` (không có hardcoded values trong code)
- [ ] **T-046**: Tạo 6 SBU2-AI-Kit agent persona files trong `agents/`: kdp-niche-agent, kdp-content-agent, kdp-cover-agent, kdp-metadata-agent, kdp-publisher-agent, kdp-monitor-agent (REQ-CORE-006)
- [ ] **T-047**: E2E test: từ `demo` command → generate → review dashboard → preflight check → (manual) publish flow
- [ ] **T-048**: Update `sbu2:brain` với `./kit engine-index brain` sau khi tạo agent personas

---

## Prioritized MVP Path (Phase 1 — 10–15 days)

Để publish cuốn sách đầu tiên:

```
T-001 → T-002 → T-003 → T-004 → T-005 → T-006  (Foundation)
T-007 → T-008 → T-009                             (Setup/Demo)
T-010 → T-011 → T-012 → T-014 → T-015            (Content, skip IP check initially)
T-016 → T-017 → T-018 → T-019                    (Cover)
T-020 → T-021 → T-022                             (Metadata)
T-023 → T-024 → T-025 → T-026 → T-027 → T-028    (Dashboard)
T-029 → T-030 → T-031 → T-032                    (Publisher)
```

**Sau MVP**: thêm T-013, T-042–T-044 (IP safety), T-034–T-038 (niche research), T-039–T-041 (monitor), T-049–T-056 (marketing).
