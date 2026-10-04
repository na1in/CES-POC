"""
Renders the live "audit report" HTML page for a payment — the same data GET /api/payments/{id} returns
(payment, signals, recommendation, audit trail, annotations), formatted to match the PayWise frontend's
own design tokens (frontend/src/app/globals.css) so the report reads as part of the app, not a separate
document brand.

Generated fresh on every request from the current DB state — analyst notes and any later human action
(approve/escalate/override/return) show up the next time the report is opened, with no separate
regeneration step. This is what the "View audit report" button on the Payment Detail page calls.
"""
import html
from datetime import datetime, timezone

_SCENARIO_LABELS = {
    "scenario_1": "1 · Strong Policy Match",
    "scenario_2": "2 · Customer Match, No Policy",
    "scenario_3": "3 · High Amount Variance",
    "scenario_4": "4 · No Matching Customer",
    "scenario_5": "5 · Duplicate Payment",
}

_STATUS_BADGE = {
    "received": "neutral", "processing": "neutral",
    "held": "hold", "applied": "apply", "escalated": "escalate",
    "pending_sender_response": "info", "returned": "neutral", "processing_failed": "escalate",
}

_ANNOTATION_LABELS = {
    "case_note": "Case note", "override_reason": "Override reason",
    "contact_record": "Contact record", "investigation_note": "Investigation note",
}

_ACTION_LABELS = {
    "received": "Payment received", "signals_computed": "Analysis complete",
    "recommendation_made": "Recommendation made", "approved": "Approved", "applied": "Payment applied",
    "escalated": "Escalated", "held": "Payment held", "overridden": "System Recommendation Overridden",
    "returned": "Returned to sender", "policy_attached": "Policy attached",
    "document_uploaded": "Document uploaded", "annotated": "Note added",
}


def esc(s) -> str:
    return html.escape(str(s), quote=False)


def _money(cents) -> str:
    if cents is None:
        return "—"
    return f"${cents / 100:,.2f}"


def _pct(v, decimals=0) -> str:
    if v is None:
        return "—"
    return f"{v:.{decimals}f}"


def _badge(label: str, kind: str) -> str:
    return f'<span class="pw-badge b-{kind}">{esc(label)}</span>'


def _humanize_path(path) -> str:
    if not isinstance(path, str):
        return ""
    import re
    out = re.sub(r"^scenario_\d+_", "", path).replace("_", " ")
    out = re.sub(r"^auto apply$", "apply recommended", out)
    return re.sub(r"(?<=[a-z])(\d)", r" \1", out)


def _actor_label(actor: str, action_type: str) -> str:
    """Mirrors auditActor() in frontend/src/app/payments/[id]/page.tsx so the report and the live
    Audit Trail card show the same actor name for the same event."""
    if actor == "system":
        return "System" if action_type in ("signals_computed", "recommendation_made") else "System"
    return actor


def _fmt_time(ts) -> str:
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return ts.strftime("%b %d, %Y at %I:%M %p").replace(" 0", " ")


def _fmt_clock(ts) -> str:
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return ts.strftime("%H:%M")


