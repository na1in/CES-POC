"""
Adds up the LLM spend recorded in data/abl_*.json (every call site, plus the AI-decider arms, all passes) at the
OpenRouter list price for google/gemini-2.5-flash, verified 2026-09-26 from https://openrouter.ai/api/v1/models:
$0.30 per million input tokens, $2.50 per million output tokens (reasoning tokens are billed as output and are already
part of completion_tokens).

Usage: python scripts/eval/spend.py [--max 11]   (exit status 1 when the total exceeds --max, so a runner can stop)
"""
import argparse
import json
import sys
from pathlib import Path

PRICE_IN, PRICE_OUT = 0.30 / 1e6, 2.50 / 1e6
DATA = Path(__file__).parent / "data"


def cost(prompt_tokens: int, completion_tokens: int) -> float:
    return prompt_tokens * PRICE_IN + completion_tokens * PRICE_OUT


def file_spend(path: Path) -> float:
    d = json.loads(path.read_text())
    if not isinstance(d, dict):  # not a run_eval result file
        return 0.0
    total = sum(cost(u["prompt_tokens"], u["completion_tokens"]) for u in (d.get("usage_all_passes") or {}).values())
    ai = d.get("ai_decider_stats")
    if ai:
        total += cost(ai["prompt_tokens"], ai["completion_tokens"])
    return total


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=float, default=None)
    args = ap.parse_args()
    files = sorted(DATA.glob("abl_*.json"))
    per = {f.name: file_spend(f) for f in files}
    total = sum(per.values())
    print(f"LLM spend recorded in {len(files)} result files: ${total:.2f}" + (f" (limit ${args.max:.2f})" if args.max else ""))
    if "-v" in sys.argv or not args.max:
        for name, v in sorted(per.items(), key=lambda t: -t[1])[:8]:
            print(f"  ${v:6.3f}  {name}")
    sys.exit(1 if args.max is not None and total > args.max else 0)
