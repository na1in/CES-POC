"""
Synthetic evaluation data generator.

Stage 1  world  — Gemini 2.5 Flash generates customers, policies and payment history.
Stage 2  cases  — Gemini 2.5 Flash instantiates test payments per archetype against that world
                  (batched per archetype, with a repair loop for cases that fail their checks).
Stage 3  checks — plain arithmetic (no pipeline code) verifies each case satisfies its archetype.
Stage 4  noise  — (--full) deterministic, seeded perturbations of valid cases: messy references,
                  case/punctuation changes in names, single-character name typos.

Expected outcomes come from the human-written ARCHETYPES table below (derived from
docs/Final_Scenario_Definitions.md), never from the LLM — the LLM only supplies realistic
concrete data. Cases that fail their checks are reported and excluded from scoring.

Usage (from backend/):
  python scripts/eval/generate.py                # pilot: 1 case per archetype, no noise
  python scripts/eval/generate.py --full         # full: 6 per archetype + noise twins
"""
import argparse
import asyncio
import difflib
import json
import random
import re
import sys
import time
from pathlib import Path
from typing import Literal

import openai
from pydantic import BaseModel

BACKEND = Path(__file__).resolve().parents[2]
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from app.config import settings  # noqa: E402
from app.routers.payments import ALLOWED_PAYMENT_METHODS  # noqa: E402

MODEL = "google/gemini-2.5-flash"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
PROTO_DIR = REPO / "proto"
POLICY_RE = re.compile(r"POL-\d{5}")
THIRD_PARTY_RE = re.compile(r"\b(LLC|Inc|Corp|Ltd|Payroll|Trust|Escrow|Mortgage|Services|Holdings|Properties)\b", re.I)
CONCURRENCY = 4
NOISE_SEED = 7


# ── Proto-derived enums (proto files stay the single source of truth) ────────

def proto_enum(file: str, enum: str) -> tuple[str, ...]:
    """Lowercase DB-style values of a proto enum: drops *_UNSPECIFIED and the enum-name prefix."""
    body = re.search(rf"enum {enum} \{{(.*?)\}}", (PROTO_DIR / file).read_text(), re.S).group(1)
    prefix = re.sub(r"(?<!^)(?=[A-Z])", "_", enum).upper() + "_"
    names = re.findall(r"^\s*([A-Z_]+)\s*=", body, re.M)
    return tuple(n[len(prefix):].lower() for n in names if not n.endswith("UNSPECIFIED"))


CUSTOMER_STATUS = proto_enum("customer.proto", "CustomerStatus")
RISK_FLAGS = proto_enum("customer.proto", "RiskFlagType")
FREQUENCY = proto_enum("policy.proto", "PremiumFrequency")
POLICY_STATUS = proto_enum("policy.proto", "PolicyStatus")
HISTORY_STATUS = proto_enum("policy.proto", "PaymentHistoryStatus")
METHODS = tuple(sorted(ALLOWED_PAYMENT_METHODS))


# ── Generator-facing schema (dollars + relative days: far more reliable for an LLM than cents/timestamps) ──

class GenHistory(BaseModel):
    days_ago: int
    amount_usd: float
    payment_method: Literal[METHODS]
    sender_account: str
    status: Literal[HISTORY_STATUS]


class GenPolicy(BaseModel):
    policy_number: str
    policy_type: Literal["Auto", "Home", "Life", "Health"]
    premium_usd: float
    premium_frequency: Literal[FREQUENCY]
    status: Literal[POLICY_STATUS]
    outstanding_balance_usd: float
    next_due_in_days: int
    history: list[GenHistory]


class GenCustomer(BaseModel):
    customer_id: str
    name: str
    account_number: str
    status: Literal[CUSTOMER_STATUS]
    risk_flags: list[Literal[RISK_FLAGS]]
    policies: list[GenPolicy]


class World(BaseModel):
    customers: list[GenCustomer]


class GenPayment(BaseModel):
    sender_name: str
    sender_account: str      # "" = none
    beneficiary_name: str    # "" = none
    payment_method: Literal[METHODS]
    amount_usd: float
    hours_ago: float
    reference_field_1: str   # "" = none
    reference_field_2: str   # "" = none


class GenCase(BaseModel):
    archetype_id: str
    target_customer_id: str      # "" when the payer is not a known customer
    target_policy_number: str    # "" when no policy is targeted
    payment: GenPayment
    prior_payments: list[GenPayment]   # duplicate archetypes: exactly one; otherwise empty
    rationale: str


class Cases(BaseModel):
    cases: list[GenCase]


# ── Archetypes: the human-written ground truth ───────────────────────────────

