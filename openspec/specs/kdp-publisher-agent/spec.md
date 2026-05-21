# Spec: KDP Publisher Agent

**Capability**: `kdp-publisher-agent`  
**Change**: kdp-amazon-ai-agent-system

---

## Overview
Agent tự động điền thông tin và upload files lên KDP, với ranh giới rõ ràng giữa hành động của agent và hành động của human để tuân thủ KDP ToS.

## Requirements

### REQ-PUBLISH-001: Human-Submit Boundary (ToS Compliance)
- **Agent-Allowed Actions**:
  - Navigate KDP dashboard pages
  - Fill text input fields (title, description, keywords)
  - Select dropdown values (categories, language, territory rights)
  - Upload files via `<input type="file">` (manuscript PDF, cover PDF)
  - Click "Save as Draft" buttons
  - Wait for KDP processing spinners
- **Human-Only Actions** (agent MUST pause và notify human):
  - "Submit for Review" button click
  - "Publish" button click
  - Account login
- **Acceptance**: Code review confirms no `click()` calls on Submit/Publish selectors

### REQ-PUBLISH-002: Playwright Session Management
- Human opens Chrome/Chromium, logs in to KDP manually
- Agent connects to existing browser session via Playwright remote debugging port (9222)
- Agent does NOT open new browser or manage login
- **Acceptance**: `playwright.chromium.connect_over_cdp("http://localhost:9222")` succeeds

### REQ-PUBLISH-003: Form Fill Automation
- Navigate to KDP > Bookshelf > Create new title (Paperback)
- Fill: Language, Title, Subtitle, Author name, Description, Keywords (7), Categories (2)
- Upload manuscript PDF and cover PDF
- Set pricing: marketplace, list price, royalty rate (60% or 35%)
- **Acceptance**: All fields filled correctly from book record in SurrealDB, confirmed by agent screenshot

### REQ-PUBLISH-004: Pre-Flight KDP Compliance Check
- Before starting browser session, run local checks:
  1. PDF page count divisible by 2
  2. Cover PDF dimensions match KDP spine calculator output
  3. All metadata fields non-empty and within KDP character limits
- Show checklist in Review Dashboard (localhost:8090/preflight/{book_id})
- **Acceptance**: Pre-flight catches at least: missing description, wrong cover size

### REQ-PUBLISH-005: Progress State Persistence
- Each form section completion saved to `kdp_book.publish_state` in SurrealDB
- If Playwright fails mid-session: agent saves last completed section, notifies human via dashboard notification
- Resume from saved state on restart
- **Acceptance**: Simulate Playwright crash after filling title → restart → resumes from post-title state

### REQ-PUBLISH-006: Anti-Detection Measures
- Random delay between page actions: uniform distribution from `config.publishing.playwright_action_delay_ms`
- Human-like typing speed: type character by character with random 50-150ms delays
- Take action only if element is visible and not disabled (no force clicks)
- **Acceptance**: Action logs show varied delays, no burst of rapid consecutive actions

## Non-Requirements
- Không support KDP Select enrollment (manual process)
- Không handle promo codes hay KDP ads setup
- Không support eBook format (paperback only for coloring books)
