# Research — KDP Amazon AI Agent System (Coloring Books)

**Change**: kdp-amazon-ai-agent-system  
**Date**: 2026-05-21  
**Scope**: Semi-auto coloring book publishing pipeline, 50–500 books/month, starting from scratch

---

## 1. KDP Publishing Mechanism

### Official API
- **Amazon SP-API (Uploads v2020-11-01)** tồn tại nhưng hướng tới A+ Content và Messaging, **không** hỗ trợ trực tiếp upload manuscript/cover.
- **Kết luận**: KDP chưa có official public API cho book publishing. Tất cả tool thực tế hiện tại dùng **browser automation**.

### Giải pháp Browser Automation
| Tool | Tech Stack | Notes |
|------|-----------|-------|
| [auto-kdp](https://github.com/ekr0/auto-kdp) | TypeScript + Puppeteer | Upload book từ CSV, handle pricing, publishing. Maintained 2025. |
| Manual Playwright/Selenium | Python/Node | Custom; cần xử lý CAPTCHA, session |
| [kdp-book-generator](https://github.com/zoyth/kdp-book-generator) | TypeScript | Generate PDF/EPUB, KDP compliance check |

**Risk chính**: KDP Terms of Service prohibit automation — cần dùng rate-limiting và human oversight trong semi-auto mode.

---

## 2. Coloring Book Generation

### Yêu cầu kỹ thuật KDP
- Trim size: **8.5" × 11"** (standard adult coloring)
- Interior pages: single-sided (trang chẵn để tránh bleed qua), 40 designs = 80 pages
- Resolution: **≥ 300 DPI** (raster) hoặc vector SVG → PDF export
- Color mode: **CMYK** (không phải RGB)
- Bleed: 0.125" mỗi cạnh

### AI Generation Tools (Coloring Line Art)
| Tool | Approach | Quality | Cost |
|------|----------|---------|------|
| **HiVG** (2026) | 3B-param model, text→SVG | High fidelity vector | Open source |
| **txt2plotter** (2026) | LLM enhance → Flux.1-dev → vectorize → SVG | Good line art | Open source |
| **VectoSolve API** | text→SVG `line_art` style | Production-ready | Paid API |
| **DALL-E 3 + img2vector** | text→raster → vectorize | Versatile | API costs |
| **Stable Diffusion (local)** | ControlNet line art | High control | Local compute |

**Recommendation**: Pipeline kết hợp:
1. Prompt template → Stable Diffusion / Flux.1 (line art ControlNet)
2. Post-process: remove background, vectorize → SVG
3. SVG → CMYK PDF via ReportLab/Inkscape CLI

### Cover Generation
- Text-based design (Canva-style): **Pillow + ReportLab** hoặc **Figma API**
- AI-generated image: DALL-E 3 / Flux.1 + overlay text
- Template-based: pre-designed Canva/KDP templates với variable text/image

---

## 3. Niche & Keyword Research

### Open Source
| Tool | Capability | Notes |
|------|-----------|-------|
| [kdp-scout](https://github.com/rxpelle/kdp-scout) | Keyword mining, BSR tracking, competitor ASIN, Amazon Ads import | SQLite, cron automation |
| Amazon Autocomplete scraping | Long-tail keywords | Cần rate-limit |
| Google Trends API | Trending topics | Free |

### Commercial (reference)
- **NicheFlow** ($0–49/month): 10M+ data points/day, AI niche discovery
- **PublishRank** ($19/month): 10 tools, keyword gap, ASIN analysis
- **KDP Niche Hunter** ($15–59/month): BSR, royalties, competition scoring

**Recommendation cho start từ zero**: bắt đầu với kdp-scout (open source) + Amazon autocomplete scraping để tránh chi phí, sau đó migrate sang NicheFlow khi scale.

---

## 4. Workflow Benchmarks (Existing Systems)

### Coloring Book Engine (CBE) — 5-step workflow
1. **Plan**: niche research, keyword selection, content outline
2. **Generate**: AI-generate 40 coloring pages
3. **Clean**: QC, remove artifacts, adjust line weight
4. **Layout**: assemble into KDP-compliant PDF
5. **Publish**: upload to KDP + metadata entry

**Thời gian benchmark**: 2–4 giờ/book (manual+AI), target automation: <30 phút/book với semi-auto.

---

## 5. Key Risks & Constraints

| Risk | Severity | Mitigation |
|------|---------|-----------|
| KDP ToS về automation | HIGH | Semi-auto với human review gate, rate-limiting, không spam |
| AI art quality không đạt 300 DPI / line weight | MEDIUM | Post-processing pipeline + human QC |
| Amazon account suspension | HIGH | 1 account, slow publishing rate (<10 books/day) |
| Cover design quality gap | MEDIUM | Template-based + AI overlay |
| CAPTCHA / UI thay đổi | MEDIUM | Playwright resilience, fallback manual |

---

## 6. Tech Stack Recommendation

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Orchestration | SBU2-AI-Kit (Rust daemon + sub-agents) | Đã có infrastructure |
| Coloring art gen | Flux.1-dev + ControlNet + img2vector | Balance quality/cost |
| PDF assembly | ReportLab + Pillow | Python, battle-tested |
| Cover design | DALL-E 3 + Pillow template overlay | Quality + control |
| KDP upload | Playwright (Python) | More reliable than Puppeteer for 2026 |
| Niche research | kdp-scout + custom scraper | Open source base |
| Storage | SurrealDB (sbu2:brain) | Already present, tracks book records |
| Review UI | Simple web dashboard (localhost) | Human-in-loop gate |