ARCHETYPES = [
    # id, expected scenario, expected AI recommendation, construction brief for the LLM
    ("S1-apply-a", 1, "apply",
     "Known ACTIVE customer with NO risk flags and an ACTIVE policy. The sender name is the customer's name with only a trivial "
     "variation (an added middle initial, or 'Robert' vs 'Robert J.'). Method ACH. Amount within 1% of the policy premium "
     "(exactly equal is fine). reference_field_1 contains the policy number."),
    ("S1-apply-b", 1, "apply",
     "As S1-apply-a for a DIFFERENT customer, but method Credit Card and the sender name exactly equals the customer name."),
    ("S1-hold-name", 1, "hold",
     "Known active customer, no risk flags, active policy, method ACH, amount within 1% of premium, reference_field_1 contains "
     "the policy number. The sender name is a noticeably different variant of the customer name (a nickname, initials only, or a "
     "transposed/misspelled surname) that still clearly refers to the same person — a fuzzy similarity of roughly 75-90%."),
    ("S1-hold-risk", 1, "hold",
     "Known customer WITH an active risk flag, active policy, exact sender name, method ACH, amount exactly the premium, "
     "reference_field_1 contains the policy number."),
    ("S2-apply-single", 2, "apply",
     "Known active customer with NO risk flags who has EXACTLY ONE active policy. Sender name exactly equals the customer name. "
     "NO policy number anywhere in the reference fields (use e.g. 'Insurance premium'). Amount within 1% of that policy's premium. Method ACH."),
    ("S2-apply-multi-unique", 2, "apply",
     "Known active customer, no risk flags, with TWO OR MORE active policies whose premiums differ from each other by more than 30%. "
     "Exact sender name, NO policy number in the reference fields. Amount equal to the premium of exactly one of the policies. Method ACH."),
    ("S2-hold-multi-ambiguous", 2, "hold",
     "Known active customer, no risk flags, with TWO active policies that have IDENTICAL premiums. Exact sender name, NO policy "
     "number in the reference fields. Amount equal to that shared premium. Method ACH."),
    ("S2-apply-single-card", 2, "apply",
     "As S2-apply-single for a DIFFERENT customer, method Credit Card, and reference_field_1 empty."),
    ("S3-tier3-above", 3, "hold",
     "Known active customer, no risk flags, active policy; exact sender name; reference_field_1 contains the policy number; method ACH. "
     "Amount is 20-40% ABOVE the premium and NOT within 10% of a whole multiple of the premium."),
    ("S3-tier3-below", 3, "hold",
     "As S3-tier3-above for a DIFFERENT customer, method Wire, with the amount 20-40% BELOW the premium."),
    ("S3-tier4", 3, "hold",
     "As S3-tier3-above but the amount is 60-90% above the premium (not within 10% of a whole multiple of the premium)."),
    ("S3-tier5", 3, "escalate",
     "As S3-tier3-above but the amount is between 2.6x and 2.85x the premium."),
    ("S4-unknown-person", 4, "escalate",
     "The payer is NOT in the world: a realistic personal name dissimilar to every customer name (different first AND last names). "
     "No policy number in the reference fields (e.g. 'Insurance' or empty). Any method, any plausible amount."),
    ("S4-unknown-company", 4, "escalate",
     "The payer is a company NOT in the world (e.g. a trading or property company) sharing no words with any customer name; no policy "
     "number in the reference fields; method Wire or Check."),
    ("S4-third-party-hold", 4, "hold",
     "A third party pays for a known customer: the sender is an employer, payroll processor, mortgage escrow or family trust "
     "(e.g. 'Northwind Payroll LLC'), NOT a customer name. reference_field_1 contains an EXISTING active policy's number. Amount within "
     "10% of that policy's premium. Method ACH or Wire."),
    ("S4-bad-policy-ref", 4, "escalate",
     "The payer is NOT in the world (dissimilar to all customer names) and reference_field_1 quotes a policy number in the right "
     "format (POL-#####) that does NOT exist in the world."),
    ("S5-dup-exact", 5, "escalate",
     "DUPLICATE. Known active customer, no risk flags, whose policy has outstanding balance 0. prior_payments holds ONE payment that is "
     "identical to the payment in sender_name (exact customer name), sender_account, payment_method, amount and both reference fields "
     "(reference_field_1 contains the policy number). The prior payment is 20-60 hours OLDER than the payment. Amount within 1% of premium. Method ACH."),
    ("S5-dup-tolerance", 5, "escalate",
     "As S5-dup-exact for a DIFFERENT customer/policy with balance 0, but the payment amount differs from the prior payment's amount by exactly $1.00."),
    ("S5-dup-balance", 5, "hold",
     "As S5-dup-exact but the policy has an OUTSTANDING BALANCE greater than 0 (use the world's customer with a positive balance)."),
    ("S5-near-dup-control", 1, "apply",
     "NOT a duplicate. As S5-dup-exact (balance 0, same sender/account/method/references, prior payment 20-60 hours older) EXCEPT the "
     "payment amount is exactly $10.00 higher than the prior payment's. Choose a policy with premium >= $600 and let the PRIOR payment "
     "equal the premium, so the payment stays within 2% of the premium but more than $2 from the prior payment."),
    ("S5-diff-ref-not-dup", 1, "apply",
     "NOT a duplicate per the specification, because the policy reference differs. Use a known active customer with no risk flags who has TWO "
     "active policies with IDENTICAL premiums and outstanding balance 0 on both. prior_payments holds ONE payment for the FIRST policy "
     "(reference_field_1 contains the first policy number); the payment is for the SECOND policy (reference_field_1 contains the second "
     "policy number; target_policy_number is the second policy). Same exact customer name, same non-empty sender_account, same method ACH, "
     "same amount (the shared premium). The prior payment is 20-60 hours OLDER."),
    ("S5-diff-account-dup", 5, "escalate",
     "DUPLICATE per the specification: sender name, payment method, policy reference and amount all match (the account is not one of the "
     "criteria). Known active customer, no risk flags, outstanding balance 0. prior_payments holds ONE payment identical to the payment in "
     "sender_name, payment_method, amount and both reference fields (reference_field_1 contains the policy number) but with a DIFFERENT "
     "non-empty sender_account (another bank account or card). The prior payment is 20-60 hours OLDER. Amount equal to the premium. Method ACH."),
]
ARCHETYPE = {a[0]: a for a in ARCHETYPES}