# ── Activity log formatting — mirrors formatAuditDetail() in frontend/src/app/payments/[id]/page.tsx,
# so the report and the live Audit Trail card describe the same event the same way. ─────────────────
def _format_detail(action_type: str, d: dict | None, system_rec: str | None = None) -> str:
    if not d:
        return ""
    try:
        if action_type == "received":
            method = str(d.get("payment_method", "")).upper()
            policy = d.get("extracted_policy_number")
            tail = f"Reference matched to policy {policy}." if policy else "No policy number found in the payment reference."
            return f"{_money(d.get('amount'))} via {method} from {d.get('sender_name')}. {tail}"
        if action_type == "signals_computed":
            return (
                f"Name match {_pct(d.get('name_similarity_score'))}% · "
                f"policy match {_pct(d.get('policy_match_confidence'))}% · "
                f"customer match {_pct(d.get('customer_match_confidence'))}%. "
                f"{'Risk flags present.' if d.get('has_risk_flags') else 'No risk flags.'} "
                f"{'Flagged as a possible duplicate.' if d.get('is_duplicate_match') else 'Not a duplicate.'}"
            )
        if action_type == "recommendation_made":
            rec = str(d.get("recommendation", "")).upper()
            scenario = _SCENARIO_LABELS.get(d.get("scenario_route"), d.get("scenario_route") or "—")
            path = _humanize_path(d.get("decision_path"))
            conf = f" at {_pct(d.get('confidence_score'))}% confidence" if d.get("confidence_score") is not None else ""
            tail = " Auto-applied, no human review required." if d.get("auto_applied") else " Held for human review."
            return f"Recommended {rec}{conf} — {scenario}" + (f" ({path})." if path else ".") + tail
        if action_type == "approved":
            return f"Approved against policy {d['policy_id']}." if d.get("policy_id") else "Approved."
        if action_type == "applied":
            return "Applied after an analyst override." if d.get("via") == "human_override" else "Applied after analyst approval — ledger updated."
        if action_type == "escalated":
            if d.get("action") == "marked_pending_outreach":
                return "Marked as awaiting a response from the sender."
            if d.get("via") == "human_override":
                return "Escalated after an analyst override."
            if d.get("via") == "analyst_rejection":
                # "rejected" only when the analyst's action differs from what the system recommended
                recommended = str(d.get("system_recommendation") or system_rec or "").lower()
                if recommended == "escalate":
                    return "Escalated to investigator — analyst confirmed the system recommendation."
                return "Escalated — analyst rejected the system recommendation."
            return "Escalated to the investigation queue."
        if action_type == "overridden":
            return f"Overrode the system recommendation → {str(d.get('override_action', '')).upper()}. Reason: \"{d.get('reason_preview', '')}\""
        if action_type == "returned":
            return "Returned to sender, with an investigation note." if d.get("notes_provided") else "Returned to sender."
        if action_type == "policy_attached":
            prev = f" (previously {d['previous_policy_number']})" if d.get("previous_policy_number") else ""
            reason = f". Reason: \"{d['reason']}\"" if d.get("reason") else "."
            return f"Manually attached policy {d.get('policy_number')}{prev}{reason}"
        if action_type == "document_uploaded":
            dt = f" ({d['document_type']})" if d.get("document_type") else ""
            return f"Uploaded \"{d.get('file_name')}\"{dt}."
        if action_type == "annotated":
            at = d.get("annotation_type")
            return f"Added a {str(at).replace('_', ' ')}." if at else "Added a note."
    except Exception:
        pass
    return ", ".join(f"{k}: {v}" for k, v in d.items())


