"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-18

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# asyncpg requires one statement per op.execute() call.

ENUM_TYPES = [
    "CREATE TYPE user_role AS ENUM ('analyst','investigator','director','admin')",
    "CREATE TYPE customer_status AS ENUM ('active','inactive','pending','closed')",
    "CREATE TYPE risk_flag_type AS ENUM ('fraud_history','suspended_account','chronic_late_payments')",
    "CREATE TYPE premium_frequency AS ENUM ('monthly','quarterly','semi_annual','annual')",
    "CREATE TYPE policy_status AS ENUM ('active','inactive','closed')",
    "CREATE TYPE payment_history_status AS ENUM ('applied','bounced','reversed')",
    """CREATE TYPE payment_status AS ENUM (
        'received','processing','applied','held','escalated',
        'processing_failed','pending_sender_response','returned'
    )""",
    "CREATE TYPE payment_timing_quality AS ENUM ('excellent','good','acceptable','poor')",
    "CREATE TYPE account_status AS ENUM ('active','inactive','closed')",
    "CREATE TYPE payment_method_risk_level AS ENUM ('low','medium','high')",
    "CREATE TYPE recommendation AS ENUM ('apply','hold','escalate','return')",
    "CREATE TYPE decision_attribution AS ENUM ('ai_autonomous','human_confirmed','human_override')",
    """CREATE TYPE scenario_route AS ENUM (
        'scenario_1','scenario_2','scenario_3','scenario_4','scenario_5'
    )""",
    """CREATE TYPE audit_action_type AS ENUM (
        'received','signals_computed','recommendation_made','approved','applied','escalated','held',
        'overridden','annotated','document_uploaded','contact_logged','returned',
        'governance_review_recorded','anomaly_flagged','config_change_proposed',
        'config_change_approved','config_change_rejected','config_change_deployed',
        'config_change_rolled_back','sla_breached'
    )""",
    """CREATE TYPE document_type AS ENUM (
        'supporting_evidence','sender_correspondence','bank_statement',
        'fraud_report','policy_document','other'
    )""",
    """CREATE TYPE annotation_type AS ENUM (
        'case_note','override_reason','contact_record','investigation_note'
    )""",
    "CREATE TYPE config_change_status AS ENUM ('pending','approved','rejected','deployed','rolled_back')",
    "CREATE TYPE anomaly_flag_status AS ENUM ('open','investigating','resolved')",
]