CHUNK = {"customers": 12, "risk": 2, "inactive": 1, "single": 3, "diff": 2, "ident": 0, "balance": 2, "big": 3}
CHUNKS_FULL = 3  # long single-shot worlds drift (wrong size, identifier formats), so the world is built in chunks


IDENT_CHUNK = 6  # customers that each hold two identical-premium active policies (S2-hold-multi-ambiguous, S5-diff-ref-not-dup)

WORLD_TAIL = """- Every policy has 6 history entries, days_ago spaced by the premium frequency, amount_usd equal to the premium, status 'applied',
  varied payment_method, and sender_account equal to the customer's account_number.
- next_due_in_days between -5 and 30."""


def world_requirements(s: dict, k: int, existing: list, kind: str = "regular") -> str:
    first = 9001 + len(existing)
    taken = ", ".join(c.name for c in existing)
    avoid = f"\n- These names are already taken; use different first names AND surnames, and nothing resembling them: {taken}." if taken else ""
    ids = (f"Unique account_number ACC-{90001 + 1000 * k}, ACC-{90002 + 1000 * k}, ... in order. "
           f"Unique policy_number POL-{90001 + 1000 * k}, POL-{90002 + 1000 * k}, ... in order (always 5 digits).")
    if kind == "ident":
        return f"""Generate {IDENT_CHUNK} fictional customers (customer_id CUST-{first} .. CUST-{first + IDENT_CHUNK - 1}). EVERY one of them:
- has status 'active' and NO risk flags; culturally diverse full name; no shared surnames and no lookalike names.{avoid}
- holds EXACTLY TWO policies, both 'active', with IDENTICAL premium_usd and premium_frequency (e.g. two policies at 210 monthly, or two at 1200
  annual) and outstanding_balance_usd 0 on both. Vary the premium level across customers (some 80-450 monthly, some 900-2500 annual).
- {ids}
{WORLD_TAIL}"""
    last = first + s["customers"] - 1
    return f"""Generate {s['customers']} fictional customers (customer_id CUST-{first} .. CUST-{last}) with these features:
- Realistic, culturally diverse full names. No two customers share a surname and no two names look alike.{avoid}
- Exactly {s['inactive']} 'inactive' customer(s); every other customer 'active'. {ids}
- 1-2 policies per customer. Realistic USD premiums: Auto/Health 80-450 monthly; Home 900-2500 semi_annual or annual; Life 300-5000 annual.
- Exactly {s['risk']} customers carry an active risk flag (half fraud_history, half chronic_late_payments); all have active policies.
- At least {s['diff']} customers (no risk flags) with two ACTIVE policies whose premiums differ by more than 30%.
- At least {s['single']} customers with exactly one ACTIVE policy, no risk flags, active status.
- At least {s['balance']} ACTIVE policies with a positive outstanding_balance_usd (their customers active with no risk flags).
- At least {s['big']} ACTIVE policies (customers with no risk flags) with premium >= 600 USD and outstanding balance 0.
{WORLD_TAIL}"""


def ident_problems(part: World) -> list[str]:
    problems = []
    if len(part.customers) != IDENT_CHUNK:
        problems.append(f"{len(part.customers)} customers, wanted {IDENT_CHUNK}")
    for c in part.customers:
        active = [p for p in c.policies if p.status == "active"]
        if c.status != "active" or c.risk_flags or len(c.policies) != 2 or len(active) != 2 \
                or len({p.premium_usd for p in active}) != 1 or any(p.outstanding_balance_usd for p in active):
            problems.append(f"{c.customer_id} does not hold two identical clean active policies")
    surnames = [c.name.split()[-1].lower() for c in part.customers]
    if len(set(surnames)) != len(surnames):
        problems.append("customers share a surname")
    return problems


# ── LLM plumbing ─────────────────────────────────────────────────────────────

def _inline(schema: dict) -> dict:
    """Inline $refs and drop $defs/title/default — provider-friendly JSON Schema."""
    defs = schema.get("$defs", {})

    def walk(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return walk(defs[node["$ref"].split("/")[-1]])
            return {k: walk(v) for k, v in node.items() if k not in ("$defs", "title", "default")}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(schema)


def _data_model_text() -> str:
    payment_msg = re.search(r"message Payment \{.*?\n\}", (PROTO_DIR / "payment.proto").read_text(), re.S).group(0)
    return "\n\n".join([(PROTO_DIR / "customer.proto").read_text(), (PROTO_DIR / "policy.proto").read_text(), payment_msg])


SYSTEM = (
    "You generate fictional, internally consistent test data for an insurance payment-exception system. "
    "The system's data model is defined by these protobuf files (the source of truth):\n\n"
    f"{_data_model_text()}\n\n"
    "Everything you produce is synthetic. Follow every constraint in the request exactly. Return only JSON matching the response schema."
)


async def ask(client: openai.AsyncOpenAI, user: str, model_cls: type[BaseModel], name: str):
    schema = _inline(model_cls.model_json_schema())
    kwargs = dict(
        model=MODEL, temperature=0.7, max_tokens=60000, timeout=400,
        messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
    )
    try:
        resp = await client.chat.completions.create(
            **kwargs, response_format={"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": schema}},
        )
        mode = "json_schema"
    except openai.BadRequestError as exc:
        print(f"  json_schema mode rejected ({exc.message[:120]}); falling back to json_object")
        kwargs["messages"][1]["content"] += "\n\nReturn ONLY a JSON object matching this JSON Schema:\n" + json.dumps(schema)
        resp = await client.chat.completions.create(**kwargs, response_format={"type": "json_object"})
        mode = "json_object"
    text = resp.choices[0].message.content.strip()
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:-1])
    usage = {"prompt_tokens": resp.usage.prompt_tokens, "completion_tokens": resp.usage.completion_tokens}
    return model_cls.model_validate_json(text), mode, usage