# ── Signal-checks table — same 20 checks documented in docs/architecture/signal-engine-report.html,
# tagged generically (not per-scenario) so this renders sensibly for any payment. ─────────────────────
def _signal_rows(signals: dict, payment: dict) -> str:
    m, a, t, r, dup = signals["matching"], signals["amount"], signals["temporal"], signals["risk"], signals["duplicate"]
    rows = []

    def row(n, check, value, rule, tag_label, tag_kind):
        rows.append(
            f'<tr><td class="n">{n}</td><td>{esc(check)}</td><td>{value}</td><td>{esc(rule)}</td>'
            f'<td class="r">{_badge(tag_label, tag_kind)}</td></tr>'
        )

    def cat(name):
        rows.append(f'<tr class="cat"><td colspan="5">{esc(name)}</td></tr>')

    # 1 · Matching
    cat("Matching")
    name_score = m["name_similarity_score"]
    if name_score is None:
        row("1.1", "Name similarity", "—", "≥ 90 apply · 75–90 hold · < 75 escalate", "N/A", "neutral")
    else:
        llm_note = " (LLM-assisted)" if m.get("used_llm") else ""
        kind = "apply" if name_score >= 90 else "hold" if name_score >= 75 else "escalate"
        row("1.1", "Name similarity", f"{_pct(name_score)} / 100{llm_note}", "≥ 90 apply · 75–90 hold · < 75 escalate",
            "PASS" if kind == "apply" else "HOLD" if kind == "hold" else "LOW", kind)
    row("1.2", "Policy match confidence", _pct(m["policy_match_confidence"]), "Name 40% + policy # 40% + amount 20%", "INFO", "info")
    row("1.3", "Customer match confidence", _pct(m["customer_match_confidence"]), "Name 60% + account 20% + history 20%", "INFO", "info")
    n_support = sum(1 for k in ("account_match", "amount_match", "historical_match") if m.get(k))
    support_str = " · ".join(f"{label} {'✓' if m.get(key) else '✗'}" for key, label in
                              (("account_match", "Account"), ("amount_match", "Amount"), ("historical_match", "History")))
    row("1.4", "Supporting signals", support_str, "≥ 2 of 3 needed when name < 90% (Scenario 2)",
        f"{n_support} / 3", "apply" if n_support == 3 else "hold" if n_support == 2 else "escalate")

    # 2 · Amount
    cat("Amount")
    variance = a["amount_variance_pct"]
    if variance is None:
        row("2.1", "Variance from premium", "Not applicable — no policy matched", "2–15% hold · 15–100% investigate · >100% escalate", "N/A", "neutral")
    else:
        premium = payment["amount"] - a["difference_amount"] if a.get("difference_amount") is not None else None
        vs = f" ({_money(payment['amount'])} vs {_money(premium)})" if premium else ""
        tier, kind = (("WITHIN TOLERANCE", "apply") if variance <= 2 else
                      ("TIER 2", "hold") if variance <= 15 else
                      ("TIER 3", "hold") if variance <= 50 else
                      ("TIER 4", "hold") if variance <= 100 else
                      ("TIER 5", "escalate"))
        row("2.1", "Variance from premium", f"{_pct(variance, 1)}%{vs}", "2–15% hold · 15–100% investigate · >100% escalate", tier, kind)
    if a.get("difference_amount") is None:
        row("2.2", "Over / underpayment", "—", "—", "N/A", "neutral")
    else:
        diff = a["difference_amount"]
        row("2.2", "Over / underpayment", "Exact match" if diff == 0 else f"{'Over' if diff > 0 else 'Under'} by {_money(abs(diff))}", "—", "INFO", "neutral")
    row("2.3", "Multiple periods", f"Yes, ~{a['estimated_periods']} periods" if a.get("is_multi_period") else "No", "N × premium, ±5%",
        "DETECTED" if a.get("is_multi_period") else "NO", "info" if a.get("is_multi_period") else "neutral")
    row("2.4", "Split payment", f"Yes, {a['multi_method_fraction']} of premium" if a.get("is_multi_method") else "No", "Premium ÷ N, ±5%",
        "DETECTED" if a.get("is_multi_method") else "NO", "info" if a.get("is_multi_method") else "neutral")
    if name_score is not None and name_score >= 50:
        row("2.5", "Third-party payer", "Not checked (name ≥ 50)", "Only checked when name < 50", "N/A", "neutral")
    else:
        val = a.get("third_party_relationship") or ("Sender differs from policyholder" if a.get("is_third_party_payment") else "No — sender matches policyholder")
        row("2.5", "Third-party payer", val, "Keyword match or name mismatch, when name < 50",
            "DETECTED" if a.get("is_third_party_payment") else "PASS", "info" if a.get("is_third_party_payment") else "apply")
    hc = a["historical_consistency_score"]
    row("2.6", "Historical consistency", _pct(hc), "z-score vs past payments, ≥ 70 supports the payment",
        "PASS" if (hc or 0) >= 70 else "LOW", "apply" if (hc or 0) >= 70 else "hold")

    # 3 · Timing
    cat("Timing")
    quality = (t.get("payment_timing_quality") or "—").upper()
    days = t.get("days_from_due_date")
    kind = {"EXCELLENT": "apply", "GOOD": "apply", "ACCEPTABLE": "info", "POOR": "hold"}.get(quality, "neutral")
    row("3.1", "Payment timing", f"{quality}" + (f" ({days} days from due)" if days is not None else ""),
        "−7–0 excellent · 1–5 good · 6–14 acceptable · else poor", quality, kind)
    row("3.2", "Days since last payment", t.get("days_since_last_payment") if t.get("days_since_last_payment") is not None else "—", "—", "INFO", "neutral")

    # 4 · Risk
    cat("Risk")
    flags = r.get("risk_flag_types") or []
    row("4.1", "Risk flags", ", ".join(flags) if flags else "None", "Any active flag forces Hold (Scenario 1)",
        "FLAGGED" if flags else "PASS", "escalate" if flags else "apply")
    status_ = (r.get("account_status") or "—").title()
    row("4.2", "Account status", status_, "Inactive / closed escalate · pending holds",
        status_.upper(), "apply" if status_ == "Active" else "hold" if status_ == "Pending" else "escalate")
    risk_level = (r.get("payment_method_risk_level") or "—").upper()
    row("4.3", "Payment method risk", risk_level, "Low · Medium · High",
        risk_level, "apply" if risk_level == "LOW" else "hold" if risk_level == "MEDIUM" else "escalate")
    row("4.4", "Outstanding balance", f"{_money(r.get('outstanding_balance_cents'))} · {(r.get('outstanding_balance_status') or '—').replace('_', ' ').title()}",
        "Past-due is a date check, independent of balance", "INFO", "neutral")

    # 5 · Duplicates
    cat("Duplicates")
    if dup.get("is_duplicate_match"):
        row("5.1", "Duplicate match", f"Yes — matches {dup.get('duplicate_payment_id')}", "Sender, method, reference + amount ±$2, ±72 h", "DUPLICATE", "escalate")
        row("5.2", "Time between payments", f"{dup.get('hours_since_duplicate')} h" if dup.get("hours_since_duplicate") is not None else "—", "—", "INFO", "neutral")
        row("5.3", "Balance justification", "Yes — may be a legitimate catch-up" if dup.get("outstanding_balance_justifies") else "No — no outstanding balance", "Balance > 0 → Hold, else Escalate",
            "HOLD" if dup.get("outstanding_balance_justifies") else "ESCALATE", "hold" if dup.get("outstanding_balance_justifies") else "escalate")
        row("5.4", "Duplicate amount difference", _money(dup.get("duplicate_amount_difference")), "0 = exact, up to $2 tolerance", "INFO", "neutral")
    else:
        row("5.1", "Duplicate match", "None found", "Sender, method, reference + amount ±$2, ±72 h", "PASS", "apply")
        rows.append('<tr><td class="n">5.2–5.4</td><td>Duplicate details</td><td>—</td><td>Only populated when 5.1 matches</td>'
                    f'<td class="r">{_badge("N/A", "neutral")}</td></tr>')

    return "".join(rows)


