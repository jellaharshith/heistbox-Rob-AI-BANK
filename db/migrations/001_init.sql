-- HeistBox schema v1. Play money only, integer cents.

CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- What the bank is actually allowed to pay, per work item.
CREATE TABLE IF NOT EXISTS payment_entitlements (
    entitlement_id    TEXT PRIMARY KEY,
    work_item_id      TEXT NOT NULL UNIQUE,
    customer_id       TEXT NOT NULL,
    promo_batch       TEXT,
    authorized_cents  BIGINT NOT NULL CHECK (authorized_cents >= 0),
    reserved_cents    BIGINT NOT NULL DEFAULT 0 CHECK (reserved_cents >= 0),
    source_acct       TEXT NOT NULL,
    enrolled_wallet   TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'AUTHORIZED' CHECK (status IN ('AUTHORIZED', 'CLOSED')),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT reserved_within_authorized CHECK (reserved_cents <= authorized_cents)
);
CREATE INDEX IF NOT EXISTS idx_entitlements_promo ON payment_entitlements (promo_batch);

-- Rows an agent proposed. Written only inside the RIGHT vault's dry-run transaction, which is
-- always rolled back, so in normal operation this table stays empty.
CREATE TABLE IF NOT EXISTS proposed_effects (
    effect_id             BIGSERIAL PRIMARY KEY,
    attack_id             TEXT NOT NULL,
    session_id            TEXT NOT NULL,
    effect_idx            INT NOT NULL,
    claimed_work_item_id  TEXT,
    amount_cents          BIGINT NOT NULL CHECK (amount_cents >= 0),
    dest_wallet           TEXT NOT NULL,
    source_acct           TEXT NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS leaderboard (
    session_id            TEXT PRIMARY KEY,
    alias                 TEXT NOT NULL,
    attempts              INT NOT NULL DEFAULT 0,
    blocked_rows          INT NOT NULL DEFAULT 0,
    left_would_pay_cents  BIGINT NOT NULL DEFAULT 0,
    right_settled_cents   BIGINT NOT NULL DEFAULT 0,
    max_wanted_stars      INT NOT NULL DEFAULT 0,
    best_preset           TEXT,
    best_preset_blocked   INT NOT NULL DEFAULT 0,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_leaderboard_rank ON leaderboard (blocked_rows DESC, attempts DESC);

-- Per-session, per-agent memory. Repeated attempts raise suspicion.
CREATE TABLE IF NOT EXISTS agent_memory (
    session_id   TEXT NOT NULL,
    agent_id     TEXT NOT NULL,
    attempts     INT NOT NULL DEFAULT 0,
    suspicion    DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (suspicion >= 0 AND suspicion <= 1),
    notes        JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (session_id, agent_id)
);

-- Sessions (token hash only; the bearer token is never stored).
CREATE TABLE IF NOT EXISTS sessions (
    session_id    TEXT PRIMARY KEY,
    token_sha256  TEXT NOT NULL,
    alias         TEXT NOT NULL,
    work_item_id  TEXT NOT NULL REFERENCES payment_entitlements (work_item_id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Ed25519 hash-chained vendor wallet history. Each link signs sha256(prev_hash || payload).
CREATE TABLE IF NOT EXISTS vendor_wallet_chain (
    vendor_id      TEXT NOT NULL,
    seq            INT NOT NULL,
    wallet         TEXT NOT NULL,
    prev_hash      TEXT NOT NULL,
    link_hash      TEXT NOT NULL,
    signature_hex  TEXT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (vendor_id, seq)
);

CREATE TABLE IF NOT EXISTS vendor_keys (
    vendor_id       TEXT PRIMARY KEY,
    public_key_hex  TEXT NOT NULL
);
