-- CES Payment Resolution - PostgreSQL Schema
-- Generated from proto definitions in proto/
-- Last updated: 2026-04-08

-- ============================================================
-- ENUM TYPES
-- ============================================================

-- User roles — controls home screen, data scope, and decision authority.
CREATE TYPE user_role AS ENUM (
    'analyst',       -- Priya: daily queue, apply/hold/escalate
    'investigator',  -- Damien: escalated cases, final determination
    'director',      -- Lorraine: governance dashboard, config approval
    'admin'          -- Marcus: config management, performance monitoring
);

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
    'escalated',
    'processing_failed',
    'pending_sender_response',  -- Damien awaiting sender reply; SLA timer running
    'returned'                  -- Payment returned to sender after investigation
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

CREATE TYPE payment_method_risk_level AS ENUM (
    'low',        -- ACH, Card
    'medium',     -- Check, Wire
    'high'        -- Unknown / unrecognized method
);

CREATE TYPE recommendation AS ENUM (
    'apply',
    'hold',
    'escalate',
    'return'  -- Damien final determination: return payment to sender
);

-- Who ultimately made the final decision on a payment.
CREATE TYPE decision_attribution AS ENUM (
    'ai_autonomous',    -- Applied/escalated with no human touch
    'human_confirmed',  -- Human agreed with AI recommendation
    'human_override'    -- Human disagreed and changed the outcome
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
    'escalated',
    'held',
    'overridden',                  -- Human changed AI outcome; mandatory reason captured
    'annotated',                   -- Case note or investigation note added
    'document_uploaded',           -- Supporting document attached
    'contact_logged',              -- Damien logged outreach to sender or bank
    'returned',                    -- Payment returned to sender
    'governance_review_recorded',  -- Lorraine recorded a period review
    'anomaly_flagged',             -- Lorraine flagged a metric anomaly for Marcus
    'config_change_proposed',      -- Marcus submitted a change request
    'config_change_approved',      -- Lorraine approved a change request
    'config_change_rejected',      -- Lorraine rejected a change request
    'config_change_deployed',      -- Marcus deployed an approved change
    'config_change_rolled_back',   -- Emergency rollback executed
    'sla_breached'                 -- Investigation SLA exceeded (system-generated)
);

-- Category of document attached to a case.
CREATE TYPE document_type AS ENUM (
    'supporting_evidence',    -- Priya: anything backing her decision
    'sender_correspondence',  -- Damien: emails or letters from sender
    'bank_statement',         -- Damien: payment proof from bank
    'fraud_report',           -- Damien: fraud team documentation
    'policy_document',        -- Either: policy-related paperwork
    'other'
);

-- Type of annotation written on a case.
CREATE TYPE annotation_type AS ENUM (
    'case_note',           -- Priya: general note on a hold or decision
    'override_reason',     -- Priya: mandatory reason when overriding AI recommendation
    'contact_record',      -- Damien: structured log of outreach to sender or bank
    'investigation_note'   -- Damien: in-progress investigation reasoning
);

-- Lifecycle of a configuration change request (Marcus → Lorraine).
CREATE TYPE config_change_status AS ENUM (
    'pending',      -- Submitted by Marcus, awaiting Lorraine
    'approved',     -- Lorraine approved, not yet deployed
    'rejected',     -- Lorraine rejected
    'deployed',     -- Marcus deployed to production
    'rolled_back'   -- Rolled back after deployment
);

-- Status of an anomaly investigation flag.
CREATE TYPE anomaly_flag_status AS ENUM (
    'open',
    'investigating',
    'resolved'
);

-- ============================================================
-- TABLES
-- ============================================================

