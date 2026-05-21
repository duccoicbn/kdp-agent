# Quorum Review Summary — KDP Amazon AI Agent System

**Change**: kdp-amazon-ai-agent-system  
**Date**: 2026-05-21  
**Status**: REJECTED → pending_revision (3 FAILs must be addressed)

---

## Quorum Result

```json
{
  "summary_status": "rejected",
  "quorum": "3/4 agents completed (brainstorming-codebase failed: provider safety filter)",
  "pass_count": 6,
  "warning_count": 6,
  "fail_count": 3
}
```

---

## FAIL Items (Must Fix Before Specs)

### FAIL-1: KDP ToS Automation Risk (Skeptic + Guardian)
- **Component**: Phase C — `kdp-publisher-agent` (Playwright automation)
- **Issue**: Automated navigation, file upload, and metadata entry via Playwright is a direct KDP ToS violation. Amazon's anti-bot detection is aggressive; account termination risk is HIGH.
- **Required fix**: Clarify automation boundaries more strictly. Playwright must only autofill pre-approved fields; every "Submit" action must be an explicit human click. Document which actions are automated vs. human-triggered.

### FAIL-2: Anime Style Copyright Risk (Skeptic)
- **Component**: Content generation — Anime style
- **Issue**: "Safe prompt filters" are too vague. SDXL/Flux models can generate derivative works resembling existing IP (Naruto, One Piece, etc.). No concrete filtering mechanism exists in the current design.
- **Required fix**: Define a concrete IP safeguard: (1) explicit negative prompts list (no named characters), (2) post-generation CLIP similarity check against known IP thumbnails, (3) human review specifically for character designs.

### FAIL-3: Missing Developer Onboarding Flow (Advocate)
- **Component**: System-level — first-run experience
- **Issue**: No setup wizard, API key configuration guide, or "First Book" guided walkthrough. Solo developer faces high cognitive load with no on-ramp.
- **Required fix**: Add a "Phase 0.5: Setup & Onboarding" step with: CLI setup wizard, API key health checks, and a "Sample Book" demo using a hardcoded niche.

---

## WARNING Items (Strongly Recommended)

### WARN-1: Scale vs. Rate Limit Contradiction
- **Component**: Section 7 Constraints vs. Goals
- **Issue**: 500 books/month ≈ 16 books/day, contradicts max 5 books/day cap. Goal and constraint are irreconcilable with 1 KDP account.
- **Recommendation**: Clarify: Phase 1 target = 50 books/month (≤2 books/day). Scale to 500/month requires multiple KDP accounts (each managed separately, different authors).

### WARN-2: Image Quality Validation Insufficient
- **Component**: Content generation pipeline
- **Issue**: Automated "min 0.5pt stroke" check is not sufficient to catch wobbly vectorization or unclosed paths (needed for proper coloring).
- **Recommendation**: Add visual validation step: run simple connected-component analysis to count unclosed paths; threshold on acceptable % unclosed. Human review gate remains essential.

### WARN-3: Magic Numbers / Hardcoded Config
- **Component**: Design brief sections 5, 7, 8
- **Issue**: BSR < 50k, competition < 300, max 5/day, port 8090 hardcoded. Violates SBU2-AI-Kit config standards.
- **Recommendation**: Move all thresholds to `kdp-config.yaml` in the change directory; reference from code.

### WARN-4: Cover Design Quality Gap
- **Component**: `kdp-cover-agent`
- **Issue**: AI image + Pillow text overlay likely produces "AI-looking" covers with low conversion rate.
- **Recommendation**: Build a template library (3-5 designs per niche) as Canva-style SVG templates; AI image fills the central art slot, typography is fixed from proven templates.

### WARN-5: Over-Engineering Risk for Solo Dev (Advocate)
- **Component**: Infrastructure choice
- **Issue**: Rust daemon + SurrealDB may be excessive for a solo dev KDP business. Adds operational complexity.
- **Recommendation (keep but document)**: SBU2-AI-Kit is already present; use it as orchestration layer but ensure the book management pipeline is independently runnable via simple Python CLI without requiring the daemon to be running.

### WARN-6: Publishing Bottleneck
- **Component**: Phase C human confirm step
- **Issue**: Human reviewing KDP native previewer inside browser reduces semi-auto benefit.
- **Recommendation**: Build local PDF previewer in dashboard that validates KDP constraints before opening browser, so the KDP session is only for final 1-click submit.

---

## PASS Items

- Technical PDF specs (300 DPI, CMYK, bleed) correctly identified
- Human Review Gate well-placed before upload
- Functional Core / Imperative Shell architecture correct
- SBU2-AI-Kit integration aligned with existing patterns
- SurrealDB data model compatible with existing schema
- Research → Design Brief artifact connectivity is strong

---

## Required Actions Before Proceeding to Specs

1. Fix design-brief.md to address FAIL-1, FAIL-2, FAIL-3
2. Resolve WARN-1 (scale target clarification)
3. Add WARN-3 config centralization to design
4. Optionally address WARN-4 (cover template library)
