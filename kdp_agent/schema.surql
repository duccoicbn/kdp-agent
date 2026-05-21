-- KDP Agent SurrealDB Schema
-- Run: surreal import --conn ws://localhost:8000 --user root --pass root --ns kdp --db agent kdp_agent/schema.surql

-- Book record table
DEFINE TABLE kdp_book SCHEMAFULL;

DEFINE FIELD id           ON kdp_book TYPE string;
DEFINE FIELD niche        ON kdp_book TYPE string;
DEFINE FIELD theme        ON kdp_book TYPE string;
DEFINE FIELD style        ON kdp_book TYPE string   ASSERT $value IN ["space", "anime", "mandala", "other"];
DEFINE FIELD status       ON kdp_book TYPE string   ASSERT $value IN ["research","draft","review","approved","publishing","live","rejected"];
DEFINE FIELD pages_generated ON kdp_book TYPE int   DEFAULT 0;
DEFINE FIELD cover_generated ON kdp_book TYPE bool  DEFAULT false;

-- Metadata sub-object
DEFINE FIELD metadata              ON kdp_book TYPE object;
DEFINE FIELD metadata.title        ON kdp_book TYPE string   DEFAULT "";
DEFINE FIELD metadata.subtitle     ON kdp_book TYPE string   DEFAULT "";
DEFINE FIELD metadata.description  ON kdp_book TYPE string   DEFAULT "";
DEFINE FIELD metadata.keywords     ON kdp_book TYPE array    DEFAULT [];
DEFINE FIELD metadata.categories   ON kdp_book TYPE array    DEFAULT [];
DEFINE FIELD metadata.price_usd    ON kdp_book TYPE float    DEFAULT 8.99;

-- File paths
DEFINE FIELD files                 ON kdp_book TYPE object;
DEFINE FIELD files.interior_pdf    ON kdp_book TYPE string   DEFAULT "";
DEFINE FIELD files.cover_pdf       ON kdp_book TYPE string   DEFAULT "";
DEFINE FIELD files.cover_jpg       ON kdp_book TYPE string   DEFAULT "";
DEFINE FIELD files.pages_dir       ON kdp_book TYPE string   DEFAULT "";

-- KDP publish info
DEFINE FIELD kdp                   ON kdp_book TYPE object;
DEFINE FIELD kdp.asin              ON kdp_book TYPE string   DEFAULT "";
DEFINE FIELD kdp.publish_date      ON kdp_book TYPE datetime ASSERT $value = NONE OR $value != NONE;
DEFINE FIELD kdp.bsr               ON kdp_book TYPE int      DEFAULT 0;
DEFINE FIELD kdp.review_count      ON kdp_book TYPE int      DEFAULT 0;
DEFINE FIELD kdp.approval_status   ON kdp_book TYPE string   DEFAULT "";

-- Page generation seeds (for reproducibility)
DEFINE FIELD page_seeds ON kdp_book TYPE array DEFAULT [];

-- Publisher agent progress state
DEFINE FIELD publish_state ON kdp_book TYPE object DEFAULT {};

-- Timestamps
DEFINE FIELD created_at ON kdp_book TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON kdp_book TYPE datetime DEFAULT time::now();

-- Indexes
DEFINE INDEX idx_status  ON kdp_book FIELDS status;
DEFINE INDEX idx_niche   ON kdp_book FIELDS niche;
DEFINE INDEX idx_created ON kdp_book FIELDS created_at;

-- Niche opportunity table
DEFINE TABLE kdp_niche SCHEMAFULL;
DEFINE FIELD keyword         ON kdp_niche TYPE string;
DEFINE FIELD bsr_estimate    ON kdp_niche TYPE int    DEFAULT 0;
DEFINE FIELD competition     ON kdp_niche TYPE int    DEFAULT 0;
DEFINE FIELD trend_score     ON kdp_niche TYPE float  DEFAULT 0.0;
DEFINE FIELD opportunity_score ON kdp_niche TYPE float DEFAULT 0.0;
DEFINE FIELD discovered_at   ON kdp_niche TYPE datetime DEFAULT time::now();
DEFINE INDEX idx_opportunity ON kdp_niche FIELDS opportunity_score;
