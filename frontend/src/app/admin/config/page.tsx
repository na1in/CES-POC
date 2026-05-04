"use client"

import { useState, useRef, useEffect } from "react"
import { useRouter } from "next/navigation"
import {
  Bell, Settings as SettingsIcon, ChevronDown, ChevronRight,
  ChevronLeft, SlidersHorizontal, X,
} from "lucide-react"
import { mockThresholds } from "@/mocks/thresholds"
import { mockChangeRequests, mockVersionHistory, thresholdChangedBy } from "@/mocks/config"
import { mockUsers } from "@/mocks/thresholds"
import type { ConfigurationThreshold } from "@/types/user"
import type { ConfigChangeRequest, ChangeRequestStatus, ThresholdVersionEntry } from "@/types/governance"
import type { UserRole } from "@/types/user"

// ── Constants ─────────────────────────────────────────────────────────────────

const REQUEST_TABS: { key: ChangeRequestStatus | "all"; label: string }[] = [
  { key: "pending",  label: "Pending"  },
  { key: "approved", label: "Approved" },
  { key: "deployed", label: "Deployed" },
  { key: "rejected", label: "Rejected" },
  { key: "all",      label: "All"      },
]

const DIRECTOR_USER_ID = "USR-003"

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionCard({
  title, icon, defaultOpen = true, children,
}: {
  title: string; icon: React.ReactNode; defaultOpen?: boolean; children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="pw-card" style={{ marginBottom: 16, overflow: "hidden" }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: "100%", display: "flex", alignItems: "center", gap: 10,
          padding: "14px 20px", background: "none", border: "none", cursor: "pointer",
          borderBottom: open ? "1px solid var(--pw-border)" : "none",
        }}
      >
        <span style={{ color: "var(--pw-primary)" }}>{icon}</span>
        <span style={{ fontSize: 14, fontWeight: 700, color: "var(--pw-text-primary)", fontFamily: "var(--pw-font-display)", flex: 1, textAlign: "left" }}>{title}</span>
        {open ? <ChevronDown size={14} color="var(--pw-text-muted)" /> : <ChevronRight size={14} color="var(--pw-text-muted)" />}
      </button>
      {open && <div>{children}</div>}
    </div>
  )
}

