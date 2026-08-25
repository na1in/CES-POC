#!/bin/bash
# CES Backend Demo — run from backend/ with server already running on :8000
# Each command shows a different scenario through the signal engine

BASE="http://localhost:8000"
SEP="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# DB connection for demo_signals — read from backend/.env so this works
# whether Postgres is on the docker-compose default port (5432) or the
# local override port (5433, see docker-compose.override.yml).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_URL_RAW=$(grep -E '^DATABASE_URL=' "$SCRIPT_DIR/.env" 2>/dev/null | cut -d '=' -f2-)
DB_URL=${DB_URL_RAW/postgresql+asyncpg:/postgresql:}
DB_URL=${DB_URL:-postgresql://ces_user:ces_password@localhost:5432/ces}

# ─────────────────────────────────────────────────────────────────
# 0. Health check
# ─────────────────────────────────────────────────────────────────
demo_health() {
  echo -e "\n$SEP"
  echo "0. HEALTH CHECK"
  echo "$SEP"
  curl -s $BASE/health | python3 -m json.tool
}

# ─────────────────────────────────────────────────────────────────
# 1. Scenario 1 — Strong Policy Match (exact name + policy ref)
#    Customer: Robert Johnson (CUST-0001), Policy: POL-00001
#    Premium: $1,500.00 | Payment: $1,500.00 (0% variance)
# ─────────────────────────────────────────────────────────────────
demo_scenario1() {
  echo -e "\n$SEP"
  echo "1. SCENARIO 1 — Strong Policy Match"
  echo "   Robert Johnson pays exact premium for POL-00001"
  echo "   Expected signals: name ~100%, policy confidence high, variance 0%"
  echo "$SEP"
  curl -s -X POST $BASE/api/payments/ingest \
    -H "Content-Type: application/json" \
    -d '{
      "sender_name": "Robert Johnson",
      "sender_account": "ACC-10001",
      "amount": 150000,
      "payment_method": "ACH",
      "reference_field_1": "Payment for policy POL-00001 - monthly premium",
      "payment_date": "2026-04-27T10:00:00Z"
    }' | python3 -m json.tool
}

# ─────────────────────────────────────────────────────────────────
# 2. Scenario 1 — Gray-Zone Name (Haiku invoked)
#    "Rob Johnson" vs "Robert Johnson" — hits 70–92% gray zone
# ─────────────────────────────────────────────────────────────────
demo_gray_zone() {
  echo -e "\n$SEP"
  echo "2. GRAY-ZONE NAME MATCHING — Claude Haiku invoked"
  echo "   'Rob Johnson' vs 'Robert Johnson' — deterministic hits gray zone"
  echo "   Expected: llm_score returned, final = max(deterministic, llm)"
  echo "$SEP"
  curl -s -X POST $BASE/api/payments/ingest \
    -H "Content-Type: application/json" \
    -d '{
      "sender_name": "Rob Johnson",
      "sender_account": "ACC-10001",
      "amount": 150000,
      "payment_method": "ACH",
      "reference_field_1": "Monthly insurance premium POL-00001",
      "payment_date": "2026-04-27T10:05:00Z"
    }' | python3 -m json.tool
}

# ─────────────────────────────────────────────────────────────────
# 3. Scenario 3 — High Amount Variance
#    Robert Johnson pays $1,800 vs $1,500 premium (20% over)
# ─────────────────────────────────────────────────────────────────
demo_variance() {
  echo -e "\n$SEP"
  echo "3. SCENARIO 3 — High Amount Variance"
  echo "   Robert Johnson pays \$1,800 vs \$1,500 premium (20% overpayment)"
  echo "   Expected: amount_variance_pct=20%, is_overpayment=true"
  echo "$SEP"
  curl -s -X POST $BASE/api/payments/ingest \
    -H "Content-Type: application/json" \
    -d '{
      "sender_name": "Robert Johnson",
      "sender_account": "ACC-10001",
      "amount": 180000,
      "payment_method": "ACH",
      "reference_field_1": "POL-00001 premium payment",
      "payment_date": "2026-04-27T10:10:00Z"
    }' | python3 -m json.tool
}

