"""
Experiment arm: let an LLM make the final APPLY / HOLD / ESCALATE decision.

Used by run_eval.py --llm ai-rules | ai-open. Everything before the decision (regex reference parse, deterministic
name score, signal engine, scenario routing) is unchanged; only the scenario handlers are replaced, so the
recommendation comes from the model instead of from the if/else code. Production code is not modified.

  ai-rules  the full authoritative spec (docs/Final_Scenario_Definitions.md, verbatim), the configured thresholds,
            the routed scenario, and the computed signals. Tests: can an LLM apply the rulebook faithfully?
  ai-open   business goal and the facts only: no rulebook, no thresholds, no scenario. Tests: the LLM's own judgement.
  ai-tight  like ai-rules, but only the routed scenario's section of the spec (plus the configuration block), and
            the model must evaluate each Decision Logic condition (value, true/false) and name the branch it took
            before it gives the recommendation. Built from the spec's structure alone; no rule is written for a
            particular kind of payment.

Note for reading results: the harness labels are derived from the same spec, so neither arm can score above "matches
the spec". The comparison shows whether the LLM reproduces the rules, at what cost and consistency; it cannot show
that the LLM's judgement is better than the rules.
"""
import asyncio
import json
import time
from pathlib import Path

import openai

from app.config import settings

MODEL = "google/gemini-2.5-flash"  # the model the pipeline already uses
SPEC = (Path(__file__).resolve().parents[3] / "docs" / "Final_Scenario_Definitions.md").read_text()

STATS = {"calls": 0, "retries": 0, "failures": 0, "seconds": 0.0, "prompt_tokens": 0, "completion_tokens": 0}

SCHEMA = {
    "name": "payment_decision",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {  # reasoning first, so the model works through the case before committing to a decision
            "reasoning": {"type": "string"},
            "recommendation": {"type": "string", "enum": ["APPLY", "HOLD", "ESCALATE"]},
            "confidence": {"type": "integer"},
        },
        "required": ["reasoning", "recommendation", "confidence"],
        "additionalProperties": False,
    },
}

RULES_SYSTEM = f"""You are the decision component of an insurance payment-exception system. An unidentified or \
mismatched payment has been received. Decide APPLY, HOLD or ESCALATE by applying the authoritative specification \
below to the case file you are given. Follow the specification's decision logic and thresholds exactly.

Notes:
- Every payment is reviewed by a human before anything is applied; "APPLY" means "recommend applying".
- The case file's "current_configuration" holds the live threshold values; use them where the specification names \
a configurable threshold.
- Amounts in the case file are in cents unless a field name says usd.
- Use only the facts in the case file. Do not invent data.

=== AUTHORITATIVE SPECIFICATION ===
{SPEC}
=== END SPECIFICATION ===

Reply with JSON: reasoning (2-4 sentences citing the rule and facts you relied on), recommendation, confidence (0-100)."""

OPEN_SYSTEM = """You are a senior payment-exception analyst at an insurance company. A payment arrived that could not be \
matched automatically. From the case file, decide what should happen:

- APPLY: you are confident this is the right customer and policy and the amount is right, so a human reviewer \
should simply approve applying it as-is.
- HOLD: plausible, but a human analyst needs to review or clarify something before it can be applied.
- ESCALATE: it cannot be resolved without investigation (unknown or unverifiable sender, an unjustified duplicate, \
a serious discrepancy, or a fraud concern).

Every decision is reviewed by a human. Wrongly recommending APPLY is the costliest mistake. Amounts are in cents \
unless a field name says usd. Use only the facts in the case file; do not invent data.

Reply with JSON: reasoning (2-4 sentences), recommendation, confidence (0-100)."""

TIGHT_SCHEMA = {
    "name": "payment_decision_checked",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {  # conditions first, then the branch, then the decision
            "checks": {"type": "array", "items": {
                "type": "object",
                "properties": {"condition": {"type": "string"}, "case_value": {"type": "string"}, "holds": {"type": "boolean"}},
                "required": ["condition", "case_value", "holds"],
                "additionalProperties": False,
            }},
            "branch_taken": {"type": "string"},
            "recommendation": {"type": "string", "enum": ["APPLY", "HOLD", "ESCALATE"]},
            "confidence": {"type": "integer"},
        },
        "required": ["checks", "branch_taken", "recommendation", "confidence"],
        "additionalProperties": False,
    },
}

TIGHT_SYSTEM = """You are the decision component of an insurance payment-exception system. A payment has been routed \
to Scenario {n}. Decide APPLY, HOLD or ESCALATE by applying that scenario's specification to the case file.

How to decide:
1. Read the Decision Logic of the scenario below. List every condition it tests that is relevant to this case and \
evaluate each against the case file: the case value, then whether the condition holds.
2. Walk the Decision Logic from top to bottom and take the first branch whose conditions all hold. Name that branch.
3. The recommendation is that branch's outcome.

Rules:
- The Decision Logic is the only source of conditions. The description, "Signals to Compute" and the examples explain \
the data and show the format; do not turn them into extra requirements, and do not add conditions from other \
scenarios or from your own caution.
- Every payment is reviewed by a human before anything is applied; "APPLY with approval required" means the \
recommendation is APPLY.
- Where the specification names a configurable threshold, use the value in the case file's current_configuration.
- Amounts in the case file are in cents unless a field name says usd. Use only the facts in the case file.

=== CONFIGURATION PARAMETERS ===
{config}

=== SCENARIO {n} SPECIFICATION ===
{section}"""