TABLES_AND_INDEXES = [
    """CREATE TABLE users (
        user_id         TEXT PRIMARY KEY,
        name            TEXT        NOT NULL,
        email           TEXT        NOT NULL UNIQUE,
        role            user_role   NOT NULL,
        is_active       BOOLEAN     NOT NULL DEFAULT true,
        created_date    TIMESTAMPTZ NOT NULL DEFAULT now(),
        last_login      TIMESTAMPTZ
    )""",
    """CREATE TABLE customers (
        customer_id     TEXT PRIMARY KEY,
        name            TEXT        NOT NULL,
        account_number  TEXT        NOT NULL UNIQUE,
        status          customer_status NOT NULL DEFAULT 'active',
        created_date    TIMESTAMPTZ NOT NULL DEFAULT now(),
        modified_date   TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE risk_flags (
        flag_id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        customer_id     TEXT        NOT NULL REFERENCES customers(customer_id),
        flag_type       risk_flag_type NOT NULL,
        is_active       BOOLEAN     NOT NULL DEFAULT true,
        flagged_date    TIMESTAMPTZ NOT NULL DEFAULT now(),
        notes           TEXT
    )""",
    "CREATE INDEX idx_risk_flags_customer_active ON risk_flags (customer_id, is_active)",
    """CREATE TABLE policies (
        policy_number       TEXT PRIMARY KEY,
        customer_id         TEXT        NOT NULL REFERENCES customers(customer_id),
        policy_type         TEXT        NOT NULL,
        premium_amount      BIGINT      NOT NULL,
        premium_frequency   premium_frequency NOT NULL,
        status              policy_status NOT NULL DEFAULT 'active',
        outstanding_balance BIGINT      NOT NULL DEFAULT 0,
        next_due_date       DATE,
        created_date        TIMESTAMPTZ NOT NULL DEFAULT now(),
        modified_date       TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    "CREATE INDEX idx_policies_customer ON policies (customer_id)",
    "CREATE INDEX idx_policies_status   ON policies (policy_number, status)",
    """CREATE TABLE payment_history (
        history_id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        policy_id       TEXT        NOT NULL REFERENCES policies(policy_number),
        payment_date    TIMESTAMPTZ NOT NULL,
        amount          BIGINT      NOT NULL,
        payment_method  TEXT        NOT NULL,
        sender_account  TEXT,
        status          payment_history_status NOT NULL
    )""",
    "CREATE INDEX idx_payment_history_policy_date ON payment_history (policy_id, payment_date)",
    """CREATE TABLE payments (
        payment_id          TEXT PRIMARY KEY,
        amount              BIGINT      NOT NULL,
        sender_name         TEXT        NOT NULL,
        sender_account      TEXT,
        beneficiary_name    TEXT,
        payment_method      TEXT        NOT NULL,
        payment_date        TIMESTAMPTZ NOT NULL,
        reference_field_1   TEXT,
        reference_field_2   TEXT,
        status              payment_status NOT NULL DEFAULT 'received',
        matched_customer_id TEXT        REFERENCES customers(customer_id),
        matched_policy_id   TEXT        REFERENCES policies(policy_number),
        investigation_due_date TIMESTAMPTZ,
        sla_breached        BOOLEAN     NOT NULL DEFAULT false,
        created_timestamp   TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    "CREATE INDEX idx_payments_date        ON payments (payment_date)",
    "CREATE INDEX idx_payments_sender_name ON payments (sender_name)",
    "CREATE INDEX idx_payments_amount      ON payments (amount)",
    "CREATE INDEX idx_payments_status      ON payments (status)",
    "CREATE INDEX idx_payments_method      ON payments (payment_method)",
    """CREATE INDEX idx_payments_sla ON payments (sla_breached, investigation_due_date)
        WHERE status IN ('escalated', 'pending_sender_response')""",
    """CREATE TABLE payment_signals (
        payment_id                  TEXT PRIMARY KEY REFERENCES payments(payment_id),
        computed_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
        name_similarity_score       DOUBLE PRECISION,
        policy_match_confidence     DOUBLE PRECISION,
        customer_match_confidence   DOUBLE PRECISION,
        account_match               BOOLEAN NOT NULL DEFAULT false,
        amount_match                BOOLEAN NOT NULL DEFAULT false,
        historical_match            BOOLEAN NOT NULL DEFAULT false,
        jaro_winkler_score          DOUBLE PRECISION,
        levenshtein_score           DOUBLE PRECISION,
        soundex_match               BOOLEAN NOT NULL DEFAULT false,
        deterministic_score         DOUBLE PRECISION,
        used_llm                    BOOLEAN NOT NULL DEFAULT false,
        llm_score                   DOUBLE PRECISION,
        amount_variance_pct             DOUBLE PRECISION,
        is_overpayment                  BOOLEAN NOT NULL DEFAULT false,
        is_underpayment                 BOOLEAN NOT NULL DEFAULT false,
        difference_amount               BIGINT,
        is_multi_period                 BOOLEAN NOT NULL DEFAULT false,
        estimated_periods               INT     NOT NULL DEFAULT 0,
        historical_consistency_score    DOUBLE PRECISION,
        is_multi_method                 BOOLEAN NOT NULL DEFAULT false,
        multi_method_fraction           DOUBLE PRECISION,
        is_third_party_payment          BOOLEAN NOT NULL DEFAULT false,
        third_party_relationship        TEXT,
        payment_timing_quality      payment_timing_quality,
        days_from_due_date          INT,
        days_since_last_payment     INT,
        has_risk_flags              BOOLEAN NOT NULL DEFAULT false,
        risk_flag_types             risk_flag_type[],
        account_status              account_status,
        payment_method_risk_level   payment_method_risk_level,
        outstanding_balance_cents   BIGINT,
        outstanding_balance_status  TEXT,
        is_duplicate_match              BOOLEAN NOT NULL DEFAULT false,
        duplicate_payment_id            TEXT,
        hours_since_duplicate           DOUBLE PRECISION,
        outstanding_balance_justifies   BOOLEAN NOT NULL DEFAULT false,
        duplicate_amount_difference     BIGINT  NOT NULL DEFAULT 0
    )""",
    """CREATE TABLE payment_recommendations (
        payment_id              TEXT PRIMARY KEY REFERENCES payments(payment_id),
        recommendation          recommendation  NOT NULL,
        confidence_score        DOUBLE PRECISION NOT NULL,
        scenario_route          scenario_route  NOT NULL,
        decision_path           TEXT,
        requires_human_approval BOOLEAN NOT NULL DEFAULT false,
        approval_reason         TEXT,
        reasoning               TEXT[],
        suggested_action        TEXT,
        processing_time_ms      INT,
        decision_attribution    decision_attribution,
        created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE case_annotations (
        annotation_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        payment_id      TEXT        NOT NULL REFERENCES payments(payment_id),
        author_user_id  TEXT        NOT NULL REFERENCES users(user_id),
        annotation_type annotation_type NOT NULL,
        content         TEXT        NOT NULL,
        contact_method  TEXT,
        contact_outcome TEXT,
        contacted_party TEXT,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    "CREATE INDEX idx_case_annotations_payment ON case_annotations (payment_id)",
    "CREATE INDEX idx_case_annotations_type    ON case_annotations (payment_id, annotation_type)",
    """CREATE TABLE case_documents (
        document_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        payment_id      TEXT        NOT NULL REFERENCES payments(payment_id),
        uploaded_by     TEXT        NOT NULL REFERENCES users(user_id),
        file_name       TEXT        NOT NULL,
        file_type       TEXT        NOT NULL,
        file_size_bytes BIGINT      NOT NULL,
        storage_path    TEXT        NOT NULL,
        document_type   document_type NOT NULL,
        description     TEXT,
        uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
        is_deleted      BOOLEAN     NOT NULL DEFAULT false
    )""",
    "CREATE INDEX idx_case_documents_payment ON case_documents (payment_id)",
    "CREATE INDEX idx_case_documents_active  ON case_documents (payment_id, is_deleted) WHERE is_deleted = false",
    """CREATE TABLE audit_log (
        log_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        payment_id      TEXT        REFERENCES payments(payment_id),
        action_type     audit_action_type NOT NULL,
        actor           TEXT        NOT NULL,
        actor_user_id   TEXT        REFERENCES users(user_id),
        details         JSONB,
        timestamp       TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    "CREATE INDEX idx_audit_log_payment   ON audit_log (payment_id)",
    "CREATE INDEX idx_audit_log_timestamp ON audit_log (timestamp)",
    "CREATE INDEX idx_audit_log_action    ON audit_log (action_type)",
    "CREATE INDEX idx_audit_log_actor     ON audit_log (actor_user_id) WHERE actor_user_id IS NOT NULL",
    """CREATE TABLE configuration_thresholds (
        parameter_name  TEXT PRIMARY KEY,
        parameter_value TEXT        NOT NULL,
        description     TEXT,
        effective_date  TIMESTAMPTZ NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE configuration_change_requests (
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
    )""",
    "CREATE INDEX idx_config_change_requests_status ON configuration_change_requests (status)",
    "CREATE INDEX idx_config_change_requests_param  ON configuration_change_requests (parameter_name)",
    """CREATE TABLE configuration_threshold_history (
        version_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        parameter_name      TEXT        NOT NULL,
        parameter_value     TEXT        NOT NULL,
        changed_by          TEXT        NOT NULL REFERENCES users(user_id),
        approved_by         TEXT        NOT NULL REFERENCES users(user_id),
        rationale           TEXT        NOT NULL,
        change_request_id   BIGINT      REFERENCES configuration_change_requests(change_id),
        effective_from      TIMESTAMPTZ NOT NULL DEFAULT now(),
        effective_to        TIMESTAMPTZ
    )""",
    "CREATE INDEX idx_config_history_param  ON configuration_threshold_history (parameter_name)",
    "CREATE INDEX idx_config_history_active ON configuration_threshold_history (parameter_name, effective_to) WHERE effective_to IS NULL",
    """CREATE TABLE governance_reviews (
        review_id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        reviewed_by         TEXT        NOT NULL REFERENCES users(user_id),
        period_start        DATE        NOT NULL,
        period_end          DATE        NOT NULL,
        review_timestamp    TIMESTAMPTZ NOT NULL DEFAULT now(),
        export_generated    BOOLEAN     NOT NULL DEFAULT false,
        notes               TEXT
    )""",
    """CREATE TABLE anomaly_flags (
        flag_id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        metric_name         TEXT        NOT NULL,
        scenario_type       TEXT,
        description         TEXT        NOT NULL,
        period_start        DATE,
        period_end          DATE,
        flagged_by          TEXT        NOT NULL REFERENCES users(user_id),
        assigned_to         TEXT        REFERENCES users(user_id),
        status              anomaly_flag_status NOT NULL DEFAULT 'open',
        resolution_notes    TEXT,
        flagged_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
        resolved_at         TIMESTAMPTZ
    )""",
    "CREATE INDEX idx_anomaly_flags_status   ON anomaly_flags (status)",
    "CREATE INDEX idx_anomaly_flags_assigned ON anomaly_flags (assigned_to)",
]

DROP_STATEMENTS = [
    "DROP TABLE IF EXISTS anomaly_flags CASCADE",
    "DROP TABLE IF EXISTS governance_reviews CASCADE",
    "DROP TABLE IF EXISTS configuration_threshold_history CASCADE",
    "DROP TABLE IF EXISTS configuration_change_requests CASCADE",
    "DROP TABLE IF EXISTS configuration_thresholds CASCADE",
    "DROP TABLE IF EXISTS audit_log CASCADE",
    "DROP TABLE IF EXISTS case_documents CASCADE",
    "DROP TABLE IF EXISTS case_annotations CASCADE",
    "DROP TABLE IF EXISTS payment_recommendations CASCADE",
    "DROP TABLE IF EXISTS payment_signals CASCADE",
    "DROP TABLE IF EXISTS payments CASCADE",
    "DROP TABLE IF EXISTS payment_history CASCADE",
    "DROP TABLE IF EXISTS policies CASCADE",
    "DROP TABLE IF EXISTS risk_flags CASCADE",
    "DROP TABLE IF EXISTS customers CASCADE",
    "DROP TABLE IF EXISTS users CASCADE",
    "DROP TYPE IF EXISTS anomaly_flag_status CASCADE",
    "DROP TYPE IF EXISTS config_change_status CASCADE",
    "DROP TYPE IF EXISTS annotation_type CASCADE",
    "DROP TYPE IF EXISTS document_type CASCADE",
    "DROP TYPE IF EXISTS audit_action_type CASCADE",
    "DROP TYPE IF EXISTS scenario_route CASCADE",
    "DROP TYPE IF EXISTS decision_attribution CASCADE",
    "DROP TYPE IF EXISTS recommendation CASCADE",
    "DROP TYPE IF EXISTS payment_method_risk_level CASCADE",
    "DROP TYPE IF EXISTS account_status CASCADE",
    "DROP TYPE IF EXISTS payment_timing_quality CASCADE",
    "DROP TYPE IF EXISTS payment_status CASCADE",
    "DROP TYPE IF EXISTS payment_history_status CASCADE",
    "DROP TYPE IF EXISTS policy_status CASCADE",
    "DROP TYPE IF EXISTS premium_frequency CASCADE",
    "DROP TYPE IF EXISTS risk_flag_type CASCADE",
    "DROP TYPE IF EXISTS customer_status CASCADE",
    "DROP TYPE IF EXISTS user_role CASCADE",
]


def upgrade() -> None:
    for stmt in ENUM_TYPES + TABLES_AND_INDEXES:
        op.execute(stmt)


def downgrade() -> None:
    for stmt in DROP_STATEMENTS:
        op.execute(stmt)