# ─────────────────────────────────────────────────────────────────
# 4. Scenario 3 — Multi-Period Payment
#    James Wilson pays 3× premium ($6,000) for POL-00004 ($2,000/mo)
# ─────────────────────────────────────────────────────────────────
demo_multi_period() {
  echo -e "\n$SEP"
  echo "4. MULTI-PERIOD PAYMENT"
  echo "   James Wilson pays \$6,000 = 3× \$2,000 monthly premium"
  echo "   Expected: is_multi_period=true, estimated_periods=3"
  echo "$SEP"
  curl -s -X POST $BASE/api/payments/ingest \
    -H "Content-Type: application/json" \
    -d '{
      "sender_name": "James Wilson",
      "sender_account": "ACC-10003",
      "amount": 600000,
      "payment_method": "Check",
      "reference_field_1": "Quarterly payment for policy POL-00004",
      "payment_date": "2026-04-27T10:15:00Z"
    }' | python3 -m json.tool
}

# ─────────────────────────────────────────────────────────────────
# 5. Scenario 5 — Duplicate Detection
#    Same sender, method, amount within $2, within 72hrs
#    Run demo_scenario1 first, then this — will flag as duplicate
# ─────────────────────────────────────────────────────────────────
demo_duplicate() {
  echo -e "\n$SEP"
  echo "5. SCENARIO 5 — Duplicate Detection"
  echo "   Same payment as #1 resubmitted — should flag as duplicate"
  echo "   Expected: duplicate_detected=true, time_between_payments<72hrs"
  echo "$SEP"
  curl -s -X POST $BASE/api/payments/ingest \
    -H "Content-Type: application/json" \
    -d '{
      "sender_name": "Robert Johnson",
      "sender_account": "ACC-10001",
      "amount": 150100,
      "payment_method": "ACH",
      "reference_field_1": "Payment for policy POL-00001 - monthly premium",
      "payment_date": "2026-04-27T11:00:00Z"
    }' | python3 -m json.tool
}

# ─────────────────────────────────────────────────────────────────
# 6. Scenario 4 — No Match + Risk Flag
#    James Wilson (CUST-0003) has fraud_history flag — active risk flag
# ─────────────────────────────────────────────────────────────────
demo_risk_flags() {
  echo -e "\n$SEP"
  echo "6. RISK FLAGS — Customer with fraud_history"
  echo "   James Wilson (CUST-0003) has active fraud_history flag"
  echo "   Expected: has_risk_flags=true, risk_flag_types=[fraud_history]"
  echo "$SEP"
  curl -s -X POST $BASE/api/payments/ingest \
    -H "Content-Type: application/json" \
    -d '{
      "sender_name": "James Wilson",
      "sender_account": "ACC-10003",
      "amount": 200000,
      "payment_method": "Wire",
      "reference_field_1": "POL-00004 monthly payment",
      "payment_date": "2026-04-27T10:20:00Z"
    }' | python3 -m json.tool
}

# ─────────────────────────────────────────────────────────────────
# 7. Query signals for a payment (replace PMT-XXX with real ID)
# ─────────────────────────────────────────────────────────────────
demo_signals() {
  local PMT_ID=${1:-"PMT-001"}
  echo -e "\n$SEP"
  echo "7. VIEW COMPUTED SIGNALS for $PMT_ID"
  echo "$SEP"
  PY="$SCRIPT_DIR/venv/bin/python3"
  [ -x "$PY" ] || PY="python3"
  "$PY" -c "
import asyncio, asyncpg, json
from datetime import datetime

def default(o):
    if isinstance(o, datetime): return o.isoformat()
    raise TypeError

async def run():
    conn = await asyncpg.connect('$DB_URL')
    row = await conn.fetchrow('SELECT * FROM payment_signals WHERE payment_id = \$1', '$PMT_ID')
    if row:
        print(json.dumps(dict(row), indent=2, default=default))
    else:
        print('No signals found for $PMT_ID')
    await conn.close()

asyncio.run(run())
"
}

# ─────────────────────────────────────────────────────────────────
# Run all demos
# ─────────────────────────────────────────────────────────────────
case "${1:-all}" in
  health)       demo_health ;;
  scenario1)    demo_scenario1 ;;
  grayzone)     demo_gray_zone ;;
  variance)     demo_variance ;;
  multiperiod)  demo_multi_period ;;
  duplicate)    demo_scenario1 && sleep 1 && demo_duplicate ;;
  riskflags)    demo_risk_flags ;;
  signals)      demo_signals "$2" ;;
  all)
    demo_health
    demo_scenario1
    demo_gray_zone
    demo_variance
    demo_multi_period
    demo_risk_flags
    demo_scenario1 && sleep 1 && demo_duplicate
    ;;
esac