_tight_cache: dict[int, str] = {}


def _spec_sections() -> dict[str, str]:
    sections: dict[str, str] = {}
    current, buf = None, []
    for line in SPEC.splitlines():
        if line.startswith("## "):
            if current:
                sections[current] = "\n".join(buf).strip()
            current, buf = line[3:].strip(), [line]
        elif current:
            buf.append(line)
    if current:
        sections[current] = "\n".join(buf).strip()
    return sections


def _tight_system(scenario: int) -> str:
    if scenario not in _tight_cache:
        sections = _spec_sections()
        section = next(v for k, v in sections.items() if k.startswith(f"Scenario {scenario}:"))
        _tight_cache[scenario] = TIGHT_SYSTEM.format(n=scenario, config=sections["Configuration Parameters"], section=section)
    return _tight_cache[scenario]


_client = None


def _get_client() -> openai.AsyncOpenAI:
    global _client
    if _client is None:
        _client = openai.AsyncOpenAI(api_key=settings.OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
    return _client


def _case_file(mode: str, scenario: int, payment: dict, signals: dict, context: dict, thresholds: dict) -> dict:
    pay = {k: payment.get(k) for k in ("sender_name", "amount", "payment_method", "sender_account", "beneficiary_name",
                                       "reference_field_1", "reference_field_2", "payment_date", "extracted_policy_number")}
    pay["amount_usd"] = round((payment.get("amount") or 0) / 100, 2)
    case = {
        "payment": pay,
        "matched_customer": {"name": context.get("customer_name"), "customer_id": context.get("customer_id"),
                             "policy_number": context.get("policy_number"),
                             "active_policy_count": context.get("active_policy_count"),
                             "active_policies": context.get("active_policies")},
        "computed_signals": {k: v for k, v in signals.items() if k not in ("payment_id", "computed_at")},
    }
    if mode in ("ai-rules", "ai-tight"):
        case["routed_scenario"] = scenario
        case["current_configuration"] = thresholds
    return json.loads(json.dumps(case, default=str))


async def decide(mode: str, scenario: int, payment: dict, signals: dict, context: dict, thresholds: dict) -> dict:
    if mode == "ai-tight":
        system, schema = _tight_system(scenario), TIGHT_SCHEMA
    else:
        system, schema = (RULES_SYSTEM if mode == "ai-rules" else OPEN_SYSTEM), SCHEMA
    user = json.dumps(_case_file(mode, scenario, payment, signals, context, thresholds), indent=1)
    last_error = None
    for attempt in range(2):
        started = time.monotonic()
        try:
            response = await _get_client().chat.completions.create(
                model=MODEL, temperature=0, max_tokens=800, timeout=60,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                response_format={"type": "json_schema", "json_schema": schema},
                extra_body={"provider": {"require_parameters": True}},
            )
            STATS["calls"] += 1
            STATS["seconds"] += time.monotonic() - started
            if response.usage:
                STATS["prompt_tokens"] += response.usage.prompt_tokens or 0
                STATS["completion_tokens"] += response.usage.completion_tokens or 0
            out = json.loads(response.choices[0].message.content)
            if mode == "ai-tight":  # fold the checklist into the single reasoning string the pipeline stores
                checks = "; ".join(f"{c['condition']} [{c['case_value']}] -> {'yes' if c['holds'] else 'no'}" for c in out["checks"])
                out = {"recommendation": out["recommendation"], "confidence": out["confidence"],
                       "reasoning": f"{out['branch_taken']} | Checks: {checks}"}
            if out["recommendation"] not in ("APPLY", "HOLD", "ESCALATE"):
                raise ValueError(f"bad recommendation {out['recommendation']!r}")
            return out
        except Exception as exc:  # noqa: BLE001 - retried once, then counted as a failed decision
            last_error = exc
            STATS["retries"] += 1
            await asyncio.sleep(1)
    STATS["failures"] += 1
    return {"reasoning": f"AI decision failed: {last_error}", "recommendation": "ESCALATE", "confidence": 0, "_failed": True}


def make_handler(mode: str, scenario: int):
    async def handler(payment: dict, signals: dict, context: dict, thresholds: dict) -> dict:
        out = await decide(mode, scenario, payment, signals, context, thresholds)
        failed = out.get("_failed", False)
        return {
            "recommendation": out["recommendation"],
            "confidence_score": float(out["confidence"]),
            "scenario_route": scenario,  # scenario routing stays in code; only the recommendation is the model's
            "decision_path": "ai_decision_failed" if failed else f"{mode.replace('-', '_')}_scenario_{scenario}",
            "requires_human_approval": True,
            "approval_reason": None,
            "reasoning": [out["reasoning"]],
            "suggested_action": None,
            "matched_policy_id": context.get("policy_id"),
            "matched_customer_id": context.get("customer_id"),
        }
    return handler


def install(mode: str) -> None:
    from app.services import pipeline

    for n in range(1, 6):
        pipeline._SCENARIO_HANDLERS[n] = make_handler(mode, n)
