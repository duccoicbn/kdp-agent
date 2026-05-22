# Design Brief — KDP Amazon AI Agent System

**Change**: kdp-amazon-ai-agent-system  
**Schema**: brainstorm  
**Date**: 2026-05-21  
**Author**: AI (via openspec-brainstorm, full mode)

---

## 1. Problem Statement

Amazon KDP coloring book publishing là cơ hội kinh doanh có thể scale, nhưng quá trình thủ công từ nghiên cứu niche → tạo nội dung → upload cần 4–8 giờ/cuốn. Mục tiêu: xây dựng hệ thống AI agent semi-auto cho phép publish 50–500 coloring books/tháng với tỉ lệ human effort tối thiểu, đảm bảo chất lượng và tuân thủ KDP.

---

## 2. Goals

| Priority | Goal |
|----------|------|
| P0 | Generate coloring book interior PDF đạt chuẩn KDP (300 DPI, 8.5×11, CMYK) |
| P0 | Human review gate trước mỗi bước upload |
| P1 | Automated niche/keyword research |
| P1 | Auto-generate metadata (title, description, keywords, category) |
| P1 | Auto-upload lên KDP via browser automation |
| P2 | Dashboard web để review và approve |
| P2 | BSR / sales monitoring |
| P2 | Auto-generate promotional images (book mockup, social media posts) |
| P2 | Auto-generate promotional video (product reel, slideshow) |
| P3 | Batch mode: queue nhiều books xử lý song song |

---

## 3. System Architecture

### 3.1 High-Level Pipeline (Semi-Auto)

```
┌─────────────────────────────────────────────────────────────┐
│              KDP AI Agent System — Semi-Auto Pipeline         │
└─────────────────────────────────────────────────────────────┘

[1] NICHE AGENT          [2] CONTENT AGENT        [3] METADATA AGENT
 │ keyword research        │ generate 40 pages       │ title / desc / kw
 │ BSR analysis            │ SVG / PDF assembly       │ category selection
 │ competition score       │ cover generation         │
 └──────────┬──────────────┴──────────┬───────────────┘
            │                         │
            ▼                         ▼
     [HUMAN REVIEW GATE] ◄──── [Review Dashboard (localhost)]
            │  approve / reject / edit
            ▼
[4] PUBLISH AGENT
 │ Playwright → KDP dashboard
 │ upload manuscript + cover
 │ set metadata + pricing
 │ submit for review
 └──────────┬──────────────
            ▼
[5] MONITOR AGENT
 │ track KDP status (live/in review)
 │ BSR monitoring (post-publish)
 │ alert on issues
```

### 3.2 Agent Personas

| Agent | Responsibility | Tools Used |
|-------|---------------|-----------|
| `kdp-niche-agent` | Niche research, keyword scoring, opportunity detection | kdp-scout CLI, Amazon scraper, Google Trends |
| `kdp-content-agent` | Generate coloring pages (text prompt → art → PDF) | Flux.1/SD API, img2vector, ReportLab |
| `kdp-cover-agent` | Generate book cover (front + back + spine) | DALL-E 3, Pillow template, ReportLab |
| `kdp-metadata-agent` | Generate title, description, 7 keywords, 2 BISAC categories | LLM (Ollama), KDP category map |
| `kdp-publisher-agent` | Upload book to KDP via browser automation (human submits) | Playwright, Python |
| `kdp-marketing-agent` | Generate promo images + promo video cho từng book | DALL-E 3, Pillow, FFmpeg, Kling/Pika API |
| `kdp-monitor-agent` | Track live books, BSR, approval status | KDP dashboard scraping, SQLite |

### 3.3 Marketing Agent — Chi tiết

Sau khi book được approve (hoặc ngay sau generate), `kdp-marketing-agent` tự động tạo:

#### Output 1: Promotional Images

| Asset | Specs | Dùng cho |
|-------|-------|---------|
| **3D Book Mockup** | 1200×1200px PNG (square) | Amazon listing, social feed |
| **Instagram Post** | 1080×1080px, 3–5 page previews dạng grid | Instagram, Facebook |
| **Pinterest Pin** | 1000×1500px vertical | Pinterest (top traffic source cho coloring books) |
| **TikTok/Reels Thumbnail** | 1080×1920px vertical | TikTok, Instagram Reels cover |
| **Twitter/X Banner** | 1200×675px | Twitter post |

