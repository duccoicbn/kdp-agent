# Spec: KDP Pipeline Core

**Capability**: `kdp-pipeline-core`  
**Change**: kdp-amazon-ai-agent-system

---

## Overview
Core data model, configuration, và orchestration layer cho toàn bộ KDP pipeline. Đây là foundation mà tất cả agents phụ thuộc vào.

## Requirements

### REQ-CORE-001: Book Record Data Model
- SurrealDB table `kdp_book` với các fields theo design-brief Section 4
- Status enum: `research | draft | review | approved | publishing | live | rejected`
- CRUD operations qua SurrealDB client
- **Acceptance**: `CREATE kdp_book` và query by status hoạt động

### REQ-CORE-002: Configuration System
- File `kdp-config.yaml` tại `openspec/changes/kdp-amazon-ai-agent-system/kdp-config.yaml`
- Tất cả thresholds/magic numbers từ design brief Section 7 phải có trong config
- Python config loader: `from kdp_agent.config import KdpConfig`
- **Acceptance**: Config load thành công, thay đổi `kdp-config.yaml` không cần rebuild

### REQ-CORE-003: CLI Entry Point
- `python -m kdp_agent <command>` interface
- Commands: `demo`, `research`, `generate`, `review`, `publish`, `monitor`, `setup`
- **Acceptance**: `python -m kdp_agent --help` liệt kê tất cả commands

### REQ-CORE-004: Setup Wizard
- `python -m kdp_agent setup` chạy health checks:
  - Ollama API (`localhost:11434`)
  - Replicate API key (hoặc Together.ai)
  - SurrealDB connection
  - Tạo `kdp-config.yaml` nếu chưa có
- **Acceptance**: Setup thành công với màu xanh cho tất cả services, đỏ nếu thiếu

### REQ-CORE-005: Sample Book Demo
- `python -m kdp_agent demo --niche "geometric mandala" --pages 5`
- Generates 5 pages + cover + metadata → lưu vào `output/demo/`
- Không upload KDP
- **Acceptance**: Demo chạy < 5 phút (với API), output folder có đủ files

### REQ-CORE-006: SBU2-AI-Kit Agent Personas
- Tạo persona files trong `agents/` cho: `kdp-niche-agent`, `kdp-content-agent`, `kdp-cover-agent`, `kdp-metadata-agent`, `kdp-publisher-agent`, `kdp-monitor-agent`
- Mỗi persona tuân theo SBU2-AI-Kit format (frontmatter: name, description, tools, runtime_constraints)
- **Acceptance**: `search_registry(target_type="agent", query="kdp")` trả về 6 agents

## Non-Requirements
- Không cần cloud deployment (localhost only)
- Không cần authentication layer cho dashboard (localhost only)