# ── Independent checks (plain arithmetic; nothing imported from the pipeline) ─

def cross_problems(existing: list[GenCustomer], new: list[GenCustomer]) -> list[str]:
    ids = {c.customer_id for c in existing}
    accts = {c.account_number for c in existing}
    pols = {p.policy_number for c in existing for p in c.policies}
    problems = []
    if any(c.customer_id in ids or c.account_number in accts or any(p.policy_number in pols for p in c.policies) for c in new):
        problems.append("identifiers collide with earlier chunks")
    lookalikes = [(c.name, e.name) for c in new for e in existing if _ratio(c.name, e.name) >= 0.85]
    if lookalikes:
        problems.append(f"name looks like an earlier customer's: {lookalikes[:2]}")
    return problems


def world_problems(world: World, s: dict, scale: int = 1, unique_surnames: bool = True) -> list[str]:
    s = {key: value * scale for key, value in s.items()}
    problems: list[str] = []
    cust = world.customers
    ids = [c.customer_id for c in cust]
    pols = [p.policy_number for c in cust for p in c.policies]
    accts = [c.account_number for c in cust]
    active = lambda c: [p for p in c.policies if p.status == "active"]  # noqa: E731
    clean = [c for c in cust if c.status == "active" and not c.risk_flags]
    if len(cust) != s["customers"]:
        problems.append(f"{len(cust)} customers, wanted {s['customers']}")
    if len(set(ids)) != len(ids) or len(set(pols)) != len(pols) or len(set(accts)) != len(accts):
        problems.append("duplicate customer/policy/account identifiers")
    surnames = [c.name.split()[-1].lower() for c in cust]
    if unique_surnames and len(set(surnames)) != len(surnames):
        problems.append("customers share a surname")
    bad = [i for i in ids if not re.fullmatch(r"CUST-\d{4}", i)] + [p for p in pols if not re.fullmatch(r"POL-\d{5}", p)]
    if bad:
        problems.append(f"identifier format: {bad[:3]}")
    if sum(1 for c in cust if c.risk_flags) != s["risk"]:
        problems.append(f"need exactly {s['risk']} customers with risk flags")
    different = [c for c in clean if len(active(c)) >= 2 and max(p.premium_usd for p in active(c)) > 1.3 * min(p.premium_usd for p in active(c))]
    if len(different) < s["diff"]:
        problems.append("too few clean customers with two clearly different active premiums")
    ident = [c for c in clean if len(active(c)) >= 2 and len({p.premium_usd for p in active(c)}) < len(active(c))
             and all(p.outstanding_balance_usd == 0 for p in active(c))]
    if len(ident) < s["ident"]:
        problems.append("too few clean customers with two identical active premiums and zero balances")
    if sum(1 for c in clean if len(active(c)) == 1) < s["single"]:
        problems.append("too few clean single-policy customers")
    if sum(1 for c in clean for p in active(c) if p.outstanding_balance_usd > 0) < s["balance"]:
        problems.append("too few clean active policies with a positive balance")
    if sum(1 for c in clean for p in active(c) if p.premium_usd >= 600 and p.outstanding_balance_usd == 0) < s["big"]:
        problems.append("too few clean policies with premium >= 600 and balance 0")
    return problems


