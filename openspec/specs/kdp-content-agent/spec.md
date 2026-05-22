# Spec: KDP Content Agent

**Capability**: `kdp-content-agent`  
**Change**: kdp-amazon-ai-agent-system

---

## Overview
Agent chịu trách nhiệm generate coloring book interior pages (40 trang) theo style Space/Universe hoặc Anime, đáp ứng đầy đủ KDP technical specifications.

## Requirements

### REQ-CONTENT-001: Prompt Template System
- Template cho Space style: `"detailed line art, {theme}, space scene, nebula, planets, astronauts, black and white, coloring book style, no shading, thick clean lines, no fill, white background"`
- Template cho Anime style: `"manga line art style, {theme}, anime character, clean black lines, coloring book page, no fill, no shading, white background, thick outlines"`
- Negative prompts: append `NEGATIVE_PROMPTS_BASELINE` từ config
- **Acceptance**: Template render với theme variable, negative prompts always present

### REQ-CONTENT-002: Image Generation (Multi-Provider Architecture)

**Provider Architecture**: Pluggable `ImageProvider` protocol cho phép thêm/đổi backend không cần sửa pipeline.

**Supported providers**:
- **Pollinations.ai** (default): Flux via public HTTP API — 100% FREE, no key required, ideal for zero-budget mode
- **Together.ai**: FLUX.1-schnell-Free — free tier (cần credit/billing) → paid ~$0.003/image
- **Replicate**: Flux.1-pro (space) / SDXL (anime) — paid only (~$0.025/image), premium quality
- **Future**: Local SD / ComfyUI / DALL-E 3 có thể plug-in qua cùng protocol

**Routing rules** (configured via `kdp-config.yaml`):
1. Try `image_gen.provider` (primary) with up to `max_gen_retries` exponential backoff
2. If still fails AND `image_gen.fallback_provider` is set → switch to secondary, retry once
3. Each provider routes model theo `style` arg: `*_model_space` vs `*_model_anime`

**Configuration use cases**:
- Zero-budget (default): `provider: pollinations`, `fallback_provider: ""`
- Free + free fallback: `provider: pollinations`, `fallback_provider: together`
- Premium first, free fallback: `provider: replicate`, `fallback_provider: pollinations`

**Output normalization**: All providers return PNG bytes → unified resize/save at 300 DPI.

- **Acceptance**:
  - Switching provider purely qua YAML (no code change)
  - Replicate failure (e.g., quota exceeded) → seamless fallback to Together.ai
  - Generate 1 image < 60 giây (Replicate) / < 90 giây (Together)
  - Output ≥ 300 DPI khi converted to 8.5×11

### REQ-CONTENT-003: Post-Processing Pipeline
- Background removal (nếu cần): rembg library
- Binarize: threshold → pure black/white line art
- Vectorize: img2vector → SVG
- Quality checks (từ REQ-CORE guardrails):
  1. Stroke width ≥ 0.5pt
  2. Connected-component: ≤ 5% unclosed paths
  3. Minimum 20 distinct regions
- Auto-reject và regenerate nếu fail (max 3 lần)
- **Acceptance**: 90%+ generated images pass quality checks sau 3 attempts

### REQ-CONTENT-004: IP Safety Check
- Sau generation, run CLIP similarity check với IP reference library
- Library: 50+ character thumbnails (Naruto, Goku, Pikachu, etc.) lưu tại `assets/ip-reference/`
- Threshold: cosine similarity > 0.75 → reject và regenerate với increased CFG negative guidance
- **Acceptance**: Test với intentional "naruto-like" prompt → agent rejects và regenerates

### REQ-CONTENT-005: KDP-Compliant PDF Assembly
- 40 pages → single PDF: 8.5" × 11", 300 DPI, CMYK, 0.125" bleed
- Single-sided printing layout (ảnh chỉ trên trang lẻ)
- Blank back page mỗi design (trang chẵn trắng hoàn toàn)
- ReportLab + Pillow cho assembly
- **Acceptance**: PDF pass KDP file checker (check manually trong KDP console)

### REQ-CONTENT-006: Batch Generation
- Support `--count N` để generate N pages trước khi assemble
- Mỗi page có seed riêng (reproducible) lưu vào book record
- **Acceptance**: 40 pages generate thành công, seeds saved, reproducible với same seeds

## Non-Requirements
- Không cần UI cho content generation (headless, triggered từ dashboard)
- Không cần real-time preview trong browser (preview qua dashboard thumbnails)
