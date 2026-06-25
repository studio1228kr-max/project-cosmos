-- ============================================================
-- COSMOS Deal Detail (1.5단계) v1.0 — 현장관찰/체크리스트/게이트/IC메모
-- 100% 추가형. 재실행 안전.
-- ============================================================
BEGIN;

CREATE TABLE IF NOT EXISTS deal_field_observation (
  id            SERIAL PRIMARY KEY,
  deal_id       INTEGER NOT NULL REFERENCES deal_master(id) ON DELETE CASCADE,
  obs_type      TEXT NOT NULL,
  severity      TEXT NOT NULL CHECK (severity IN ('INFO','WATCH','REVIEW','CRITICAL','FATAL')),
  obs_text      TEXT NOT NULL,
  risk_domain   TEXT,
  gate_impact   TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dfo_deal ON deal_field_observation(deal_id);

CREATE TABLE IF NOT EXISTS deal_checklist_item (
  id                  SERIAL PRIMARY KEY,
  deal_id             INTEGER NOT NULL REFERENCES deal_master(id) ON DELETE CASCADE,
  dd_tier             TEXT NOT NULL CHECK (dd_tier IN ('SDD','CDD','EDD')),
  item_code           TEXT NOT NULL,
  item_name           TEXT NOT NULL,
  item_type           TEXT NOT NULL CHECK (item_type IN ('AUTO','DOC','MANUAL','RULE')),
  status              TEXT NOT NULL DEFAULT 'PENDING'
                        CHECK (status IN ('PENDING','RECEIVED','VERIFIED','REVIEW','NA')),
  value_text          TEXT,
  source_type         TEXT DEFAULT 'MANUAL_STATEMENT',
  verification_status TEXT DEFAULT 'UNVERIFIED',
  engine_connected    BOOLEAN DEFAULT FALSE,
  file_url            TEXT,
  updated_at          TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(deal_id, dd_tier, item_code)
);
CREATE INDEX IF NOT EXISTS idx_dci_deal ON deal_checklist_item(deal_id);

CREATE TABLE IF NOT EXISTS deal_gate_result (
  id              SERIAL PRIMARY KEY,
  deal_id         INTEGER NOT NULL REFERENCES deal_master(id) ON DELETE CASCADE,
  dd_tier         TEXT NOT NULL,
  checklist_gate  TEXT,
  red_flag_gate   TEXT,
  narrative_gate  TEXT,
  final_gate      TEXT NOT NULL CHECK (final_gate IN ('PASS','HOLD','FAIL','INCOMPLETE')),
  gate_note       TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dgr_deal ON deal_gate_result(deal_id);

CREATE TABLE IF NOT EXISTS deal_ic_memo (
  id            SERIAL PRIMARY KEY,
  deal_id       INTEGER NOT NULL REFERENCES deal_master(id) ON DELETE CASCADE,
  sdd_pct       INTEGER DEFAULT 0,
  cdd_pct       INTEGER DEFAULT 0,
  memo_text     TEXT,
  status        TEXT DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','SUBMITTED')),
  submitted_at  TIMESTAMPTZ,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dim_deal ON deal_ic_memo(deal_id);

COMMIT;