def _ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def check_case(case: GenCase, world: World) -> tuple[list[str], list[str]]:
    """Return (failures, warnings). Failures exclude the case from scoring; warnings are informational."""
    aid = case.archetype_id
    customers = {c.customer_id: c for c in world.customers}
    policies = {p.policy_number: (c, p) for c in world.customers for p in c.policies}
    pay, fails, warns = case.payment, [], []
    refs = f"{pay.reference_field_1} {pay.reference_field_2}"
    tokens = POLICY_RE.findall(refs)
    cust = customers.get(case.target_customer_id)
    pol_c, pol = policies.get(case.target_policy_number, (None, None))
    best_name = max((_ratio(pay.sender_name, c.name) for c in world.customers), default=0.0)

    def variance() -> float | None:
        return None if pol is None else (pay.amount_usd - pol.premium_usd) / pol.premium_usd * 100

    def need(cond: bool, msg: str) -> None:
        if not cond:
            fails.append(msg)

    if aid.startswith(("S1", "S3", "S5")):
        need(cust is not None and pol is not None and pol_c is cust, "target customer/policy missing or mismatched")
        if cust is None or pol is None:
            return fails, warns
        need(cust.status == "active" and pol.status == "active", "customer/policy not active")
        need(case.target_policy_number in tokens, "policy number not in reference fields")

    if aid in ("S1-apply-a", "S1-apply-b", "S1-hold-name", "S1-hold-risk"):
        need(abs(variance()) <= 2.0, f"variance {variance():.2f}% > 2%")
        need(bool(cust.risk_flags) == (aid == "S1-hold-risk"), "risk-flag state does not match archetype")
        need(pay.payment_method == ("Credit Card" if aid == "S1-apply-b" else "ACH"), "payment method does not match archetype")
        ratio = _ratio(pay.sender_name, cust.name)
        if aid == "S1-hold-name":
            need(pay.sender_name.strip().lower() != cust.name.lower(), "sender name is not a variant")
            if not 0.55 <= ratio <= 0.93:
                warns.append(f"difflib name ratio {ratio:.2f} outside 0.55-0.93 band")
        elif ratio < 0.85:
            warns.append(f"difflib name ratio {ratio:.2f} < 0.85")

    elif aid.startswith("S2"):
        cust = cust or (pol_c if pol else None)
        need(cust is not None, "target customer missing")
        if cust is None:
            return fails, warns
        need(cust.status == "active" and not cust.risk_flags, "customer not active/clean")
        need(pay.sender_name.strip().lower() == cust.name.lower(), "sender name is not exact")
        need(not tokens, "policy number present in reference fields")
        active = [p for p in cust.policies if p.status == "active"]
        close = [p for p in active if abs(pay.amount_usd - p.premium_usd) / p.premium_usd <= 0.02]
        if aid in ("S2-apply-single", "S2-apply-single-card"):
            need(len(active) == 1 and len(close) == 1, "needs exactly one active policy matching the amount")
            need(pay.payment_method == ("Credit Card" if aid.endswith("card") else "ACH"), "payment method does not match archetype")
            need(aid != "S2-apply-single-card" or not pay.reference_field_1.strip(), "reference_field_1 should be empty")
        elif aid == "S2-apply-multi-unique":
            others = [p for p in active if p not in close]
            need(len(active) >= 2 and len(close) == 1 and all(abs(pay.amount_usd - p.premium_usd) / p.premium_usd > 0.15 for p in others),
                 "amount must match exactly one of >=2 active policies")
        else:
            need(len(active) >= 2 and len(close) >= 2, "amount must match >=2 active policies")

    elif aid.startswith("S3"):
        need(cust is not None and cust.status == "active" and not cust.risk_flags, "customer not active/clean")
        need(pay.sender_name.strip().lower() == cust.name.lower(), "sender name is not exact")
        ratio = pay.amount_usd / pol.premium_usd
        need(abs(pay.amount_usd - pol.premium_usd * round(ratio)) >= 0.10 * pol.premium_usd or aid == "S3-tier5" and 2.6 <= ratio <= 2.85,
             "amount within 10% of a whole multiple of the premium")
        band = {"S3-tier3-above": (20, 40), "S3-tier3-below": (-40, -20), "S3-tier4": (60, 90), "S3-tier5": (160, 185)}[aid]
        need(band[0] <= variance() <= band[1], f"variance {variance():.1f}% outside {band}")

    elif aid.startswith("S4"):
        need(pay.sender_name.strip().lower() not in {c.name.lower() for c in world.customers}, "sender is a known customer")
        if aid in ("S4-unknown-person", "S4-unknown-company", "S4-bad-policy-ref"):
            need(best_name < 0.70, f"sender too similar to a customer (difflib {best_name:.2f})")
            if best_name >= 0.60:
                warns.append(f"difflib similarity to nearest customer {best_name:.2f}")
        if aid == "S4-bad-policy-ref":
            need(len(tokens) == 1 and tokens[0] not in policies, "policy number must be well-formed but non-existent")
        elif aid == "S4-third-party-hold":
            need(len(tokens) == 1 and tokens[0] in policies, "reference must name an existing policy")
            if tokens and tokens[0] in policies:
                _, p = policies[tokens[0]]
                need(p.status == "active" and abs(pay.amount_usd - p.premium_usd) / p.premium_usd <= 0.10, "policy inactive or amount not within 10%")
            need(bool(THIRD_PARTY_RE.search(pay.sender_name)), "sender does not look like a third party")
        else:
            need(not tokens, "policy number present in reference fields")

    if aid.startswith("S5"):
        need(len(case.prior_payments) == 1, "needs exactly one prior payment")
        if len(case.prior_payments) == 1:
            prior = case.prior_payments[0]
            gap = prior.hours_ago - pay.hours_ago
            need(12 <= gap <= 66 and pay.hours_ago >= 0, f"gap {gap:.1f}h outside 12-66h")
            need(cust is not None and pay.sender_name.strip().lower() == cust.name.lower() and prior.sender_name == pay.sender_name,
                 "sender must be the exact customer name on both payments")
            need(prior.payment_method == pay.payment_method and bool(pay.sender_account.strip()) and bool(prior.sender_account.strip()),
                 "prior/payment must share the method and have non-empty accounts")
            same_refs = (prior.reference_field_1, prior.reference_field_2) == (pay.reference_field_1, pay.reference_field_2)
            same_acct = prior.sender_account == pay.sender_account
            if aid == "S5-diff-ref-not-dup":
                need(not same_refs and same_acct, "references must differ while the account matches")
                prior_tokens = POLICY_RE.findall(f"{prior.reference_field_1} {prior.reference_field_2}")
                other = policies.get(prior_tokens[0]) if len(prior_tokens) == 1 else None
                need(other is not None and other[0] is cust and prior_tokens[0] != case.target_policy_number
                     and abs(other[1].premium_usd - pol.premium_usd) < 0.01 and other[1].status == "active"
                     and other[1].outstanding_balance_usd == 0,
                     "prior must reference a different active policy of the same customer with identical premium and zero balance")
            elif aid == "S5-diff-account-dup":
                need(same_refs and not same_acct, "references must match while the account differs")
            else:
                need(same_refs and same_acct, "prior/payment must share account and references")
            diff_cents = round(abs(pay.amount_usd - prior.amount_usd) * 100)
            want = {"S5-dup-exact": 0, "S5-dup-balance": 0, "S5-dup-tolerance": 100, "S5-near-dup-control": 1000,
                    "S5-diff-ref-not-dup": 0, "S5-diff-account-dup": 0}[aid]
            need(diff_cents == want, f"amount difference {diff_cents}c not {want}c")
            need(abs(variance()) <= 2.0, f"variance {variance():.2f}% > 2%")
            need((pol.outstanding_balance_usd > 0) == (aid == "S5-dup-balance"), "policy balance does not match archetype")
            need(cust is not None and not cust.risk_flags, "customer has risk flags")
    elif case.prior_payments:
        fails.append("unexpected prior payment")
    return fails, warns