function StatusBadge({ status }: { status: ChangeRequestStatus }) {
  const map: Record<ChangeRequestStatus, { bg: string; color: string; label: string }> = {
    pending:  { bg: "var(--pw-hold-tint)",     color: "var(--pw-hold)",     label: "PENDING"  },
    approved: { bg: "var(--pw-apply-tint)",    color: "var(--pw-apply)",    label: "APPROVED" },
    deployed: { bg: "rgba(124,77,255,0.12)",   color: "var(--pw-primary)",  label: "DEPLOYED" },
    rejected: { bg: "var(--pw-escalate-tint)", color: "var(--pw-escalate)", label: "REJECTED" },
  }
  const { bg, color, label } = map[status]
  return (
    <span style={{ display: "inline-flex", alignItems: "center", background: bg, color, borderRadius: 4, padding: "2px 8px", fontSize: 11, fontWeight: 700, letterSpacing: "0.04em" }}>
      {label}
    </span>
  )
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 200, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ background: "var(--pw-surface)", borderRadius: 12, padding: "24px 28px", width: "100%", maxWidth: 480, boxShadow: "var(--pw-shadow-md)", position: "relative" }}>
        <button onClick={onClose} aria-label="Close dialog" style={{ position: "absolute", top: 14, right: 14, background: "none", border: "none", cursor: "pointer", color: "var(--pw-text-muted)" }}>
          <X size={16} />
        </button>
        <p style={{ fontSize: 15, fontWeight: 700, fontFamily: "var(--pw-font-display)", color: "var(--pw-text-primary)", margin: "0 0 16px" }}>{title}</p>
        {children}
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ConfigManagementPage() {
  const router = useRouter()
  const [activeRole, setActiveRole] = useState<UserRole>("admin")
  const [roleMenuOpen, setRoleMenuOpen] = useState(false)
  const currentUser = mockUsers.find(u => u.role === activeRole) ?? mockUsers[0]

  // Section 1 — live thresholds (updated on deploy/rollback)
  const [thresholds, setThresholds] = useState<ConfigurationThreshold[]>(mockThresholds)

  // Section 2 — propose form
  const [proposing, setProposing] = useState<ConfigurationThreshold | null>(null)
  const [proposedValue, setProposedValue] = useState("")
  const [rationale, setRationale] = useState("")
  const [projectedImpact, setProjectedImpact] = useState("")
  const [rationaleError, setRationaleError] = useState("")
  const [proposeSuccess, setProposeSuccess] = useState(false)
  const formRef = useRef<HTMLDivElement>(null)

  // Section 3 — change requests
  const [changeRequests, setChangeRequests] = useState<ConfigChangeRequest[]>(mockChangeRequests)
  const [requestTab, setRequestTab] = useState<ChangeRequestStatus | "all">("pending")

  // Section 4 — version history
  const [versionHistory, setVersionHistory] = useState<Record<string, ThresholdVersionEntry[]>>(mockVersionHistory)
  const [expandedParam, setExpandedParam] = useState<string | null>(null)

  // Deploy dialog
  const [deployTarget, setDeployTarget] = useState<ConfigChangeRequest | null>(null)

  // Rollback dialog
  const [rollbackTarget, setRollbackTarget] = useState<ConfigChangeRequest | null>(null)
  const [directorId, setDirectorId] = useState("")
  const [directorIdError, setDirectorIdError] = useState("")

  // Scroll to form when it opens
  useEffect(() => {
    if (proposing && formRef.current) {
      formRef.current.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }, [proposing])

  function openProposeForm(t: ConfigurationThreshold) {
    setProposing(t)
    setProposedValue("")
    setRationale("")
    setProjectedImpact("")
    setRationaleError("")
    setProposeSuccess(false)
  }

  function submitPropose() {
    if (!proposing) return
    if (rationale.trim().length < 20) {
      setRationaleError("Rationale must be at least 20 characters.")
      return
    }
    if (!proposedValue.trim()) {
      setRationaleError("Proposed value is required.")
      return
    }
    const newRequest: ConfigChangeRequest = {
      request_id: `CR-${String(changeRequests.length + 1).padStart(3, "0")}`,
      parameter_name: proposing.parameter_name,
      current_value: proposing.parameter_value,
      proposed_value: proposedValue.trim(),
      rationale: rationale.trim(),
      projected_impact: projectedImpact.trim() || null,
      proposed_by: currentUser.name,
      proposed_at: new Date().toISOString(),
      status: "pending",
      reviewed_by: null,
      reviewed_at: null,
      review_comment: null,
      deployed_at: null,
      deployed_by: null,
    }
    setChangeRequests(prev => [newRequest, ...prev])
    setProposeSuccess(true)
    setProposing(null)
    setRequestTab("pending")
  }

  function confirmDeploy() {
    if (!deployTarget) return
    const now = new Date().toISOString()
    // Update change request status
    setChangeRequests(prev => prev.map(r =>
      r.request_id === deployTarget.request_id
        ? { ...r, status: "deployed" as ChangeRequestStatus, deployed_at: now, deployed_by: currentUser.name }
        : r
    ))
    // Update threshold value
    setThresholds(prev => prev.map(t =>
      t.parameter_name === deployTarget.parameter_name
        ? { ...t, parameter_value: deployTarget.proposed_value, effective_date: now }
        : t
    ))
    // Append version history entry
    const newEntry: ThresholdVersionEntry = {
      version_id: `VH-${Date.now()}`,
      parameter_name: deployTarget.parameter_name,
      old_value: deployTarget.current_value,
      new_value: deployTarget.proposed_value,
      changed_by: currentUser.name,
      changed_at: now,
      change_request_id: deployTarget.request_id,
    }
    setVersionHistory(prev => ({
      ...prev,
      [deployTarget.parameter_name]: [newEntry, ...(prev[deployTarget.parameter_name] ?? [])],
    }))
    setDeployTarget(null)
    setRequestTab("deployed")
  }

  function confirmRollback() {
    if (!rollbackTarget) return
    if (directorId.trim() !== DIRECTOR_USER_ID) {
      setDirectorIdError(`Must be director user ID (${DIRECTOR_USER_ID}).`)
      return
    }
    const now = new Date().toISOString()
    // Revert change request to approved
    setChangeRequests(prev => prev.map(r =>
      r.request_id === rollbackTarget.request_id
        ? { ...r, status: "approved" as ChangeRequestStatus, deployed_at: null, deployed_by: null }
        : r
    ))
    // Revert threshold value
    setThresholds(prev => prev.map(t =>
      t.parameter_name === rollbackTarget.parameter_name
        ? { ...t, parameter_value: rollbackTarget.current_value, effective_date: now }
        : t
    ))
    // Append rollback entry to version history
    const newEntry: ThresholdVersionEntry = {
      version_id: `VH-${Date.now()}`,
      parameter_name: rollbackTarget.parameter_name,
      old_value: rollbackTarget.proposed_value,
      new_value: rollbackTarget.current_value,
      changed_by: currentUser.name,
      changed_at: now,
      change_request_id: rollbackTarget.request_id,
    }
    setVersionHistory(prev => ({
      ...prev,
      [rollbackTarget.parameter_name]: [newEntry, ...(prev[rollbackTarget.parameter_name] ?? [])],
    }))
    setRollbackTarget(null)
    setDirectorId("")
    setDirectorIdError("")
    setRequestTab("approved")
  }

  const filteredRequests = changeRequests.filter(r =>
    requestTab === "all" || r.status === requestTab
  )

  const inputStyle: React.CSSProperties = {
    border: "1px solid var(--pw-border)", borderRadius: 8,
    padding: "7px 10px", fontSize: 13, color: "var(--pw-text-primary)",
    background: "var(--pw-surface)", outline: "none", width: "100%", boxSizing: "border-box",
  }
  const labelStyle: React.CSSProperties = {
    fontSize: 12, fontWeight: 600, color: "var(--pw-text-secondary)",
    display: "block", marginBottom: 5,
  }
  const TH: React.CSSProperties = {
    padding: "10px 14px", fontSize: 11, fontWeight: 600,
    color: "var(--pw-text-secondary)", textTransform: "uppercase",
    letterSpacing: "0.05em", textAlign: "left",
    borderBottom: "1px solid var(--pw-border)", background: "var(--pw-bg)", whiteSpace: "nowrap",
  }
  const TD: React.CSSProperties = {
    padding: "11px 14px", fontSize: 13, color: "var(--pw-text-primary)",
    borderBottom: "1px solid var(--pw-border)", verticalAlign: "middle",
  }

  return (
    <div style={{ minHeight: "100vh", background: "var(--pw-bg)", display: "flex", flexDirection: "column" }}>

      {/* Nav */}
      <nav style={{ height: "var(--pw-nav-height)", background: "var(--pw-surface)", borderBottom: "1px solid var(--pw-border)", display: "flex", alignItems: "center", padding: "0 20px", gap: 12, position: "sticky", top: 0, zIndex: 50 }}>
        <button onClick={() => router.push("/")} style={{ display: "flex", alignItems: "center", gap: 6, background: "none", border: "none", cursor: "pointer", marginRight: "auto" }}>
          <div style={{ width: 28, height: 28, background: "var(--pw-primary)", borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <span style={{ color: "#fff", fontWeight: 700, fontSize: 13, fontFamily: "var(--pw-font-display)" }}>P</span>
          </div>
          <span style={{ fontWeight: 700, fontSize: 15, fontFamily: "var(--pw-font-display)", color: "var(--pw-text-primary)" }}>PayWise</span>
        </button>
        <div style={{ display: "flex", alignItems: "center", gap: 6, background: "var(--pw-bg)", border: "1px solid var(--pw-border)", borderRadius: 8, padding: "5px 10px", width: 200 }}>
          <span style={{ fontSize: 12, color: "var(--pw-text-muted)", flex: 1 }}>Search…</span>
          <span style={{ fontSize: 10, color: "var(--pw-text-muted)", background: "var(--pw-border)", padding: "1px 4px", borderRadius: 3 }}>⌘K</span>
        </div>
        <Bell size={16} color="var(--pw-text-secondary)" style={{ cursor: "pointer" }} />
        <SettingsIcon size={16} color="var(--pw-text-secondary)" style={{ cursor: "pointer" }} onClick={() => router.push("/settings")} />
        <div style={{ position: "relative" }}>
          <button aria-label="Switch role" onClick={() => setRoleMenuOpen(o => !o)} style={{ display: "flex", alignItems: "center", gap: 6, background: "var(--pw-bg)", border: "1px solid var(--pw-border)", borderRadius: 8, padding: "4px 10px", fontSize: 12, color: "var(--pw-text-secondary)", cursor: "pointer" }}>
            <div style={{ width: 22, height: 22, borderRadius: "50%", background: "var(--pw-primary)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontWeight: 700, fontSize: 10 }}>
              {currentUser.name.split(" ").map((w: string) => w[0]).join("").slice(0, 2)}
            </div>
            {currentUser.name.split(" ")[0]}
            <ChevronDown size={12} />
          </button>
          {roleMenuOpen && (
            <div style={{ position: "absolute", right: 0, top: "calc(100% + 6px)", background: "var(--pw-surface)", border: "1px solid var(--pw-border)", borderRadius: 8, boxShadow: "var(--pw-shadow-md)", zIndex: 60, minWidth: 180, overflow: "hidden" }}>
              {mockUsers.map((u: { user_id: string; role: UserRole; name: string }) => (
                <button key={u.user_id} onClick={() => { setActiveRole(u.role); setRoleMenuOpen(false) }} style={{ display: "block", width: "100%", textAlign: "left", padding: "9px 14px", fontSize: 13, cursor: "pointer", background: u.role === activeRole ? "var(--pw-bg)" : "transparent", border: "none", color: "var(--pw-text-primary)" }}>
                  {u.name}<span style={{ fontSize: 11, color: "var(--pw-text-muted)", marginLeft: 6 }}>({u.role})</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </nav>

      {/* Page header */}
      <div style={{ background: "var(--pw-surface)", borderBottom: "1px solid var(--pw-border)", padding: "16px 24px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button onClick={() => router.push("/admin")} style={{ display: "flex", alignItems: "center", gap: 4, background: "none", border: "none", cursor: "pointer", color: "var(--pw-text-secondary)", padding: 0 }} aria-label="Back to Admin">
            <ChevronLeft size={16} />
          </button>
          <SlidersHorizontal size={18} color="var(--pw-primary)" />
          <h1 style={{ fontSize: 20, fontWeight: 700, fontFamily: "var(--pw-font-display)", color: "var(--pw-text-primary)", margin: 0 }}>Configuration Management</h1>
        </div>
        <p style={{ fontSize: 13, color: "var(--pw-text-secondary)", margin: "4px 0 0 54px" }}>
          Threshold change-request workflow — propose, approve, deploy, and roll back.
        </p>
      </div>

      {/* Body */}
      <div style={{ flex: 1, padding: "24px", maxWidth: 1280, width: "100%", boxSizing: "border-box" }}>

        {/* ── Section 1: Current Thresholds ── */}
        <SectionCard title="Current Thresholds" icon={<SlidersHorizontal size={16} />}>
          {proposeSuccess && (
            <div style={{ margin: "12px 20px 0", padding: "10px 14px", borderRadius: 8, background: "var(--pw-apply-tint)", color: "var(--pw-apply)", fontSize: 13, fontWeight: 500 }}>
              Change request submitted and added to the Pending queue.
            </div>
          )}
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={TH}>Parameter</th>
                  <th style={TH}>Current Value</th>
                  <th style={TH}>Description</th>
                  <th style={TH}>Last Changed</th>
                  <th style={TH}>Changed By</th>
                  <th style={TH}></th>
                </tr>
              </thead>
              <tbody>
                {thresholds.map(t => (
                  <tr key={t.parameter_name} style={{ background: "var(--pw-surface)" }}>
                    <td style={{ ...TD, fontFamily: "var(--pw-font-mono)", fontSize: 12, color: "var(--pw-text-secondary)" }}>{t.parameter_name}</td>
                    <td style={{ ...TD, fontFamily: "var(--pw-font-mono)", fontWeight: 700, color: "var(--pw-primary)" }}>{t.parameter_value}</td>
                    <td style={{ ...TD, color: "var(--pw-text-secondary)", fontSize: 12 }}>{t.description}</td>
                    <td style={{ ...TD, fontSize: 12, color: "var(--pw-text-muted)", whiteSpace: "nowrap" }}>
                      {new Date(t.effective_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                    </td>
                    <td style={{ ...TD, fontSize: 12, color: "var(--pw-text-secondary)", whiteSpace: "nowrap" }}>
                      {thresholdChangedBy[t.parameter_name] ?? "—"}
                    </td>
                    <td style={{ ...TD, textAlign: "right" }}>
                      <button
                        onClick={() => openProposeForm(t)}
                        aria-label={`Propose change for ${t.parameter_name}`}
                        style={{ fontSize: 12, fontWeight: 500, color: "var(--pw-primary)", background: "none", border: "1px solid var(--pw-border)", borderRadius: 6, padding: "4px 10px", cursor: "pointer" }}
                      >
                        Propose Change
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        {/* ── Section 2: Propose Change Form ── */}
        <div ref={formRef}>
          <SectionCard key={proposing?.parameter_name ?? "propose-empty"} title="Propose a Change" icon={<ChevronRight size={16} />} defaultOpen={!!proposing}>
            {!proposing ? (
              <div style={{ padding: "20px 24px" }}>
                <p style={{ fontSize: 13, color: "var(--pw-text-muted)", margin: 0 }}>
                  Click <strong>Propose Change</strong> on any threshold row above to open the form.
                </p>
              </div>
            ) : (
              <div style={{ padding: "20px 24px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                {/* Parameter (read-only) */}
                <div>
                  <label style={labelStyle}>Parameter Name</label>
                  <input
                    readOnly
                    value={proposing.parameter_name}
                    style={{ ...inputStyle, background: "var(--pw-bg)", color: "var(--pw-text-muted)", fontFamily: "var(--pw-font-mono)", fontSize: 12 }}
                    aria-label="Parameter name (read-only)"
                  />
                </div>
                {/* Current value (read-only) */}
                <div>
                  <label style={labelStyle}>Current Value</label>
                  <input
                    readOnly
                    value={proposing.parameter_value}
                    style={{ ...inputStyle, background: "var(--pw-bg)", color: "var(--pw-text-muted)", fontFamily: "var(--pw-font-mono)", fontSize: 12 }}
                    aria-label="Current value (read-only)"
                  />
                </div>
                {/* Proposed value */}
                <div>
                  <label style={labelStyle}>Proposed Value <span style={{ color: "var(--pw-escalate)" }}>*</span></label>
                  <input
                    type="text"
                    value={proposedValue}
                    onChange={e => setProposedValue(e.target.value)}
                    placeholder="e.g. 93%"
                    style={{ ...inputStyle, fontFamily: "var(--pw-font-mono)", fontSize: 12 }}
                    aria-label="Proposed value"
                  />
                </div>
                {/* Projected impact */}
                <div>
                  <label style={labelStyle}>Projected Impact <span style={{ color: "var(--pw-text-muted)", fontWeight: 400 }}>(optional)</span></label>
                  <input
                    type="text"
                    value={projectedImpact}
                    onChange={e => setProjectedImpact(e.target.value)}
                    placeholder="Est. impact on volume or accuracy"
                    style={inputStyle}
                    aria-label="Projected impact"
                  />
                </div>
                {/* Rationale */}
                <div style={{ gridColumn: "1 / -1" }}>
                  <label style={labelStyle}>
                    Rationale <span style={{ color: "var(--pw-escalate)" }}>*</span>
                    <span style={{ marginLeft: 6, fontWeight: 400, color: rationaleError ? "var(--pw-escalate)" : rationale.length >= 20 ? "var(--pw-apply)" : "var(--pw-text-muted)" }}>
                      ({rationale.length}/20 min)
                    </span>
                  </label>
                  <textarea
                    value={rationale}
                    onChange={e => { setRationale(e.target.value); if (rationaleError) setRationaleError("") }}
                    rows={3}
                    placeholder="Explain why this change is needed (min 20 characters)"
                    style={{ ...inputStyle, resize: "vertical", fontFamily: "inherit" }}
                    aria-label="Rationale"
                  />
                  {rationaleError && (
                    <p style={{ fontSize: 12, color: "var(--pw-escalate)", margin: "4px 0 0" }} role="alert">{rationaleError}</p>
                  )}
                </div>
                {/* Actions */}
                <div style={{ gridColumn: "1 / -1", display: "flex", gap: 10 }}>
                  <button
                    onClick={submitPropose}
                    style={{ background: "var(--pw-primary)", color: "#fff", border: "none", borderRadius: 8, padding: "8px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}
                  >
                    Submit Request
                  </button>
                  <button
                    onClick={() => setProposing(null)}
                    style={{ background: "none", color: "var(--pw-text-secondary)", border: "1px solid var(--pw-border)", borderRadius: 8, padding: "8px 16px", fontSize: 13, cursor: "pointer" }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </SectionCard>
        </div>

        {/* ── Section 3: Change Request List ── */}
        <SectionCard title="Change Requests" icon={<ChevronRight size={16} />}>
          {/* Tab bar */}
          <div style={{ display: "flex", borderBottom: "1px solid var(--pw-border)", padding: "0 20px" }}>
            {REQUEST_TABS.map(tab => (
              <button
                key={tab.key}
                onClick={() => setRequestTab(tab.key)}
                aria-selected={requestTab === tab.key}
                style={{
                  padding: "10px 14px", fontSize: 13, fontWeight: requestTab === tab.key ? 600 : 400,
                  color: requestTab === tab.key ? "var(--pw-primary)" : "var(--pw-text-secondary)",
                  background: "none", border: "none", cursor: "pointer",
                  borderBottom: requestTab === tab.key ? "2px solid var(--pw-primary)" : "2px solid transparent",
                  marginBottom: -1,
                }}
              >
                {tab.label}
                <span style={{ marginLeft: 5, fontSize: 11, color: "var(--pw-text-muted)" }}>
                  ({changeRequests.filter(r => tab.key === "all" || r.status === tab.key).length})
                </span>
              </button>
            ))}
          </div>

          {filteredRequests.length === 0 ? (
            <div style={{ padding: "32px 24px", textAlign: "center" }}>
              <p style={{ fontSize: 13, color: "var(--pw-text-muted)", margin: 0 }}>No change requests in this category.</p>
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    <th style={TH}>ID</th>
                    <th style={TH}>Parameter</th>
                    <th style={TH}>Change</th>
                    <th style={TH}>Proposed By</th>
                    <th style={TH}>Proposed</th>
                    <th style={TH}>Status</th>
                    <th style={TH}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRequests.map(r => (
                    <tr key={r.request_id} style={{ background: "var(--pw-surface)" }}>
                      <td style={{ ...TD, fontFamily: "var(--pw-font-mono)", fontSize: 12, color: "var(--pw-text-muted)" }}>{r.request_id}</td>
                      <td style={{ ...TD, fontFamily: "var(--pw-font-mono)", fontSize: 12 }}>{r.parameter_name}</td>
                      <td style={{ ...TD, fontSize: 12 }}>
                        <span style={{ fontFamily: "var(--pw-font-mono)", color: "var(--pw-text-secondary)" }}>{r.current_value}</span>
                        <span style={{ margin: "0 6px", color: "var(--pw-text-muted)" }}>→</span>
                        <span style={{ fontFamily: "var(--pw-font-mono)", fontWeight: 700, color: "var(--pw-primary)" }}>{r.proposed_value}</span>
                      </td>
                      <td style={{ ...TD, fontSize: 12, color: "var(--pw-text-secondary)" }}>{r.proposed_by}</td>
                      <td style={{ ...TD, fontSize: 12, color: "var(--pw-text-muted)", whiteSpace: "nowrap" }}>
                        {new Date(r.proposed_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                      </td>
                      <td style={TD}><StatusBadge status={r.status} /></td>
                      <td style={{ ...TD, whiteSpace: "nowrap" }}>
                        {r.status === "approved" && (
                          <button
                            onClick={() => setDeployTarget(r)}
                            aria-label={`Deploy ${r.request_id}`}
                            style={{ background: "var(--pw-apply)", color: "#fff", border: "none", borderRadius: 6, padding: "5px 12px", fontSize: 12, fontWeight: 600, cursor: "pointer" }}
                          >
                            Deploy
                          </button>
                        )}
                        {r.status === "deployed" && (
                          <button
                            onClick={() => { setRollbackTarget(r); setDirectorId(""); setDirectorIdError("") }}
                            aria-label={`Rollback ${r.request_id}`}
                            style={{ background: "none", color: "var(--pw-escalate)", border: "1px solid var(--pw-escalate)", borderRadius: 6, padding: "5px 12px", fontSize: 12, fontWeight: 600, cursor: "pointer" }}
                          >
                            Rollback
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        {/* ── Section 4: Version History ── */}
        <SectionCard title="Version History" icon={<ChevronRight size={16} />} defaultOpen={false}>
          <div style={{ padding: "8px 0" }}>
            {thresholds.map(t => {
              const history = versionHistory[t.parameter_name] ?? []
              const isExpanded = expandedParam === t.parameter_name
              return (
                <div key={t.parameter_name} style={{ borderBottom: "1px solid var(--pw-border)" }}>
                  <button
                    onClick={() => setExpandedParam(isExpanded ? null : t.parameter_name)}
                    aria-expanded={isExpanded}
                    aria-label={`Toggle history for ${t.parameter_name}`}
                    style={{ width: "100%", display: "flex", alignItems: "center", gap: 10, padding: "12px 20px", background: "none", border: "none", cursor: "pointer" }}
                  >
                    {isExpanded ? <ChevronDown size={13} color="var(--pw-text-muted)" /> : <ChevronRight size={13} color="var(--pw-text-muted)" />}
                    <span style={{ fontFamily: "var(--pw-font-mono)", fontSize: 12, color: "var(--pw-text-secondary)", flex: 1, textAlign: "left" }}>{t.parameter_name}</span>
                    <span style={{ fontSize: 11, color: "var(--pw-text-muted)" }}>{history.length} change{history.length !== 1 ? "s" : ""}</span>
                  </button>
                  {isExpanded && (
                    <div style={{ padding: "0 20px 12px 44px" }}>
                      {history.length === 0 ? (
                        <p style={{ fontSize: 12, color: "var(--pw-text-muted)", margin: 0 }}>No history.</p>
                      ) : (
                        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                          <thead>
                            <tr>
                              <th style={{ ...TH, fontSize: 10, padding: "6px 10px" }}>Date</th>
                              <th style={{ ...TH, fontSize: 10, padding: "6px 10px" }}>Old Value</th>
                              <th style={{ ...TH, fontSize: 10, padding: "6px 10px" }}>New Value</th>
                              <th style={{ ...TH, fontSize: 10, padding: "6px 10px" }}>Changed By</th>
                              <th style={{ ...TH, fontSize: 10, padding: "6px 10px" }}>Request ID</th>
                            </tr>
                          </thead>
                          <tbody>
                            {history.map(v => (
                              <tr key={v.version_id}>
                                <td style={{ ...TD, padding: "8px 10px", fontSize: 11, color: "var(--pw-text-muted)" }}>
                                  {new Date(v.changed_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                                </td>
                                <td style={{ ...TD, padding: "8px 10px", fontFamily: "var(--pw-font-mono)", fontSize: 11 }}>{v.old_value}</td>
                                <td style={{ ...TD, padding: "8px 10px", fontFamily: "var(--pw-font-mono)", fontSize: 11, fontWeight: 700, color: "var(--pw-primary)" }}>{v.new_value}</td>
                                <td style={{ ...TD, padding: "8px 10px", fontSize: 11, color: "var(--pw-text-secondary)" }}>{v.changed_by}</td>
                                <td style={{ ...TD, padding: "8px 10px", fontFamily: "var(--pw-font-mono)", fontSize: 11, color: "var(--pw-text-muted)" }}>{v.change_request_id ?? "—"}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </SectionCard>
      </div>

      {/* ── Deploy confirmation dialog ── */}
      {deployTarget && (
        <Modal title="Confirm Deployment" onClose={() => setDeployTarget(null)}>
          <p style={{ fontSize: 13, color: "var(--pw-text-secondary)", margin: "0 0 12px" }}>
            Deploy <strong style={{ fontFamily: "var(--pw-font-mono)" }}>{deployTarget.parameter_name}</strong>?
          </p>
          <p style={{ fontSize: 13, margin: "0 0 20px" }}>
            <span style={{ fontFamily: "var(--pw-font-mono)", color: "var(--pw-text-secondary)" }}>{deployTarget.current_value}</span>
            <span style={{ margin: "0 8px", color: "var(--pw-text-muted)" }}>→</span>
            <span style={{ fontFamily: "var(--pw-font-mono)", fontWeight: 700, color: "var(--pw-primary)" }}>{deployTarget.proposed_value}</span>
          </p>
          <p style={{ fontSize: 12, color: "var(--pw-text-muted)", margin: "0 0 20px" }}>
            This will take effect immediately and update the live thresholds table.
          </p>
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button onClick={() => setDeployTarget(null)} style={{ background: "none", border: "1px solid var(--pw-border)", borderRadius: 8, padding: "8px 16px", fontSize: 13, cursor: "pointer", color: "var(--pw-text-secondary)" }}>
              Cancel
            </button>
            <button
              onClick={confirmDeploy}
              aria-label="Confirm deploy"
              style={{ background: "var(--pw-apply)", color: "#fff", border: "none", borderRadius: 8, padding: "8px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}
            >
              Deploy
            </button>
          </div>
        </Modal>
      )}

      {/* ── Rollback confirmation dialog ── */}
      {rollbackTarget && (
        <Modal title="Rollback Requires Director Approval" onClose={() => { setRollbackTarget(null); setDirectorId(""); setDirectorIdError("") }}>
          <p style={{ fontSize: 13, color: "var(--pw-text-secondary)", margin: "0 0 16px" }}>
            This will revert <strong style={{ fontFamily: "var(--pw-font-mono)" }}>{rollbackTarget.parameter_name}</strong> from{" "}
            <span style={{ fontFamily: "var(--pw-font-mono)", fontWeight: 700, color: "var(--pw-primary)" }}>{rollbackTarget.proposed_value}</span> back to{" "}
            <span style={{ fontFamily: "var(--pw-font-mono)", color: "var(--pw-text-secondary)" }}>{rollbackTarget.current_value}</span>.
          </p>
          <label style={{ ...labelStyle, marginBottom: 6 }}>
            Enter director user ID to confirm
          </label>
          <input
            type="text"
            value={directorId}
            onChange={e => { setDirectorId(e.target.value); setDirectorIdError("") }}
            placeholder="e.g. USR-003"
            style={{ ...inputStyle, marginBottom: 4, fontFamily: "var(--pw-font-mono)" }}
            aria-label="Director user ID"
          />
          {directorIdError && (
            <p style={{ fontSize: 12, color: "var(--pw-escalate)", margin: "0 0 12px" }} role="alert">{directorIdError}</p>
          )}
          {!directorIdError && <div style={{ marginBottom: 16 }} />}
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button onClick={() => { setRollbackTarget(null); setDirectorId(""); setDirectorIdError("") }} style={{ background: "none", border: "1px solid var(--pw-border)", borderRadius: 8, padding: "8px 16px", fontSize: 13, cursor: "pointer", color: "var(--pw-text-secondary)" }}>
              Cancel
            </button>
            <button
              onClick={confirmRollback}
              aria-label="Confirm rollback"
              style={{ background: "none", color: "var(--pw-escalate)", border: "1px solid var(--pw-escalate)", borderRadius: 8, padding: "8px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}
            >
              Rollback
            </button>
          </div>
        </Modal>
      )}

      {/* Footer */}
      <footer style={{ height: "var(--pw-footer-height)", background: "var(--pw-surface)", borderTop: "1px solid var(--pw-border)", display: "flex", alignItems: "center", padding: "0 20px", gap: 16, fontSize: 11, color: "var(--pw-text-muted)", position: "sticky", bottom: 0, zIndex: 40 }}>
        <span style={{ color: "var(--pw-apply)", fontWeight: 600 }}>● Audit Active</span>
        <span>User: {currentUser.name}</span>
        <span>Role: {currentUser.role}</span>
        <span style={{ marginLeft: "auto" }}>
          Press <kbd style={{ background: "var(--pw-surface-elevated)", padding: "1px 5px", borderRadius: 3, fontFamily: "var(--pw-font-mono)" }}>?</kbd> for keyboard shortcuts
        </span>
      </footer>
    </div>
  )
}