-- System users. Role assigned at auth time controls access scope and home screen.
CREATE TABLE users (
    user_id         TEXT PRIMARY KEY,            -- e.g., USR-XXXX
    name            TEXT        NOT NULL,
    email           TEXT        NOT NULL UNIQUE,
    role            user_role   NOT NULL,
    is_active       BOOLEAN     NOT NULL DEFAULT true,
    created_date    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login      TIMESTAMPTZ
);

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
    payment_method  TEXT        NOT NULL,  -- ACH, Check, Credit Card, Wire
    sender_account  TEXT,
    status          payment_history_status NOT NULL
);

CREATE INDEX idx_payment_history_policy_date ON payment_history (policy_id, payment_date);

-- Incoming payments to be resolved by the AI agent.
CREATE TABLE payments (
    payment_id          TEXT PRIMARY KEY,            -- e.g., PMT-XXX
    amount              BIGINT      NOT NULL,         -- cents
    sender_name         TEXT        NOT NULL,
    sender_account      TEXT,
    beneficiary_name    TEXT,
    payment_method      TEXT        NOT NULL,         -- ACH, Check, Credit Card, Wire
    payment_date        TIMESTAMPTZ NOT NULL,
    reference_field_1   TEXT,
    reference_field_2   TEXT,
    status              payment_status NOT NULL DEFAULT 'received',
    matched_customer_id TEXT        REFERENCES customers(customer_id),
    matched_policy_id   TEXT        REFERENCES policies(policy_number),
    -- Set when case is escalated to investigation. SLA deadline for Damien.
    investigation_due_date TIMESTAMPTZ,
    -- True when case has exceeded the investigation SLA without resolution.
    sla_breached        BOOLEAN     NOT NULL DEFAULT false,
    created_timestamp   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_payments_date        ON payments (payment_date);
CREATE INDEX idx_payments_sender_name ON payments (sender_name);
CREATE INDEX idx_payments_amount      ON payments (amount);
CREATE INDEX idx_payments_status      ON payments (status);
CREATE INDEX idx_payments_method      ON payments (payment_method);
CREATE INDEX idx_payments_sla         ON payments (sla_breached, investigation_due_date)
    WHERE status IN ('escalated', 'pending_sender_response');

-- Snapshot of all computed signals at decision time (1-to-1 with Payment).
CREATE TABLE payment_signals (
    payment_id      TEXT PRIMARY KEY REFERENCES payments(payment_id),
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Matching signals
    name_similarity_score       DOUBLE PRECISION,   -- 0-100 final score
    policy_match_confidence     DOUBLE PRECISION,   -- 0-100
    customer_match_confidence   DOUBLE PRECISION,   -- 0-100
    account_match               BOOLEAN NOT NULL DEFAULT false,
    amount_match                BOOLEAN NOT NULL DEFAULT false,
    historical_match            BOOLEAN NOT NULL DEFAULT false,

    -- Name matching algorithm breakdown (for Damien's algorithmic provenance)
    jaro_winkler_score          DOUBLE PRECISION,   -- 0-100 raw Jaro-Winkler score
    levenshtein_score           DOUBLE PRECISION,   -- 0-100 Levenshtein-based score
    soundex_match               BOOLEAN NOT NULL DEFAULT false,
    deterministic_score         DOUBLE PRECISION,   -- 0-100 combined deterministic score
    used_llm                    BOOLEAN NOT NULL DEFAULT false,
    llm_score                   DOUBLE PRECISION,   -- 0-100 Haiku score; 0 if not called

    -- Amount signals
    amount_variance_pct             DOUBLE PRECISION,
    is_overpayment                  BOOLEAN NOT NULL DEFAULT false,
    is_underpayment                 BOOLEAN NOT NULL DEFAULT false,
    difference_amount               BIGINT,          -- cents
    is_multi_period                 BOOLEAN NOT NULL DEFAULT false,
    estimated_periods               INT     NOT NULL DEFAULT 0,
    historical_consistency_score    DOUBLE PRECISION, -- 0-100
    is_multi_method                 BOOLEAN NOT NULL DEFAULT false,
    multi_method_fraction           DOUBLE PRECISION,
    is_third_party_payment          BOOLEAN NOT NULL DEFAULT false,
    third_party_relationship        TEXT,            -- 'employer', 'family', 'escrow', etc.

    -- Temporal signals
    payment_timing_quality      payment_timing_quality,
    days_from_due_date          INT,                 -- positive = late, negative = early
    days_since_last_payment     INT,

    -- Risk signals
    has_risk_flags              BOOLEAN NOT NULL DEFAULT false,
    risk_flag_types             risk_flag_type[],
    account_status              account_status,
    payment_method_risk_level   payment_method_risk_level,
    outstanding_balance_cents   BIGINT,              -- snapshot of balance at decision time
    outstanding_balance_status  TEXT,                -- 'current' or 'past_due'

    -- Duplicate signals
    is_duplicate_match              BOOLEAN NOT NULL DEFAULT false,
    duplicate_payment_id            TEXT,
    hours_since_duplicate           DOUBLE PRECISION,
    outstanding_balance_justifies   BOOLEAN NOT NULL DEFAULT false,
    duplicate_amount_difference     BIGINT  NOT NULL DEFAULT 0  -- cents; 0=exact, up to 200=$2
);

-- AI agent recommendation (1-to-1 with Payment).
CREATE TABLE payment_recommendations (
    payment_id              TEXT PRIMARY KEY REFERENCES payments(payment_id),
    recommendation          recommendation  NOT NULL,
    confidence_score        DOUBLE PRECISION NOT NULL,  -- 0-100
    scenario_route          scenario_route  NOT NULL,
    decision_path           TEXT,
    requires_human_approval BOOLEAN NOT NULL DEFAULT false,
    approval_reason         TEXT,
    reasoning               TEXT[],
    suggested_action        TEXT,
    processing_time_ms      INT,
    -- Who ultimately made the final decision. Populated at case closure.
    decision_attribution    decision_attribution,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Persistent annotations on case records (analyst notes, override reasons, contact logs).
-- Append-only — never updated or deleted.
CREATE TABLE case_annotations (
    annotation_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    payment_id      TEXT        NOT NULL REFERENCES payments(payment_id),
    author_user_id  TEXT        NOT NULL REFERENCES users(user_id),
    annotation_type annotation_type NOT NULL,
    content         TEXT        NOT NULL,

    -- Contact record fields (populated when annotation_type = 'contact_record')
    contact_method  TEXT,   -- phone, email, letter
    contact_outcome TEXT,   -- reached, no_answer, voicemail, bounced
    contacted_party TEXT,   -- name/identifier of party contacted

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_case_annotations_payment ON case_annotations (payment_id);
CREATE INDEX idx_case_annotations_type    ON case_annotations (payment_id, annotation_type);

-- Supporting documents attached to cases by analysts or investigators.
-- Files stored in object storage; this table holds metadata only.
CREATE TABLE case_documents (
    document_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    payment_id      TEXT        NOT NULL REFERENCES payments(payment_id),
    uploaded_by     TEXT        NOT NULL REFERENCES users(user_id),
    file_name       TEXT        NOT NULL,
    file_type       TEXT        NOT NULL,   -- MIME type (e.g., application/pdf)
    file_size_bytes BIGINT      NOT NULL,
    storage_path    TEXT        NOT NULL,   -- S3 key or local path
    document_type   document_type NOT NULL,
    description     TEXT,
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_deleted      BOOLEAN     NOT NULL DEFAULT false  -- soft delete only
);

CREATE INDEX idx_case_documents_payment ON case_documents (payment_id);
CREATE INDEX idx_case_documents_active  ON case_documents (payment_id, is_deleted)
    WHERE is_deleted = false;

-- Append-only audit log for compliance.
-- All four users and the system contribute to this log.
CREATE TABLE audit_log (
    log_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    payment_id      TEXT        REFERENCES payments(payment_id),  -- NULL for system-wide events
    action_type     audit_action_type NOT NULL,
    actor           TEXT        NOT NULL,   -- display name: "system" or user name
    actor_user_id   TEXT        REFERENCES users(user_id),  -- NULL for system actions
    details         JSONB,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_log_payment   ON audit_log (payment_id);
CREATE INDEX idx_audit_log_timestamp ON audit_log (timestamp);
CREATE INDEX idx_audit_log_action    ON audit_log (action_type);
CREATE INDEX idx_audit_log_actor     ON audit_log (actor_user_id) WHERE actor_user_id IS NOT NULL;

-- Active configuration thresholds (current values only).
-- For full version history, see configuration_threshold_history.
CREATE TABLE configuration_thresholds (
    parameter_name  TEXT PRIMARY KEY,
    parameter_value TEXT        NOT NULL,
    description     TEXT,
    effective_date  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Formal requests to change a configuration threshold.
-- Every production config change must have an approved request.
CREATE TABLE configuration_change_requests (
    change_id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    parameter_name      TEXT        NOT NULL,
    current_value       TEXT        NOT NULL,
    proposed_value      TEXT        NOT NULL,
    rationale           TEXT        NOT NULL,
    projected_impact    TEXT,
    proposed_by         TEXT        NOT NULL REFERENCES users(user_id),
    approved_by         TEXT        REFERENCES users(user_id),
    review_comment      TEXT,
    status              config_change_status NOT NULL DEFAULT 'pending',
    proposed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_at         TIMESTAMPTZ,
    deployed_at         TIMESTAMPTZ
);

CREATE INDEX idx_config_change_requests_status ON configuration_change_requests (status);
CREATE INDEX idx_config_change_requests_param  ON configuration_change_requests (parameter_name);

-- Append-only version history for every configuration threshold change.
-- Written when a change request is deployed or rolled back.
CREATE TABLE configuration_threshold_history (
    version_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    parameter_name      TEXT        NOT NULL,
    parameter_value     TEXT        NOT NULL,
    changed_by          TEXT        NOT NULL REFERENCES users(user_id),
    approved_by         TEXT        NOT NULL REFERENCES users(user_id),
    rationale           TEXT        NOT NULL,
    change_request_id   BIGINT      REFERENCES configuration_change_requests(change_id),
    effective_from      TIMESTAMPTZ NOT NULL DEFAULT now(),
    effective_to        TIMESTAMPTZ  -- NULL = currently active
);

CREATE INDEX idx_config_history_param   ON configuration_threshold_history (parameter_name);
CREATE INDEX idx_config_history_active  ON configuration_threshold_history (parameter_name, effective_to)
    WHERE effective_to IS NULL;

-- Lorraine's governance review log.
-- Every time she reviews a period's performance report, it is timestamped here.
CREATE TABLE governance_reviews (
    review_id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    reviewed_by         TEXT        NOT NULL REFERENCES users(user_id),
    period_start        DATE        NOT NULL,
    period_end          DATE        NOT NULL,
    review_timestamp    TIMESTAMPTZ NOT NULL DEFAULT now(),
    export_generated    BOOLEAN     NOT NULL DEFAULT false,
    notes               TEXT
);

-- Anomaly flags raised by Lorraine (or system) for Marcus to investigate.
CREATE TABLE anomaly_flags (
    flag_id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    metric_name         TEXT        NOT NULL,   -- e.g., override_rate, escalation_rate
    scenario_type       TEXT,                   -- NULL = system-wide
    description         TEXT        NOT NULL,
    period_start        DATE,
    period_end          DATE,
    flagged_by          TEXT        NOT NULL REFERENCES users(user_id),
    assigned_to         TEXT        REFERENCES users(user_id),
    status              anomaly_flag_status NOT NULL DEFAULT 'open',
    resolution_notes    TEXT,
    flagged_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at         TIMESTAMPTZ
);

CREATE INDEX idx_anomaly_flags_status   ON anomaly_flags (status);
CREATE INDEX idx_anomaly_flags_assigned ON anomaly_flags (assigned_to);