**Cách tạo mockup**: Dùng Python library `py3d-mockup` hoặc Placeit-style composite: render flat cover lên perspective template 3D → Pillow composite.

**Cách tạo grid preview**: Lấy 4–6 trang nội dung đẹp nhất → layout collage → add brand text, website (nếu có).

#### Output 2: Promotional Video

**Loại video**:

| Variant | Duration | Format | Platform |
|---------|----------|--------|---------|
| **Page Flip Reel** | 15–30s | 9:16 vertical | TikTok, Reels |
| **Slideshow Preview** | 30–60s | 16:9 horizontal | YouTube, Facebook |
| **Speed-Color Demo** | 30s | 9:16 vertical | TikTok (trending format) |

**Pipeline tạo video**:
```
[Pages thumbnails] + [Cover image]
       │
       ▼
FFmpeg slideshow (ken-burns effect, fade transitions)
       │
       ▼
Add royalty-free background music (from Pixabay/Freesound)
       │
       ▼
Overlay: title text + "Available on Amazon" CTA
       │
       ▼
Optional: AI voiceover (ElevenLabs/Kokoro TTS)
       │
       ▼
Output: MP4 (9:16 và 16:9 variants)
```

**Optional — AI Video** (nâng cao):
- Kling AI / Pika Labs API: animate 1 page trở thành video loop (crayons drawing effect)
- Phù hợp cho TikTok organic growth

### 3.4 Review Dashboard

Lightweight web UI (FastAPI + HTML/JS, localhost:8090) hiển thị:
- Preview của interior pages (thumbnails)
- Cover preview
- Generated metadata
- **Marketing tab**: promo images (download per format) + video preview + download MP4
- Approve / Reject / Edit buttons per field
- Queue status (pending / approved / publishing / live)

---

## 4. Data Model (SurrealDB `sbu2:brain`)

```sql
-- Book record
book {
  id: string,            -- ULID
  niche: string,         -- "Animals", "Mandalas", etc.
  theme: string,         -- "Forest animals for adults"
  status: enum,          -- research|draft|review|approved|publishing|live|rejected
  pages_generated: int,
  cover_generated: bool,
  metadata: {
    title: string,
    subtitle: string,
    description: string,
    keywords: [string; 7],
    categories: [string; 2],
    price_usd: float
  },
  files: {
    interior_pdf: string,   -- path
    cover_pdf: string,
    cover_jpg: string
  },
  kdp: {
    asin: string,
    publish_date: datetime,
    bsr: int,
    review_count: int
  },
  created_at: datetime,
  updated_at: datetime
}
```

---

## 5. Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Orchestration | SBU2-AI-Kit Rust daemon + sub-agents | Infrastructure đã có |
| Art generation | Flux.1-dev (ComfyUI API) hoặc DALL-E 3 | Fallback strategy |
| Line art post-processing | img2vector, OpenCV (Python) | Clean line art |
| PDF assembly | ReportLab + Pillow | Battle-tested Python |
| Cover assembly | ReportLab + DALL-E 3 | Template + AI image |
| KDP automation | Playwright (Python async) | 2026 best practice |
| Niche research | kdp-scout + custom Amazon scraper | Open source |
| Review dashboard | FastAPI + Vanilla JS | Lightweight, no framework |
| Storage | SurrealDB (sbu2:brain) + SQLite (niche data) | Dual-store |
| Config | `.env` file + SBU2 config system | Standard |

---

## 6. Semi-Auto Flow Detail

### Phase A: Niche Discovery (daily/weekly)
1. `kdp-niche-agent` runs keyword research (Amazon autocomplete A–Z sweep)
2. Scores opportunities: BSR < 50k + competition < 300 + trend rising
3. Saves to SurrealDB, presents top 10 niches in dashboard

### Phase B: Book Creation (per book, ~15–20 min)
1. Human selects niche + theme from dashboard
2. `kdp-content-agent` generates 40 coloring pages (prompt template → Flux.1 → vectorize → PDF)
3. `kdp-cover-agent` generates cover (DALL-E 3 + title overlay → KDP-spec PDF)
4. `kdp-metadata-agent` generates all metadata fields
5. **Human Review Gate**: human reviews pages, cover, metadata → Approve/Edit/Reject

