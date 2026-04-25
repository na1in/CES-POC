/**
 * CES-12 — Mock data validation
 *
 * These tests enforce that every mock fixture matches the proto-derived
 * TypeScript types exactly. They act as a regression guard: if a type
 * changes (e.g. a new required field is added to the proto) and the mock
 * isn't updated, a test here will catch it before it breaks a page.
 */

import {
  mockPayments,
  mockPaymentSignals,
  mockRecommendations,
  mockAnnotations,
  mockAuditLogs,
} from "@/mocks/payments"
import type { PaymentStatus, PaymentMethod } from "@/types/payment"
import type { ScenarioRoute } from "@/types/recommendation"
import type { AnnotationType } from "@/types/annotation"
import type { AuditActionType } from "@/types/user"
import type { RiskFlagType, AccountStatus, PaymentMethodRiskLevel, PaymentTimingQuality } from "@/types/signals"

// ── Valid enum values (mirrors the TypeScript types) ─────────────────────────

const VALID_STATUSES: PaymentStatus[] = [
  "received", "processing", "applied", "held", "escalated",
  "processing_failed", "pending_sender_response", "returned",
]
const VALID_METHODS: PaymentMethod[] = ["ACH", "Check", "Credit Card", "Wire"]
const VALID_SCENARIOS: ScenarioRoute[] = [
  "scenario_1", "scenario_2", "scenario_3", "scenario_4", "scenario_5",
]
const VALID_ANNOTATION_TYPES: AnnotationType[] = [
  "case_note", "override_reason", "contact_record", "investigation_note",
]
const VALID_AUDIT_ACTIONS: AuditActionType[] = [
  "received", "signals_computed", "recommendation_made", "approved", "applied",
  "escalated", "held", "overridden", "annotated", "document_uploaded",
  "contact_logged", "returned", "governance_review_recorded", "anomaly_flagged",
  "config_change_proposed", "config_change_approved", "config_change_rejected",
  "config_change_deployed", "config_change_rolled_back", "sla_breached",
]
const VALID_RISK_FLAG_TYPES: RiskFlagType[] = [
  "fraud_history", "suspended_account", "chronic_late_payments",
]
const VALID_ACCOUNT_STATUSES: AccountStatus[] = ["active", "inactive", "closed"]
const VALID_RISK_LEVELS: PaymentMethodRiskLevel[] = ["low", "medium", "high"]
const VALID_TIMING_QUALITIES: PaymentTimingQuality[] = [
  "excellent", "good", "acceptable", "poor",
]

function isValidISO(value: string): boolean {
  return !isNaN(Date.parse(value))
}

// ── mockPayments ─────────────────────────────────────────────────────────────

