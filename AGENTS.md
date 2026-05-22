# KDP Agent — AI Assistant Context

## Project Overview

KDP Agent là hệ thống **semi-automated AI pipeline** để tạo và publish coloring books trên Amazon KDP. Stack: Python + FastAPI + Playwright + Replicate API + Ollama.

**Trạng thái hiện tại**: MVP hoàn thành (26/57 tasks). Xem `openspec/tasks.md` để biết tasks còn lại.

## Cấu trúc project

```
kdp_agent/
├── agents/
│   ├── content/      # Image generation (Replicate), postprocess, PDF builder, IP check
│   ├── metadata/     # Ollama LLM → title/desc/keywords
│   ├── publisher/    # Playwright session → KDP form fill (HITL gate)
│   ├── cover/        # TODO: Phase 2
│   ├── marketing/    # TODO: Phase 10
│   ├── niche/        # TODO: Phase 6
│   └── monitor/      # TODO: Phase 7
├── commands/         # Typer CLI commands (generate, metadata, dashboard, publish...)
├── dashboard/        # FastAPI web UI (Jinja2 templates)
├── config.py         # Load kdp-config.yaml → typed dataclasses
└── db.py             # SurrealDB async client + Pydantic models
openspec/             # OpenSpec artifacts (design-brief, specs, tasks)
kdp-config.yaml       # ALL thresholds & API settings — edit này, không hardcode
QUICKSTART.md         # Setup guide
```

## Coding Rules

- **Không hardcode** bất kỳ số/URL/threshold nào — đọc từ `kdp-config.yaml` qua `KdpConfig`
- **HITL gate**: `session.py` chỉ được fill form, KHÔNG được click "Submit for Review" hay "Publish" — human làm
- **IP safety**: Mọi image generate xong phải qua `IpChecker.check()` trước khi dùng
- **Async everywhere**: Các operations nặng (Replicate, Ollama, SurrealDB) đều dùng `async/await`
- **Error handling**: Dùng `Result` pattern hoặc raise rõ ràng, không `except: pass`

## Khi tiếp tục implement

1. Đọc `openspec/tasks.md` — tasks nào `- [ ]` là chưa làm
2. Đọc spec tương ứng trong `openspec/specs/`
3. Implement, rồi mark task `- [x]`
4. Commit: `feat(phase-X): <mô tả>`

## Services cần chạy local

| Service | Command | Port |
|---------|---------|------|
| SurrealDB | `surreal start --user root --pass root file:data/kdp.db` | 8000 |
| Ollama | `ollama serve` | 11434 |
| Dashboard | `python -m kdp_agent dashboard start` | 8080 |

## Image Providers (parallel + auto-fallback)

| Provider | Type | Cost | Use case |
|----------|------|------|----------|
| **Pollinations.ai** | Public HTTP API | 100% FREE, no key | Default — zero-budget mode (Flux) |
| **Together.ai** | Cloud API | Free tier (with credit) → paid ~$0.003/img | Mid-tier, faster than Pollinations |
| **Replicate** | Cloud API | Paid ~$0.025/img | Premium quality (Flux.1-pro, SDXL) |

Routing logic in `kdp_agent/agents/content/image_gen.py`:

1. Try `image_gen.provider` (primary) with `max_gen_retries` exponential backoff
2. If still fails AND `fallback_provider` is set → switch to secondary, retry once
3. Style-based model selection: `*_model_space` vs `*_model_anime`

Adding a new provider: implement `ImageProvider` protocol → add to `ImageGenerator._PROVIDERS`.

## Phases còn lại

| Phase | Mô tả | Tasks |
|-------|-------|-------|
| 2 | Cover Agent (Stable Diffusion XL cover design) | T-016 → T-019 |
| 6 | Niche Research Agent (keyword scraping) | T-037 → T-041 |
| 7 | Monitor Agent (BSR tracking) | T-042 → T-045 |
| 8 | IP Safety nâng cao (CLIP similarity) | T-046 → T-048 |
| 10 | Marketing Agent (mockup images, video) | T-049 → T-057 |
| 9 | Integration & E2E test | T-033 → T-036 |

## Off-limits

- Không commit `.env` hay credentials
- Không click Submit/Publish trong Playwright — đây là HITL boundary
- Không dùng `torch` trực tiếp cho inference — dùng qua Replicate API