### Phase C: Publishing (~5 min human time)
1. Human clicks "Approve" in dashboard
2. `kdp-publisher-agent` opens Playwright browser session
3. Auto-navigates KDP, uploads files, fills metadata
4. **Final human confirm** (1-click): reviews KDP preview → Publish
5. System captures ASIN, sets status `live`

### Phase D: Monitoring (automated)
1. `kdp-monitor-agent` polls KDP for approval status every 6 hours
2. Post-publish: checks BSR weekly, alerts if BSR > 500k (low sales)

---

## 7. Constraints & Guardrails

### ToS Compliance Boundaries (FAIL-1 addressed)
- **Human-Controlled Actions**: Mọi action có thể trigger KDP account risk PHẢI là human click:
  - "Submit for Review" button → human click only
  - "Publish" button → human click only
  - Account login/logout → human only
- **Agent-Allowed Actions** (form fill, non-submit):
  - Navigate KDP UI pages
  - Fill text fields (title, description, keywords)
  - Select dropdowns (categories, pricing)
  - Upload file via file input (manuscripts, covers)
  - Wait for KDP processing
- **Playwright Mode**: Agent controls browser up to "Review & Publish" page; pauses and notifies human for final submit.

### Copyright Safeguards (FAIL-2 addressed)
- **Negative Prompt Enforcement**: All image generation prompts MUST append a `NEGATIVE_PROMPTS_BASELINE`:
  ```
  known anime characters, naruto, goku, luffy, pikachu, existing IP,
  watermark, logo, text, brand names, famous fictional characters
  ```
- **Post-Generation IP Check**: After generating each image, run CLIP similarity check against a curated IP reference library (50+ character thumbnails). If similarity > 0.75, regenerate with increased negative guidance.
- **Human Review Flag**: Cover images containing humanoid characters are auto-flagged in dashboard for extra human attention before approve.

### Rate Limits & Scale Targets
- **Phase 1 (Month 1-3)**: Target 50 books/month = ≤ 2 books/day (very safe)
- **Phase 2 (Month 4-6)**: Target 100-150 books/month = ≤ 5 books/day (cautious)  
- **Phase 3 (Scale)**: 500 books/month requires 2-3 separate KDP accounts (different author names); never automate cross-account actions
- **Anti-detection**: Random delays (30-120s) between page actions; human-like typing speed for text fields

### Image Quality Gates
- Automated checks before human review:
  1. Stroke width ≥ 0.5pt (line weight check)
  2. Connected-component analysis: ≤ 5% unclosed paths (colorability check)
  3. DPI verification: extracted page ≥ 300 DPI when rasterized at 8.5×11
  4. Minimum detail count: ≥ 20 distinct regions per page
- Pages failing automated checks are auto-rejected (not sent to human review)

### Configuration Centralization (WARN-3 addressed)
All thresholds live in `kdp-config.yaml`:
```yaml
niche_research:
  bsr_threshold: 50000
  competition_max: 300
  trend_min_score: 0.6
publishing:
  max_books_per_day: 2
  playwright_action_delay_ms: [30000, 120000]
generation:
  min_stroke_pt: 0.5
  max_unclosed_path_pct: 5
  target_dpi: 300
  pages_per_book: 40
dashboard:
  port: 8090
image_gen:
  ip_similarity_threshold: 0.75
```

### Fallback
- If Playwright fails mid-upload: agent saves progress state to SurrealDB, notifies human with resume link
- If image gen API fails: queue retry with exponential backoff (max 3 retries), then alert human

---

## 8. Developer Onboarding (FAIL-3 addressed)

### Phase 0.5: Setup Wizard (first-run experience)
1. **CLI Setup Wizard** (`python setup.py`):
   - Check Ollama running (`http://localhost:11434/api/tags`)
   - Check Replicate API key (or fallback: Together.ai)
   - Check DALL-E 3 API key (optional, for covers)
   - Test SurrealDB connection
   - Run "API Health Check" page at localhost:8090/health
2. **Sample Book Demo**: one-command to generate a complete demo book:
   ```bash
   python -m kdp_agent demo --niche "geometric mandala" --pages 5
   ```
   Produces: 5 sample pages + cover + metadata preview in dashboard (no KDP upload)
3. **Documentation**: `QUICKSTART.md` with step-by-step from clone → first publish

---

## 9. Implementation Phases

