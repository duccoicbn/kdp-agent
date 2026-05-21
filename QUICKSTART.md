# KDP Agent — Quickstart Guide

Semi-auto AI system for Amazon KDP coloring book publishing (Space/Anime style).

---

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai) running locally (for metadata generation)
- **At least one image provider** (choose one or both):
  - [Replicate](https://replicate.com) — premium quality, ~$0.025/image
  - [Together.ai](https://api.together.xyz) — has free tier (Flux.1-schnell-Free)
- SurrealDB running locally (for book records)
- Google Chrome (for KDP upload step)

---

## 1. Install

```bash
# Clone or copy this project
cd C:\Users\ducnh2\Projects\kdp-agent

# Install dependencies
pip install -e .

# Install Playwright browsers (for KDP upload)
pip install -e ".[playwright]"
playwright install chromium
```

---

## 2. Configure API Keys

```powershell
# Primary provider: Replicate (paid, premium quality)
$env:REPLICATE_API_TOKEN = "r8_your_token_here"

# Secondary provider: Together.ai (free tier available, auto-fallback if Replicate fails)
$env:TOGETHER_API_KEY = "your_together_key_here"
```

### Image Provider Selection

Edit `kdp-config.yaml`:

```yaml
image_gen:
  provider: "replicate"           # Primary: "replicate" | "together"
  fallback_provider: "together"   # Auto-fallback on primary failure ("" to disable)
```

**Free tier mode** (no Replicate cost — slower but $0):

```yaml
image_gen:
  provider: "together"
  fallback_provider: ""
```

**Best of both** (default — try premium first, fallback to free):

```yaml
image_gen:
  provider: "replicate"
  fallback_provider: "together"
```

---

## 3. Setup Wizard

```bash
python -m kdp_agent setup
```

This checks:
- ✓ Ollama connection (localhost:11434)
- ✓ Image provider API keys (Replicate and/or Together.ai)
- ✓ SurrealDB connection (localhost:8000)

---

## 4. Run a Demo Book (no KDP upload)

```bash
python -m kdp_agent demo --niche "galaxy astronaut" --style space --pages 5
```

Output: `output/demo/` — 5 coloring pages + assembled PDF

---

## 5. Full Workflow (First Book)

### Step 1: Create a book record
```python
# Python snippet to create a book in the DB
import asyncio
from kdp_agent.db import KdpBook, get_db

async def create():
    db = get_db()
    await db.connect()
    book = KdpBook(niche="space coloring", theme="astronaut exploring nebula", style="space")
    await db.create_book(book)
    print(f"Book ID: {book.id}")
    await db.disconnect()

asyncio.run(create())
```

### Step 2: Generate interior pages
```bash
python -m kdp_agent generate \
  --book-id YOUR_BOOK_ID \
  --theme "astronaut exploring nebula" \
  --style space \
  --pages 40
```

### Step 3: Generate metadata
```bash
python -m kdp_agent metadata \
  --book-id YOUR_BOOK_ID \
  --niche "space coloring book adults" \
  --theme "astronaut exploring nebula" \
  --style space
```

### Step 4: Start the review dashboard
```bash
python -m kdp_agent dashboard
# Opens http://localhost:8090
```

Review your book, edit metadata if needed, run pre-flight check, then click **Approve**.

### Step 5: Publish to KDP (semi-auto)
```bash
python -m kdp_agent publish --book-id YOUR_BOOK_ID
```

1. Open Chrome: `chrome.exe --remote-debugging-port=9222`
2. Log in to [KDP](https://kdp.amazon.com)
3. Press Enter in the terminal — agent fills all fields automatically
4. **You click "Submit for Review"** (human action required per KDP ToS)

---

## Configuration

Edit `kdp-config.yaml` to adjust all thresholds:
- `generation.pages_per_book` — default 40
- `publishing.max_books_per_day` — default 2 (conservative)
- `metadata.ollama_model` — default `qwen3:8b`
- `image_gen.provider` — `replicate` | `together`

---

## Project Structure

```
kdp-agent/
├── kdp_agent/
│   ├── agents/
│   │   ├── content/      # Image generation, post-processing, PDF
│   │   ├── cover/        # Cover generation
│   │   ├── metadata/     # Ollama-based metadata
│   │   ├── publisher/    # Playwright KDP upload
│   │   └── marketing/    # Promo images & video (Phase 10)
│   ├── commands/         # CLI commands
│   ├── dashboard/        # FastAPI review dashboard
│   ├── config.py         # Config loader
│   └── db.py             # SurrealDB wrapper
├── assets/               # Templates, mockups, music
├── output/               # Generated books
├── kdp-config.yaml       # All configuration
└── QUICKSTART.md
```

---

## Rate Limits & Safety

- **Max 2 books/day** (configurable) — conservative for single KDP account
- KDP Submit/Publish buttons are **always human-click** — agent never submits
- Anime style: negative prompts prevent copyrighted characters
- All thresholds in `kdp-config.yaml` — no hardcoded magic numbers
