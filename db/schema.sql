-- CES Payment Resolution - PostgreSQL Schema
-- Generated from proto definitions in proto/

-- ============================================================
-- ENUM TYPES
-- ============================================================

CREATE TYPE customer_status AS ENUM (
    'active',
    'inactive',
    'pending',
    'closed'
);

CREATE TYPE risk_flag_type AS ENUM (
    'fraud_history',
    'suspended_account',
    'chronic_late_payments'
);

CREATE TYPE premium_frequency AS ENUM (
    'monthly',
    'quarterly',
    'semi_annual',
    'annual'
);

CREATE TYPE policy_status AS ENUM (
    'active',
    'inactive',
    'closed'
);

CREATE TYPE payment_history_status AS ENUM (
    'applied',
    'bounced',
    'reversed'
);

CREATE TYPE payment_status AS ENUM (
    'received',
    'processing',
    'applied',
    'held',
    'escalated'
);

CREATE TYPE payment_timing_quality AS ENUM (
    'excellent',
    'good',
    'acceptable',
    'poor'
);

CREATE TYPE account_status AS ENUM (
    'active',
    'inactive',
    'closed'
);

CREATE TYPE recommendation AS ENUM (
    'apply',
    'hold',
    'escalate'
);

CREATE TYPE scenario_route AS ENUM (
    'scenario_1',  -- Strong Policy Match
    'scenario_2',  -- Customer Match, No Policy
    'scenario_3',  -- High Amount Variance
    'scenario_4',  -- No Matching Customer
    'scenario_5'   -- Duplicate Payment
);

CREATE TYPE audit_action_type AS ENUM (
    'received',
    'signals_computed',
    'recommendation_made',
    'approved',
    'applied',
    'escalated'
);

-- ============================================================
-- TABLES
-- ============================================================