# ── Case generation (batched per archetype, with a repair loop) ──────────────

def _case_key(c: GenCase) -> tuple:
    return (c.target_customer_id, c.target_policy_number, c.payment.sender_name, round(c.payment.amount_usd, 2))


def eligible_ids(aid: str, world: World) -> list[str] | None:
    """Customers whose structure can satisfy the archetype, computed by plain arithmetic and given to the LLM as a hint."""
    active = lambda c: [p for p in c.policies if p.status == "active"]  # noqa: E731
    clean = [c for c in world.customers if c.status == "active" and not c.risk_flags]
    identical = lambda c: len(active(c)) >= 2 and len({p.premium_usd for p in active(c)}) < len(active(c))  # noqa: E731
    if aid in ("S4-unknown-person", "S4-unknown-company", "S4-bad-policy-ref"):
        return None
    if aid == "S1-hold-risk":
        pool = [c for c in world.customers if c.status == "active" and c.risk_flags and active(c)]
    elif aid in ("S2-apply-single", "S2-apply-single-card"):
        pool = [c for c in clean if len(active(c)) == 1]
    elif aid == "S2-apply-multi-unique":
        pool = [c for c in clean if len(active(c)) >= 2 and max(p.premium_usd for p in active(c)) > 1.3 * min(p.premium_usd for p in active(c))]
    elif aid == "S2-hold-multi-ambiguous":
        pool = [c for c in clean if identical(c)]
    elif aid == "S5-diff-ref-not-dup":
        pool = [c for c in clean if identical(c) and all(p.outstanding_balance_usd == 0 for p in active(c))]
    elif aid == "S5-dup-balance":
        pool = [c for c in clean if any(p.outstanding_balance_usd > 0 for p in active(c))]
    elif aid == "S5-near-dup-control":
        pool = [c for c in clean if any(p.premium_usd >= 600 and p.outstanding_balance_usd == 0 for p in active(c))]
    elif aid.startswith("S5"):
        pool = [c for c in clean if any(p.outstanding_balance_usd == 0 for p in active(c))]
    else:
        pool = [c for c in clean if active(c)]
    return [c.customer_id for c in pool]


async def generate_archetype(client, sem, aid: str, n: int, world: World, spec: str) -> dict:
    _, scenario, rec, brief = ARCHETYPE[aid]
    valid: list[dict] = []
    seen: set = set()
    stats = {"archetype_id": aid, "requested": n, "generated": 0, "rejected": 0, "calls": 0, "tokens": {"prompt_tokens": 0, "completion_tokens": 0}}
    reject_reasons: list[str] = []
    for _ in range(3):
        need = n - len(valid)
        if need <= 0:
            break
        user = (
            "SPECIFICATION (authoritative decision logic):\n" + spec
            + "\n\nWORLD (customers, policies, history — the system's database):\n" + world.model_dump_json()
            + f"\n\nCreate EXACTLY {need + 1} DIFFERENT test cases, all with archetype_id '{aid}'. Brief: {brief}\n"
              "Make the cases differ from each other: use different customers/policies wherever the WORLD allows, vary amounts (within the "
              "brief's constraints), payment methods where allowed, and the wording of the reference fields. Follow the brief exactly, using "
              "only customers and policies from the WORLD (except where the brief says the payer is not in the world). amount_usd in dollars "
              "with cents; hours_ago is how long before now the payment arrived (payment 1-48; a prior payment is older, i.e. larger). Set "
              "target_customer_id / target_policy_number to the customer and policy the payer intends ('' if none). rationale: one sentence "
              "citing the specification rule that applies. Use '' for absent optional strings."
        )
        ids = eligible_ids(aid, world)
        if ids is not None:
            user += (f"\n\nELIGIBLE customer_ids for this archetype (the payer's customer MUST be one of these): {ids}. Spread the cases "
                     "across them and avoid reusing a customer while unused eligible customers remain.")
        async with sem:
            cases, _, usage = await ask(client, user, Cases, f"cases_{aid}".replace("-", "_"))
        stats["calls"] += 1
        stats["tokens"] = {k: stats["tokens"][k] + usage[k] for k in usage}
        for case in cases.cases:
            stats["generated"] += 1
            if case.archetype_id != aid or _case_key(case) in seen:
                stats["rejected"] += 1
                reject_reasons.append("wrong archetype or duplicate")
                continue
            fails, warns = check_case(case, world)
            if fails:
                stats["rejected"] += 1
                reject_reasons.extend(fails)
                continue
            seen.add(_case_key(case))
            if len(valid) < n:
                valid.append({**case.model_dump(), "expected_scenario": scenario, "expected_recommendation": rec,
                              "variant": "clean", "checks": {"failures": [], "warnings": warns}})
    for i, v in enumerate(valid, 1):
        v["case_id"] = f"{aid}-{i:02d}"
    stats["valid"] = len(valid)
    stats["reject_reasons"] = dict(sorted(((r, reject_reasons.count(r)) for r in set(reject_reasons)), key=lambda kv: -kv[1])[:5])
    return {"cases": valid, "stats": stats}


