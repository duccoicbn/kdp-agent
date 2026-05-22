-- Idempotent additive migration for Phase 11: Series Tracking.
-- Run:
-- surreal import --conn ws://localhost:8000 --user root --pass root --ns kdp --db agent kdp_agent/migrations/001_add_series.surql

-- Optional series linkage on existing book records.
DEFINE FIELD OVERWRITE series_id         ON kdp_book TYPE string DEFAULT "";
DEFINE FIELD OVERWRITE volume_number     ON kdp_book TYPE int    DEFAULT 0;
DEFINE FIELD OVERWRITE relationship_type ON kdp_book TYPE string DEFAULT "standalone"
    ASSERT $value IN ["standalone","volume","anthology_entry"];
DEFINE INDEX OVERWRITE idx_series_volume ON kdp_book FIELDS series_id, volume_number;

-- Canonical series table.
DEFINE TABLE OVERWRITE kdp_series SCHEMAFULL;

DEFINE FIELD OVERWRITE id     ON kdp_series TYPE string;
DEFINE FIELD OVERWRITE name   ON kdp_series TYPE string;
DEFINE FIELD OVERWRITE brand  ON kdp_series TYPE string DEFAULT "";
DEFINE FIELD OVERWRITE author ON kdp_series TYPE string DEFAULT "KDP Agent";
DEFINE FIELD OVERWRITE style  ON kdp_series TYPE string ASSERT $value IN ["space","anime","mandala","other"];
DEFINE FIELD OVERWRITE status ON kdp_series TYPE string DEFAULT "active"
    ASSERT $value IN ["active","completed","archived"];

DEFINE FIELD OVERWRITE style_dna ON kdp_series TYPE object DEFAULT {};
DEFINE FIELD OVERWRITE style_dna.prompt_template       ON kdp_series TYPE string DEFAULT "";
DEFINE FIELD OVERWRITE style_dna.negative_prompt       ON kdp_series TYPE string DEFAULT "";
DEFINE FIELD OVERWRITE style_dna.palette               ON kdp_series TYPE array  DEFAULT [];
DEFINE FIELD OVERWRITE style_dna.character_descriptor  ON kdp_series TYPE string DEFAULT "";
DEFINE FIELD OVERWRITE style_dna.reference_image_paths ON kdp_series TYPE array  DEFAULT [];
DEFINE FIELD OVERWRITE style_dna.captured_at           ON kdp_series TYPE datetime ASSERT $value = NONE OR $value != NONE;
DEFINE FIELD OVERWRITE style_dna.captured_from_book_id ON kdp_series TYPE string DEFAULT "";

DEFINE FIELD OVERWRITE used_seeds   ON kdp_series TYPE array DEFAULT [];
DEFINE FIELD OVERWRITE used_prompts ON kdp_series TYPE array DEFAULT [];

DEFINE FIELD OVERWRITE volume_count ON kdp_series TYPE int DEFAULT 0;
DEFINE FIELD OVERWRITE created_at   ON kdp_series TYPE datetime DEFAULT time::now();
DEFINE FIELD OVERWRITE updated_at   ON kdp_series TYPE datetime DEFAULT time::now();

DEFINE INDEX OVERWRITE idx_series_name  ON kdp_series FIELDS name UNIQUE;
DEFINE INDEX OVERWRITE idx_series_brand ON kdp_series FIELDS brand;