-- Master customer data.
CREATE TABLE customers (
    customer_id     TEXT PRIMARY KEY,            -- e.g., CUST-XXXX
    name            TEXT        NOT NULL,
    account_number  TEXT        NOT NULL UNIQUE,
    status          customer_status NOT NULL DEFAULT 'active',
    created_date    TIMESTAMPTZ NOT NULL DEFAULT now(),
    modified_date   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Risk flags on customer accounts (used by Scenario 1 hold path).
CREATE TABLE risk_flags (
    flag_id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id     TEXT        NOT NULL REFERENCES customers(customer_id),
    flag_type       risk_flag_type NOT NULL,
    is_active       BOOLEAN     NOT NULL DEFAULT true,
    flagged_date    TIMESTAMPTZ NOT NULL DEFAULT now(),
    notes           TEXT
);

CREATE INDEX idx_risk_flags_customer_active ON risk_flags (customer_id, is_active);

-- Insurance policies tied to customers.
CREATE TABLE policies (
    policy_number       TEXT PRIMARY KEY,            -- e.g., POL-XXXXX
    customer_id         TEXT        NOT NULL REFERENCES customers(customer_id),
    policy_type         TEXT        NOT NULL,         -- Auto, Home, Life, Health
    premium_amount      BIGINT      NOT NULL,         -- cents
    premium_frequency   premium_frequency NOT NULL,
    status              policy_status NOT NULL DEFAULT 'active',
    outstanding_balance BIGINT      NOT NULL DEFAULT 0, -- cents
    next_due_date       DATE,
    created_date        TIMESTAMPTZ NOT NULL DEFAULT now(),
    modified_date       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_policies_customer ON policies (customer_id);
CREATE INDEX idx_policies_status   ON policies (policy_number, status);

-- Historical payment records for pattern analysis (Scenarios 2, 3, 5).
CREATE TABLE payment_history (
    history_id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    policy_id       TEXT        NOT NULL REFERENCES policies(policy_number),
    payment_date    TIMESTAMPTZ NOT NULL,
    amount          BIGINT      NOT NULL,  -- cents
    payment_method  TEXT        NOT NULL,   -- ACH, Check, Credit Card, Wire
    sender_account  TEXT,
    status          payment_history_status NOT NULL
);

CREATE INDEX idx_payment_history_policy_date ON payment_history (policy_id, payment_date);

-- Incoming payments to be resolved by the AI agent.
CREATE TABLE payments (
    payment_id          TEXT PRIMARY KEY,            -- e.g., PMT-XXX
    amount              BIGINT      NOT NULL,         -- cents (proto has float, but use BIGINT per design notes)
    sender_name         TEXT        NOT NULL,
    sender_account      TEXT,
    beneficiary_name    TEXT,
    payment_method      TEXT        NOT NULL,
    payment_date        TIMESTAMPTZ NOT NULL,
    reference_field_1   TEXT,                          -- primary reference (policy number, etc.)
    reference_field_2   TEXT,                          -- secondary reference
    status              payment_status NOT NULL DEFAULT 'received',
    matched_customer_id TEXT        REFERENCES customers(customer_id),
    matched_policy_id   TEXT        REFERENCES policies(policy_number),
    created_timestamp   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_payments_date        ON payments (payment_date);
CREATE INDEX idx_payments_sender_name ON payments (sender_name);
CREATE INDEX idx_payments_amount      ON payments (amount);
CREATE INDEX idx_payments_status      ON payments (status);

-- Snapshot of all computed signals at decision time (1-to-1 with Payment).
CREATE TABLE payment_signals (
    payment_id      TEXT PRIMARY KEY REFERENCES payments(payment_id),
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Matching signals
    name_similarity_score       DOUBLE PRECISION,   -- 0-100
    policy_match_confidence     DOUBLE PRECISION,   -- 0-100
    customer_match_confidence   DOUBLE PRECISION,   -- 0-100
    account_match               BOOLEAN NOT NULL DEFAULT false,
    amount_match                BOOLEAN NOT NULL DEFAULT false,
    historical_match            BOOLEAN NOT NULL DEFAULT false,

    -- Amount signals
    amount_variance_pct             DOUBLE PRECISION,
    is_overpayment                  BOOLEAN NOT NULL DEFAULT false,
    is_underpayment                 BOOLEAN NOT NULL DEFAULT false,
    difference_amount               BIGINT,          -- cents
    is_multi_period                 BOOLEAN NOT NULL DEFAULT false,
    estimated_periods               INT     NOT NULL DEFAULT 0,
    historical_consistency_score    DOUBLE PRECISION, -- 0-100

    -- Temporal signals
    payment_timing_quality      payment_timing_quality,
    days_from_due_date          INT,                 -- positive = late, negative = early
    days_since_last_payment     INT,

    -- Risk signals
    has_risk_flags              BOOLEAN NOT NULL DEFAULT false,
    risk_flag_types             risk_flag_type[],    -- postgres array of enum
    account_status              account_status,

    -- Duplicate signals
    is_duplicate_match              BOOLEAN NOT NULL DEFAULT false,
    duplicate_payment_id            TEXT,
    hours_since_duplicate           DOUBLE PRECISION,
    outstanding_balance_justifies   BOOLEAN NOT NULL DEFAULT false
);

-- AI agent recommendation (1-to-1 with Payment).
CREATE TABLE payment_recommendations (
    payment_id              TEXT PRIMARY KEY REFERENCES payments(payment_id),
    recommendation          recommendation  NOT NULL,
    confidence_score        DOUBLE PRECISION NOT NULL,  -- 0-100
    scenario_route          scenario_route  NOT NULL,
    decision_path           TEXT,                        -- e.g., "scenario_1_auto_apply"
    requires_human_approval BOOLEAN NOT NULL DEFAULT false,
    approval_reason         TEXT,
    reasoning               TEXT[],                      -- ordered list of reasoning points
    suggested_action        TEXT,
    processing_time_ms      INT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Append-only audit log for compliance.
CREATE TABLE audit_log (
    log_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    payment_id      TEXT        NOT NULL REFERENCES payments(payment_id),
    action_type     audit_action_type NOT NULL,
    actor           TEXT        NOT NULL,   -- system or user identifier
    details         JSONB,                  -- maps to google.protobuf.Struct
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_log_payment   ON audit_log (payment_id);
CREATE INDEX idx_audit_log_timestamp ON audit_log (timestamp);
CREATE INDEX idx_audit_log_action    ON audit_log (action_type);

-- Externalized configuration thresholds (tunable without code changes).
CREATE TABLE configuration_thresholds (
    parameter_name  TEXT PRIMARY KEY,        -- e.g., NAME_MATCH_AUTO_APPLY
    parameter_value TEXT        NOT NULL,
    description     TEXT,
    effective_date  TIMESTAMPTZ NOT NULL DEFAULT now()
);