describe("mockPayments (CES-12)", () => {
  it("contains at least 8 payments", () => {
    expect(mockPayments.length).toBeGreaterThanOrEqual(8)
  })

  it("all payment_ids are unique", () => {
    const ids = mockPayments.map(p => p.payment_id)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it("all payment_ids follow PMT-XXX format", () => {
    mockPayments.forEach(p => {
      expect(p.payment_id).toMatch(/^PMT-\d+$/)
    })
  })

  it("all amounts are positive integers (cents — never floats)", () => {
    mockPayments.forEach(p => {
      expect(Number.isInteger(p.amount)).toBe(true)
      expect(p.amount).toBeGreaterThan(0)
    })
  })

  it("all statuses are valid PaymentStatus values", () => {
    mockPayments.forEach(p => {
      expect(VALID_STATUSES).toContain(p.status)
    })
  })

  it("all payment methods are valid PaymentMethod values", () => {
    mockPayments.forEach(p => {
      expect(VALID_METHODS).toContain(p.payment_method)
    })
  })

  it("payment_date and created_timestamp are valid ISO strings", () => {
    mockPayments.forEach(p => {
      expect(isValidISO(p.payment_date)).toBe(true)
      expect(isValidISO(p.created_timestamp)).toBe(true)
    })
  })

  it("investigation_due_date is null or a valid ISO string", () => {
    mockPayments.forEach(p => {
      if (p.investigation_due_date !== null) {
        expect(isValidISO(p.investigation_due_date)).toBe(true)
      }
    })
  })

  it("covers all 5 scenarios (has at least one payment per scenario_route)", () => {
    const routes = new Set(
      Object.values(mockRecommendations).map(r => r.scenario_route)
    )
    VALID_SCENARIOS.forEach(s => expect(routes).toContain(s))
  })

  it("includes at least one processing_failed payment", () => {
    expect(mockPayments.some(p => p.status === "processing_failed")).toBe(true)
  })

  it("includes at least one sla_breached payment", () => {
    expect(mockPayments.some(p => p.sla_breached === true)).toBe(true)
  })
})

// ── mockPaymentSignals ────────────────────────────────────────────────────────

describe("mockPaymentSignals (CES-12)", () => {
  it("has a signals entry for every payment", () => {
    mockPayments.forEach(p => {
      expect(mockPaymentSignals[p.payment_id]).toBeDefined()
    })
  })

  it("computed_at is a valid ISO string", () => {
    Object.values(mockPaymentSignals).forEach(s => {
      expect(isValidISO(s.computed_at)).toBe(true)
    })
  })

  it("all matching scores are in range 0–100", () => {
    Object.values(mockPaymentSignals).forEach(({ matching: m }) => {
      const scores = [
        m.name_similarity_score, m.policy_match_confidence, m.customer_match_confidence,
        m.jaro_winkler_score, m.levenshtein_score, m.deterministic_score, m.llm_score,
      ]
      scores.forEach(score => {
        expect(score).toBeGreaterThanOrEqual(0)
        expect(score).toBeLessThanOrEqual(100)
      })
    })
  })

  it("llm_score is 0 when used_llm is false", () => {
    Object.values(mockPaymentSignals).forEach(({ matching: m }) => {
      if (!m.used_llm) {
        expect(m.llm_score).toBe(0)
      }
    })
  })

  it("historical_consistency_score is in range 0–100", () => {
    Object.values(mockPaymentSignals).forEach(({ amount: a }) => {
      expect(a.historical_consistency_score).toBeGreaterThanOrEqual(0)
      expect(a.historical_consistency_score).toBeLessThanOrEqual(100)
    })
  })

  it("is_overpayment and is_underpayment are mutually exclusive", () => {
    Object.values(mockPaymentSignals).forEach(({ amount: a }) => {
      expect(a.is_overpayment && a.is_underpayment).toBe(false)
    })
  })

  it("payment_timing_quality is a valid enum value", () => {
    Object.values(mockPaymentSignals).forEach(({ temporal: t }) => {
      expect(VALID_TIMING_QUALITIES).toContain(t.payment_timing_quality)
    })
  })

  it("risk_flag_types contains only valid RiskFlagType values", () => {
    Object.values(mockPaymentSignals).forEach(({ risk: r }) => {
      r.risk_flag_types.forEach(flag => {
        expect(VALID_RISK_FLAG_TYPES).toContain(flag)
      })
    })
  })

  it("account_status is a valid AccountStatus value", () => {
    Object.values(mockPaymentSignals).forEach(({ risk: r }) => {
      expect(VALID_ACCOUNT_STATUSES).toContain(r.account_status)
    })
  })

  it("payment_method_risk_level is a valid PaymentMethodRiskLevel value", () => {
    Object.values(mockPaymentSignals).forEach(({ risk: r }) => {
      expect(VALID_RISK_LEVELS).toContain(r.payment_method_risk_level)
    })
  })

  it("duplicate_payment_id references an existing payment when is_duplicate_match is true", () => {
    const paymentIds = new Set(mockPayments.map(p => p.payment_id))
    Object.values(mockPaymentSignals).forEach(({ duplicate: d }) => {
      if (d.is_duplicate_match) {
        expect(paymentIds).toContain(d.duplicate_payment_id)
      }
    })
  })

  it("duplicate_amount_difference is within $2 tolerance (≤200 cents)", () => {
    Object.values(mockPaymentSignals).forEach(({ duplicate: d }) => {
      if (d.is_duplicate_match) {
        expect(d.duplicate_amount_difference).toBeLessThanOrEqual(200)
        expect(d.duplicate_amount_difference).toBeGreaterThanOrEqual(0)
      }
    })
  })
})

// ── mockRecommendations ───────────────────────────────────────────────────────

describe("mockRecommendations (CES-12)", () => {
  it("has a recommendation for every payment", () => {
    mockPayments.forEach(p => {
      expect(mockRecommendations[p.payment_id]).toBeDefined()
    })
  })

  it("all confidence scores are in range 0–100", () => {
    Object.values(mockRecommendations).forEach(r => {
      expect(r.confidence_score).toBeGreaterThanOrEqual(0)
      expect(r.confidence_score).toBeLessThanOrEqual(100)
    })
  })

  it("all scenario_routes are valid", () => {
    Object.values(mockRecommendations).forEach(r => {
      expect(VALID_SCENARIOS).toContain(r.scenario_route)
    })
  })

  it("all recommendations are apply | hold | escalate (never 'return')", () => {
    Object.values(mockRecommendations).forEach(r => {
      expect(["apply", "hold", "escalate"]).toContain(r.recommendation)
    })
  })

  it("requires_human_approval=false only when recommendation is apply", () => {
    Object.values(mockRecommendations).forEach(r => {
      if (!r.requires_human_approval) {
        expect(r.recommendation).toBe("apply")
      }
    })
  })

  it("reasoning is a non-empty array of strings", () => {
    Object.values(mockRecommendations).forEach(r => {
      expect(Array.isArray(r.reasoning)).toBe(true)
      expect(r.reasoning.length).toBeGreaterThan(0)
      r.reasoning.forEach(line => expect(typeof line).toBe("string"))
    })
  })

  it("created_at is a valid ISO string", () => {
    Object.values(mockRecommendations).forEach(r => {
      expect(isValidISO(r.created_at)).toBe(true)
    })
  })
})

// ── mockAnnotations ───────────────────────────────────────────────────────────

describe("mockAnnotations (CES-12)", () => {
  const allAnnotations = Object.values(mockAnnotations).flat()

  it("all annotation_ids are unique positive integers", () => {
    const ids = allAnnotations.map(a => a.annotation_id)
    expect(new Set(ids).size).toBe(ids.length)
    ids.forEach(id => {
      expect(Number.isInteger(id)).toBe(true)
      expect(id).toBeGreaterThan(0)
    })
  })

  it("all annotation_types are valid", () => {
    allAnnotations.forEach(a => {
      expect(VALID_ANNOTATION_TYPES).toContain(a.annotation_type)
    })
  })

  it("all payment_ids reference existing payments", () => {
    const paymentIds = new Set(mockPayments.map(p => p.payment_id))
    allAnnotations.forEach(a => {
      expect(paymentIds).toContain(a.payment_id)
    })
  })

  it("created_at is a valid ISO string", () => {
    allAnnotations.forEach(a => {
      expect(isValidISO(a.created_at)).toBe(true)
    })
  })
})

// ── mockAuditLogs ─────────────────────────────────────────────────────────────

describe("mockAuditLogs (CES-12)", () => {
  const allLogs = Object.values(mockAuditLogs).flat()

  it("all log_ids are unique positive integers", () => {
    const ids = allLogs.map(l => l.log_id)
    expect(new Set(ids).size).toBe(ids.length)
    ids.forEach(id => {
      expect(Number.isInteger(id)).toBe(true)
      expect(id).toBeGreaterThan(0)
    })
  })

  it("all action_types are valid AuditActionType values", () => {
    allLogs.forEach(l => {
      expect(VALID_AUDIT_ACTIONS).toContain(l.action_type)
    })
  })

  it("all payment_ids reference existing payments", () => {
    const paymentIds = new Set(mockPayments.map(p => p.payment_id))
    allLogs.forEach(l => {
      expect(paymentIds).toContain(l.payment_id)
    })
  })

  it("first log for each payment is always 'received'", () => {
    Object.values(mockAuditLogs).forEach(logs => {
      expect(logs[0].action_type).toBe("received")
    })
  })

  it("timestamp is a valid ISO string", () => {
    allLogs.forEach(l => {
      expect(isValidISO(l.timestamp)).toBe(true)
    })
  })
})
