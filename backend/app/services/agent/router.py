import logging
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLDS = {
    "name_match_hold": "75",
    "amount_tolerance_auto": "2",
}


@dataclass
class RoutingResult:
    scenario: int        # 1–5
    decision_path: str
    thresholds: dict


async def load_thresholds(db: AsyncSession) -> dict:
    result = await db.execute(
        text("SELECT parameter_name, parameter_value FROM configuration_thresholds")
    )
    return {row.parameter_name: row.parameter_value for row in result}


def _variance_tier(variance_pct: float) -> int:
    """Classify absolute variance into tiers 1–5."""
    if variance_pct <= 2:
        return 1
    elif variance_pct <= 15:
        return 2
    elif variance_pct <= 50:
        return 3
    elif variance_pct <= 100:
        return 4
    return 5


def _route(signals: dict, payment: dict, thresholds: dict) -> tuple[int, str]:
    """
    Deterministic scenario routing — no I/O.

    Priority order (highest to lowest):
      5 → duplicate detected
      4 → name similarity below hold threshold
      3 → amount variance above auto-apply tolerance
      1 → policy reference present
      2 → customer match, no policy reference
    """
    name_hold = float(thresholds.get("name_match_hold", DEFAULT_THRESHOLDS["name_match_hold"]))
    amount_tol = float(thresholds.get("amount_tolerance_auto", DEFAULT_THRESHOLDS["amount_tolerance_auto"]))

    # Scenario 5 runs first on every payment
    if signals.get("is_duplicate_match"):
        return 5, "scenario_5_duplicate"

    name_score = float(signals.get("name_similarity_score", 0))

    # Scenario 4 — no matching customer
    if name_score < name_hold:
        return 4, "scenario_4_no_customer_match"

    # Scenario 3 — amount variance exceeds auto-apply tolerance
    variance = abs(float(signals.get("amount_variance_pct") or 0))
    if variance > amount_tol:
        tier = _variance_tier(variance)
        return 3, f"scenario_3_tier_{tier}"

    # Scenario 1 — explicit policy reference provided
    if payment.get("extracted_policy_number"):
        return 1, "scenario_1_strong_policy_match"

    # Scenario 2 — customer match without policy reference
    return 2, "scenario_2_customer_match_no_policy"


async def route_scenario(
    payment: dict,
    signals: dict,
    db: AsyncSession,
) -> RoutingResult:
    thresholds = await load_thresholds(db)
    scenario, decision_path = _route(signals, payment, thresholds)
    logger.info(
        "payment=%s routed to scenario=%d path=%s",
        payment.get("payment_id"),
        scenario,
        decision_path,
    )
    return RoutingResult(scenario=scenario, decision_path=decision_path, thresholds=thresholds)