def render_audit_report_html(detail: dict, customer_name: str | None = None) -> str:
    payment = detail["payment"]
    signals = detail["signals"]
    rec = detail["recommendation"]
    audit_logs = detail["audit_logs"]
    annotations = detail["annotations"]
    pid = payment["payment_id"]

    status_kind = _STATUS_BADGE.get(payment["status"], "neutral")
    status_label = payment["status"].replace("_", " ").title()

    # ── Section 2: outcome + human decision ──────────────────────────────────
    if rec:
        rec_kind = {"apply": "apply", "hold": "hold", "escalate": "escalate"}.get(rec["recommendation"], "neutral")
        outcome_fields = f"""
        <div class="f"><div class="l">Scenario</div><div class="v">{esc(_SCENARIO_LABELS.get(rec['scenario_route'], rec['scenario_route'] or '—'))}</div></div>
        <div class="f"><div class="l">System recommendation</div><div class="v">{_badge(rec['recommendation'].title(), rec_kind)}</div></div>
        <div class="f"><div class="l">Confidence</div><div class="v">{_pct(rec['confidence_score'])}%</div></div>
        <div class="f"><div class="l">Deciding rule</div><div class="v">{esc(_humanize_path(rec['decision_path']) or '—')}</div></div>
        """
        reasoning_html = "".join(f"<li>{esc(line)}</li>" for line in (rec.get("reasoning") or []))
        expl = f'<div class="expl"><div class="l">Reasoning · written by AI after the decision was fixed</div><ul>{reasoning_html}</ul></div>' if reasoning_html else ""
    else:
        outcome_fields = '<div class="f" style="grid-column:span 4"><div class="v">Not yet processed.</div></div>'
        expl = ""

    human_actions = [
        a for a in audit_logs
        if a.get("actor_user_id") and a["action_type"] in ("approved", "applied", "escalated", "overridden", "returned")
    ]
    if human_actions:
        last = human_actions[-1]
        human_html = (
            f'<div class="human"><div class="dot"></div><div><b>{esc(last["actor"])}</b> '
            f'{_format_detail(last["action_type"], last.get("details"), (rec or {}).get("recommendation"))} '
            f'<span style="color:var(--pw-text-muted)">— {esc(_fmt_time(last["timestamp"]))}</span></div></div>'
        )
    else:
        human_html = (
            '<div class="human" style="background:var(--pw-hold-tint);border-color:rgba(180,83,9,.28)">'
            '<div class="dot" style="background:var(--pw-hold)"></div>'
            f'<div>Still awaiting human review — current status: <b style="color:var(--pw-hold)">{esc(status_label)}</b>.</div></div>'
        )

    # ── Section 3: signal checks ──────────────────────────────────────────────
    signals_html = _signal_rows(signals, payment) if signals else '<tr><td colspan="5">No signals computed yet.</td></tr>'

    # ── Section 4: notes (visible to whoever else opens this report) ─────────
    if annotations:
        note_rows = "".join(
            f'<tr><td class="mono">{esc(_fmt_time(n["created_at"]))}</td>'
            f'<td>{esc(_ANNOTATION_LABELS.get(n["annotation_type"], n["annotation_type"]))}</td>'
            f'<td>{esc(n.get("author_user_id") or "—")}</td>'
            f'<td>{esc(n["content"])}</td></tr>'
            for n in annotations
        )
        notes_section = f"""
        <h2>4 · Notes <span>added by the analyst or investigator — visible here to both</span></h2>
        <div class="tbl"><table>
          <thead><tr><th>Time</th><th>Type</th><th>Author</th><th>Note</th></tr></thead>
          <tbody>{note_rows}</tbody>
        </table></div>
        """
        activity_num = "5"
    else:
        notes_section = ""
        activity_num = "4"

    # ── Activity log ───────────────────────────────────────────────────────────
    log_rows = "".join(
        f'<tr><td class="mono">{esc(_fmt_clock(a["timestamp"]))}</td>'
        f'<td>{esc(_actor_label(a["actor"], a["action_type"]))}</td>'
        f'<td>{esc(_ACTION_LABELS.get(a["action_type"], a["action_type"]))}</td>'
        f'<td>{esc(_format_detail(a["action_type"], a.get("details"), (rec or {}).get("recommendation")))}</td></tr>'
        for a in audit_logs
    ) or '<tr><td colspan="4">No activity yet.</td></tr>'

    reference = payment.get("reference_field_1") or payment.get("reference_field_2") or "—"
    generated = datetime.now(timezone.utc).strftime("%b %d, %Y").replace(" 0", " ")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PayWise Audit Report — {esc(pid)}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=DM+Sans:wght@500;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{{
  --pw-primary:#0A66C2;
  --pw-apply:#047857;    --pw-apply-tint:rgba(16,185,129,.10);
  --pw-hold:#B45309;     --pw-hold-tint:rgba(245,158,11,.10);
  --pw-escalate:#B91C1C; --pw-escalate-tint:rgba(239,68,68,.10);
  --pw-info:#1D4ED8;     --pw-info-tint:rgba(59,130,246,.10);
  --pw-text-primary:#1E293B; --pw-text-secondary:#64748B; --pw-text-muted:#5B6B82;
  --pw-border:#E2E8F0; --pw-bg:#F8F9FA; --pw-surface:#FFFFFF; --pw-surface-elevated:#F1F3F5;
  --pw-font-sans:'Inter',sans-serif; --pw-font-mono:'JetBrains Mono',monospace; --pw-font-display:'DM Sans',sans-serif;
  --pw-shadow-sm:0 1px 2px rgba(0,0,0,.05);
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:var(--pw-font-sans);background:var(--pw-bg);color:var(--pw-text-primary);font-size:13.5px;line-height:1.5;padding:32px 16px;-webkit-font-smoothing:antialiased}}
.mono{{font-family:var(--pw-font-mono);font-size:12.5px}}
.topbar{{max-width:900px;margin:0 auto 14px;display:flex;align-items:center;gap:8px}}
.logo-tile{{width:26px;height:26px;border-radius:7px;background:var(--pw-primary);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;font-family:var(--pw-font-display)}}
.wordmark{{font-family:var(--pw-font-display);font-weight:700;font-size:14px;color:var(--pw-text-primary)}}
.topbar .env{{margin-left:auto;font-size:11.5px;color:var(--pw-text-muted)}}
.topbar button{{font-family:var(--pw-font-sans);font-size:12px;font-weight:600;color:var(--pw-primary);background:var(--pw-info-tint);border:none;border-radius:8px;padding:6px 12px;cursor:pointer}}
.doc{{max-width:900px;margin:0 auto;background:var(--pw-surface);border:1px solid var(--pw-border);border-radius:12px;padding:36px 40px;box-shadow:var(--pw-shadow-sm)}}
header{{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;padding-bottom:18px;border-bottom:2px solid var(--pw-text-primary)}}
.brand{{font-weight:700;color:var(--pw-primary);font-size:12px;letter-spacing:.04em;text-transform:uppercase;font-family:var(--pw-font-display)}}
h1{{font-family:var(--pw-font-display);font-size:21px;font-weight:700;margin-top:4px;color:var(--pw-text-primary)}}
.id{{text-align:right;color:var(--pw-text-muted);font-size:12.5px}}
.id b{{display:block;color:var(--pw-text-primary);font-size:14px;font-family:var(--pw-font-mono);font-weight:600}}
h2{{font-family:var(--pw-font-display);font-size:12px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;margin:28px 0 10px;display:flex;gap:10px;align-items:baseline;color:var(--pw-text-primary)}}
h2 span{{color:var(--pw-text-muted);font-weight:500;text-transform:none;letter-spacing:0;font-family:var(--pw-font-sans)}}
.fields{{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid var(--pw-border);border-radius:8px;overflow:hidden}}
.f{{padding:10px 12px;border-right:1px solid var(--pw-border);border-bottom:1px solid var(--pw-border);background:var(--pw-surface)}}
.f:nth-child(4n){{border-right:0}}
.f:nth-last-child(-n+4){{border-bottom:0}}
.f .l{{font-size:10.5px;color:var(--pw-text-muted);margin-bottom:2px;text-transform:uppercase;letter-spacing:.04em}}
.f .v{{font-weight:600;color:var(--pw-text-primary)}}
.f .v.mono{{font-family:var(--pw-font-mono);font-weight:500;font-size:12.5px}}
table{{width:100%;border-collapse:collapse}}
th{{text-align:left;font-size:10.5px;font-weight:600;color:var(--pw-text-muted);text-transform:uppercase;letter-spacing:.03em;padding:7px 10px;border-bottom:1px solid var(--pw-border);background:var(--pw-surface-elevated)}}
td{{padding:8px 10px;border-bottom:1px solid var(--pw-border);vertical-align:top;color:var(--pw-text-primary)}}
tr.cat td{{background:var(--pw-surface);font-size:10.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--pw-text-muted);padding-top:14px;border-bottom:none}}
td.n{{color:var(--pw-text-muted);width:38px;font-family:var(--pw-font-mono);font-size:11.5px}}
td.r{{width:96px;text-align:right}}
.tbl{{border:1px solid var(--pw-border);border-radius:8px;overflow:hidden}}
.tbl tr:last-child td{{border-bottom:0}}
.pw-badge{{display:inline-flex;align-items:center;padding:2px 9px;border-radius:9999px;font-size:10.5px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap}}
.b-apply{{background:var(--pw-apply-tint);color:var(--pw-apply)}}
.b-hold{{background:var(--pw-hold-tint);color:var(--pw-hold)}}
.b-escalate{{background:var(--pw-escalate-tint);color:var(--pw-escalate)}}
.b-info{{background:var(--pw-info-tint);color:var(--pw-info)}}
.b-neutral{{background:var(--pw-surface-elevated);color:var(--pw-text-secondary)}}
.expl{{border:1px solid var(--pw-border);border-radius:8px;padding:12px 14px;margin-top:10px;background:var(--pw-surface)}}
.expl .l{{font-size:10.5px;color:var(--pw-text-muted);margin-bottom:6px;text-transform:uppercase;letter-spacing:.04em}}
.expl ul{{margin:0;padding-left:18px;color:var(--pw-text-primary)}}
.expl li{{margin-bottom:3px}}
.human{{display:flex;align-items:center;gap:10px;margin-top:10px;padding:10px 14px;border-radius:8px;background:var(--pw-apply-tint);border:1px solid rgba(16,185,129,.28)}}
.human .dot{{width:8px;height:8px;border-radius:50%;background:var(--pw-apply);flex-shrink:0}}
.human b{{color:var(--pw-apply)}}
footer{{margin-top:26px;padding-top:14px;border-top:1px solid var(--pw-border);display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;font-size:11.5px;color:var(--pw-text-muted)}}
@media (max-width:720px){{
  .doc{{padding:22px 16px}} .fields{{grid-template-columns:repeat(2,1fr)}}
  .f:nth-child(4n){{border-right:1px solid var(--pw-border)}} .f:nth-child(2n){{border-right:0}}
  .f:nth-last-child(-n+4){{border-bottom:1px solid var(--pw-border)}} .f:nth-last-child(-n+2){{border-bottom:0}}
  header{{flex-direction:column}} .id{{text-align:left}}
}}
@media print{{ body{{background:#fff;padding:0}} .topbar{{display:none}} .doc{{border:none;box-shadow:none;border-radius:0;max-width:100%}} }}
</style>
</head>
<body>
<div class="topbar">
  <div class="logo-tile">P</div>
  <span class="wordmark">PayWise</span>
  <span class="env">Live report — generated {esc(generated)} from current case data</span>
  <button onclick="window.print()">Download / Print</button>
</div>
<article class="doc">
<header>
  <div><div class="brand">PayWise</div><h1>Payment audit report</h1></div>
  <div class="id"><b class="mono">{esc(pid)}</b>Generated {esc(generated)}<br>Visible to: Analyst, Investigator</div>
</header>

<h2>1 · Payment <span>as received</span></h2>
<div class="fields">
  <div class="f"><div class="l">Amount</div><div class="v">{_money(payment['amount'])}</div></div>
  <div class="f"><div class="l">Received</div><div class="v">{esc(_fmt_time(payment['created_timestamp']).split(' at')[0])}</div></div>
  <div class="f"><div class="l">Method</div><div class="v">{esc(payment['payment_method'])}</div></div>
  <div class="f"><div class="l">Status</div><div class="v">{_badge(status_label, status_kind)}</div></div>
  <div class="f"><div class="l">Sender</div><div class="v">{esc(payment['sender_name'])}</div></div>
  <div class="f"><div class="l">Reference (as sent)</div><div class="v mono">{esc(reference)}</div></div>
  <div class="f"><div class="l">Matched policy</div><div class="v mono">{esc(payment.get('matched_policy_id') or 'Not matched')}</div></div>
  <div class="f"><div class="l">Policyholder</div><div class="v">{esc(customer_name or 'No customer matched')}</div></div>
</div>

<h2>2 · Outcome <span>decided by rules</span></h2>
<div class="fields">{outcome_fields}</div>
{expl}
{human_html}

<h2>3 · Signal checks <span>same 20 checks, same order, every payment</span></h2>
<div class="tbl"><table>
  <thead><tr><th>#</th><th>Check</th><th>Value</th><th>Rule</th><th style="text-align:right">Result</th></tr></thead>
  <tbody>{signals_html}</tbody>
</table></div>

{notes_section}

<h2>{activity_num} · Activity log <span>entries are only added, never edited</span></h2>
<div class="tbl"><table>
  <thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Detail</th></tr></thead>
  <tbody>{log_rows}</tbody>
</table></div>

<footer><span>PayWise · Live case data — <code class="mono">GET /api/payments/{esc(pid)}/audit-report</code></span><span>Page 1 of 1</span></footer>
</article>
</body>
</html>
"""