# ── Deterministic noise twins ────────────────────────────────────────────────

REF_FORMATS = ["pol {d}", "POL{d}", "pol-{d}", "Policy #{d}", "policy no. {d}", "POL {d}", "Pol.{d}"]
MEMO_WORDS = ["pmt for", "prem", "ins.", "payment", "ref", "renewal", "acct pmt"]
PLAIN_MEMOS = ["ins pymt", "premium", "monthly", "payment - insurance", "ref 4471", "PREMIUM PMT"]


def noisy_ref(text: str, rng: random.Random) -> str:
    match = POLICY_RE.search(text)
    if not match:
        return rng.choice(PLAIN_MEMOS)
    core = rng.choice(REF_FORMATS).format(d=match.group(0)[4:])
    rest = POLICY_RE.sub("", text).strip(" -|:")
    memo = rng.choice(MEMO_WORDS)
    return rng.choice([f"{memo} {core}", f"{core} {rest}".strip(), f"{core} - {memo}"]).strip()


def noisy_case(name: str, rng: random.Random) -> str:
    return rng.choice([name.upper(), name.lower(), name.replace(" ", "  ") + " .", name + ","])


def typo(name: str, rng: random.Random) -> str:
    words = name.split()
    candidates = [i for i, w in enumerate(words) if len(w) >= 4] or list(range(len(words)))
    for _ in range(20):
        w = rng.choice(candidates)
        word = words[w]
        i = rng.randrange(1, max(2, len(word) - 1))
        op = rng.choice(["swap", "drop", "dup", "sub"])
        if op == "swap" and i + 1 < len(word):
            new = word[:i] + word[i + 1] + word[i] + word[i + 2:]
        elif op == "drop":
            new = word[:i] + word[i + 1:]
        elif op == "dup":
            new = word[:i] + word[i] + word[i:]
        else:
            new = word[:i] + rng.choice("aeiou") + word[i + 1:]
        if new != word:
            return " ".join(words[:w] + [new] + words[w + 1:])
    return name


TWIN_QUOTA = {"ref_noise": 2, "name_case": 1, "name_typo": 1}
TYPO_ARCHETYPES = {"S1-apply-b", "S2-apply-single", "S2-apply-single-card"}


def make_twins(bases: list[dict], world: World, rng: random.Random) -> list[dict]:
    exact_names = {c.name.lower() for c in world.customers}
    twins: list[dict] = []
    by_arch: dict[str, list[dict]] = {}
    for b in bases:
        by_arch.setdefault(b["archetype_id"], []).append(b)

    def build(base: dict, tag: str, edit) -> dict:
        twin = json.loads(json.dumps(base))
        for p in [twin["payment"], *twin["prior_payments"]]:
            edit(p)
        twin.update({"case_id": f"{base['case_id']}~{tag}", "variant": tag, "base_case": base["case_id"],
                     "noise_detail": {"before": {k: base["payment"][k] for k in ("sender_name", "reference_field_1", "reference_field_2")},
                                      "after": {k: twin["payment"][k] for k in ("sender_name", "reference_field_1", "reference_field_2")}}})
        return twin

    for aid, group in by_arch.items():
        scenario = ARCHETYPE[aid][1]
        pools = {
            "ref_noise": [b for b in group if b["payment"]["reference_field_1"].strip()],
            "name_case": [b for b in group if scenario != 4 and b["payment"]["sender_name"].lower() in exact_names],
            "name_typo": [b for b in group if aid in TYPO_ARCHETYPES and b["payment"]["sender_name"].lower() in exact_names],
        }
        for tag, quota in TWIN_QUOTA.items():
            for base in rng.sample(pools[tag], min(quota, len(pools[tag]))):
                if tag == "ref_noise":
                    cache: dict[str, str] = {}  # identical originals stay identical, distinct ones stay distinct
                    ref2_case = rng.choice([str.upper, str.lower, str])

                    def edit(p, _cache=cache, _case=ref2_case):
                        original = p["reference_field_1"]
                        if original not in _cache:
                            _cache[original] = noisy_ref(original, rng)
                        p["reference_field_1"] = _cache[original]
                        p["reference_field_2"] = _case(p["reference_field_2"])
                elif tag == "name_case":
                    name = noisy_case(base["payment"]["sender_name"], rng)

                    def edit(p, _name=name):
                        p["sender_name"] = _name
                else:
                    name = typo(base["payment"]["sender_name"], rng)

                    def edit(p, _name=name):
                        p["sender_name"] = _name
                twin = build(base, tag, edit)
                if tag == "name_typo":
                    twin["accept"] = ["apply", "hold"]
                token = POLICY_RE.search(base["payment"]["reference_field_1"])
                if tag == "ref_noise" and token and token.group(0)[4:] not in twin["payment"]["reference_field_1"]:
                    continue  # ground-truth policy no longer recoverable — drop the twin
                if twin["payment"]["sender_name"] == base["payment"]["sender_name"] and tag != "ref_noise":
                    continue
                twins.append(twin)
    return twins