| Phase | Scope | Estimated Effort |
|-------|-------|-----------------|
| Phase 0 | Setup: SurrealDB schema, book record, basic CLI | 1 day |
| Phase 0.5 | Setup wizard + API health check + Sample Book demo | 1 day |
| Phase 1 | `kdp-content-agent`: prompt → PDF interior pipeline (Space/Anime) | 3–5 days |
| Phase 2 | `kdp-cover-agent`: cover template library + AI art fill | 2–3 days |
| Phase 3 | `kdp-metadata-agent`: Ollama-powered metadata generation | 1–2 days |
| Phase 4 | Review Dashboard (FastAPI, localhost:8090) + pre-flight KDP checker | 2–3 days |
| Phase 5 | `kdp-publisher-agent`: Playwright KDP upload (human-submit boundary) | 3–5 days |
| Phase 6 | `kdp-niche-agent`: kdp-scout integration + keyword research | 2–3 days |
| Phase 7 | `kdp-monitor-agent`: BSR tracking + alerts | 1–2 days |
| Phase 8 | IP safety pipeline (CLIP check + negative prompts) | 1–2 days |
| Phase 9 | `kdp-config.yaml` centralization + integration E2E test | 2–3 days |

**Total estimate**: 19–30 days for full system (1 developer)  
**Phase 1 MVP** (publish 1 book manually assisted): Phase 0 + 0.5 + 1 + 2 + 3 + 4 = ~10–15 days

---

## 9. Clarified Decisions (từ brainstorm session)

| Question | Decision | Rationale |
|----------|----------|-----------|
| Image gen infrastructure | Start với cloud API (Replicate / Together.ai), migrate sang self-hosted (ComfyUI on GPU VM) khi có doanh thu | Cost-optimal: zero upfront, scale as revenue grows |
| Content style focus | **Space/Universe** + **Anime** style coloring books | High-demand, distinctive aesthetic, strong community |
| LLM backend | **Ollama** (local hoặc cloud VM) cho text generation (metadata, prompts) | Cost: $0, privacy, no rate limits |
| Image gen for art | **Multi-provider architecture** — Replicate (Flux.1-pro/SDXL) primary + Together.ai (FLUX.1-schnell-Free) fallback. Provider chọn qua `kdp-config.yaml`. Future: local SD/ComfyUI as 3rd provider. | Flexibility + cost control: pay-as-you-go default, free-tier mode optional, auto-failover for reliability |
| Cover image | Cùng provider stack với interior pages (chia sẻ `ImageGenerator` facade) | Consistency — switch providers 1 chỗ, áp dụng cho cả interior và cover |
| KDP account | 1 account, start slow | Avoid ban |
| Niche research | kdp-scout (free) + Amazon autocomplete | Start lean |
| Dashboard | FastAPI + Vanilla JS (localhost:8090) | Lightweight |
| Multi-volume series | Hybrid model (Volume series + Anthology), full Style DNA capture (prompt + palette + character + 5 ref images + seeds), dual-track dedup (seeds + prompt fingerprints), both CLI surfaces (`series add-volume` + `generate --series --volume N`) | Long-tail strategy: 1 successful niche → 5–10 volumes amortize research effort, brand-building, increased CTR via "Look Inside" series recommendations |

### Content Style Implications

**Space/Universe Coloring Books:**
- Keywords: "space coloring book adult", "galaxy mandala coloring", "astronaut coloring pages", "celestial coloring adult"
- Prompt style: "detailed line art, space scene, nebula, planets, astronauts, black and white, coloring book style, no shading"
- Target audience: Adults 25–45, sci-fi fans
- BSR benchmark: Top books < 20k BSR

**Anime Coloring Books:**
- Keywords: "anime coloring book adult", "manga style coloring pages", "anime characters coloring"
- Prompt style: "manga line art style, anime character, clean lines, black and white, coloring book page, no fill"
- **Copyright risk**: MUST use original anime-style characters (not existing IP)
- Target audience: Teens + young adults
- BSR benchmark: Top books < 30k BSR

### Updated Tech Stack for Space/Anime Style

| Art Type | Recommended Model | Notes |
|----------|------------------|-------|
| Space/Universe | Flux.1-dev + space LoRA | High detail, complex scenes |
| Anime line art | SDXL + AnimeLineArt LoRA | Clean manga-style strokes |
| Post-process | img2vector + threshold filter | Clean up for print |