# ── Main ─────────────────────────────────────────────────────────────────────

async def main(args) -> None:
    client = openai.AsyncOpenAI(api_key=settings.OPENROUTER_API_KEY, base_url=OPENROUTER_BASE)
    started = time.monotonic()
    chunks = CHUNKS_FULL if args.full else 1
    per_archetype = args.cases_per_archetype or (6 if args.full else 1)
    tokens = {"prompt_tokens": 0, "completion_tokens": 0}

    kinds = ["regular"] * chunks + ["ident"]
    print(f"Stage 1: generating world ({chunks} chunk(s) of {CHUNK['customers']} customers + {IDENT_CHUNK} identical-premium customers)…")
    world = World(customers=[])
    for k, kind in enumerate(kinds):
        for attempt in range(1, 4):
            part, mode, usage = await ask(client, world_requirements(CHUNK, k, world.customers, kind), World, "world")
            tokens = {key: tokens[key] + usage[key] for key in tokens}
            part.customers = part.customers[:CHUNK["customers"] if kind == "regular" else IDENT_CHUNK]  # the model sometimes overshoots
            problems = (world_problems(part, CHUNK) if kind == "regular" else ident_problems(part)) + cross_problems(world.customers, part.customers)
            print(f"  chunk {k + 1} ({kind}) attempt {attempt} ({mode}): {len(part.customers)} customers, problems: {problems or 'none'}")
            if not problems:
                world.customers.extend(part.customers)
                break
        else:
            sys.exit(f"world chunk {k + 1} failed its structural checks after 3 attempts")
    total = {key: value * chunks for key, value in CHUNK.items()}
    total.update(customers=CHUNK["customers"] * chunks + IDENT_CHUNK, ident=IDENT_CHUNK)
    print(f"  merged world: {len(world.customers)} customers, problems: {world_problems(world, total, unique_surnames=False) or 'none'}")

    print(f"Stage 2: generating {per_archetype} case(s) for each of {len(ARCHETYPES)} archetypes…")
    spec = (REPO / "docs/Final_Scenario_Definitions.md").read_text()
    sem = asyncio.Semaphore(CONCURRENCY)
    outcomes = await asyncio.gather(*(generate_archetype(client, sem, a[0], per_archetype, world, spec) for a in ARCHETYPES),
                                    return_exceptions=True)
    bases, stats = [], []
    for aid, out in zip((a[0] for a in ARCHETYPES), outcomes):
        if isinstance(out, Exception):
            print(f"  ! {aid}: generation failed ({type(out).__name__}: {str(out)[:100]})")
            stats.append({"archetype_id": aid, "requested": per_archetype, "valid": 0, "error": str(out)[:200]})
            continue
        bases.extend(out["cases"])
        stats.append(out["stats"])
        s = out["stats"]
        tokens = {k: tokens[k] + s["tokens"][k] for k in tokens}
        extra = f"  rejected {s['rejected']}/{s['generated']}: {s['reject_reasons']}" if s["rejected"] else ""
        print(f"  {aid:<26} {s['valid']}/{per_archetype} valid{extra}")

    twins = make_twins(bases, world, random.Random(NOISE_SEED)) if args.full else []
    cases = bases + twins
    generated = sum(s.get("generated", 0) for s in stats)
    rejected = sum(s.get("rejected", 0) for s in stats)
    print(f"\nBase cases: {len(bases)} valid ({rejected}/{generated} generated cases failed independent checks)")
    for tag in TWIN_QUOTA:
        print(f"  {tag:<10} twins: {sum(1 for t in twins if t['variant'] == tag)}")
    print(f"Total cases: {len(cases)}")

    out = args.out or Path(__file__).parent / "data" / ("full.json" if args.full else "pilot.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "meta": {"model": MODEL, "full": args.full, "seconds": round(time.monotonic() - started, 1), "tokens": tokens,
                 "world_customers": len(world.customers), "base_cases": len(bases), "twin_cases": len(twins),
                 "generated_cases": generated, "rejected_cases": rejected, "noise_seed": NOISE_SEED, "archetype_stats": stats},
        "world": world.model_dump(), "cases": cases,
    }, indent=2))
    print(f"\nWrote {out}  ({tokens['prompt_tokens']} prompt / {tokens['completion_tokens']} completion tokens, "
          f"{time.monotonic() - started:.0f}s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="30-customer world, 6 cases per archetype, plus noise twins")
    parser.add_argument("--cases-per-archetype", type=int, default=0)
    parser.add_argument("--out", type=Path, default=None)
    asyncio.run(main(parser.parse_args()))
