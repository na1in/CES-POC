"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { AlertTriangle, X } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"
import { mockPayments, mockRecommendations } from "@/mocks/payments"
import type { ScenarioRoute } from "@/types/recommendation"
import type { PaymentMethod } from "@/types/payment"

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatUSD(cents: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(cents / 100)
}

function formatAge(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const minutes = Math.floor(diff / 60_000)
  const hours = Math.floor(diff / 3_600_000)
  const days = Math.floor(diff / 86_400_000)
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  return `${days}d ago`
}

type ConfidenceBand = "Low" | "Medium" | "High"

function getBand(score: number): ConfidenceBand {
  if (score < 40) return "Low"
  if (score <= 70) return "Medium"
  return "High"
}

const SCENARIO_LABEL: Record<ScenarioRoute, string> = {
  scenario_1: "Sc1",
  scenario_2: "Sc2",
  scenario_3: "Sc3",
  scenario_4: "Sc4",
  scenario_5: "Sc5",
}

const SCENARIO_COLOR: Record<ScenarioRoute, string> = {
  scenario_1: "bg-blue-100 text-blue-800",
  scenario_2: "bg-purple-100 text-purple-800",
  scenario_3: "bg-orange-100 text-orange-800",
  scenario_4: "bg-red-100 text-red-800",
  scenario_5: "bg-slate-100 text-slate-700",
}

const ALL_SCENARIOS: ScenarioRoute[] = [
  "scenario_1", "scenario_2", "scenario_3", "scenario_4", "scenario_5",
]
const ALL_BANDS: ConfidenceBand[] = ["Low", "Medium", "High"]
const ALL_METHODS: PaymentMethod[] = ["ACH", "Check", "Credit Card", "Wire"]

// ── Filter chip ───────────────────────────────────────────────────────────────

function FilterChip({
  active,
  activeClass,
  onClick,
  children,
}: {
  active: boolean
  activeClass: string
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "rounded-md border px-2 py-0.5 text-xs font-medium transition-colors",
        active
          ? cn(activeClass, "border-transparent")
          : "border-border text-muted-foreground hover:bg-muted",
      )}
    >
      {children}
    </button>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function QueueDashboard() {
  const router = useRouter()

  const [scenarioFilter, setScenarioFilter] = useState<Set<ScenarioRoute>>(new Set())
  const [bandFilter, setBandFilter] = useState<Set<ConfidenceBand>>(new Set())
  const [methodFilter, setMethodFilter] = useState<Set<PaymentMethod>>(new Set())
  const [bannerDismissed, setBannerDismissed] = useState(false)

  function toggle<T>(set: Set<T>, value: T): Set<T> {
    const next = new Set(set)
    next.has(value) ? next.delete(value) : next.add(value)
    return next
  }

  function clearFilters() {
    setScenarioFilter(new Set())
    setBandFilter(new Set())
    setMethodFilter(new Set())
  }

  const hasFilters = scenarioFilter.size > 0 || bandFilter.size > 0 || methodFilter.size > 0
  const failedCount = mockPayments.filter(p => p.status === "processing_failed").length

  const rows = mockPayments
    .map(p => ({ payment: p, rec: mockRecommendations[p.payment_id] ?? null }))
    .sort((a, b) => (a.rec?.confidence_score ?? 0) - (b.rec?.confidence_score ?? 0))

  const filtered = rows.filter(({ payment, rec }) => {
    if (!rec) return true
    if (scenarioFilter.size > 0 && !scenarioFilter.has(rec.scenario_route)) return false
    if (bandFilter.size > 0 && !bandFilter.has(getBand(rec.confidence_score))) return false
    if (methodFilter.size > 0 && !methodFilter.has(payment.payment_method)) return false
    return true
  })

  return (
    <div className="min-h-screen bg-background">
      {/* Page header */}
      <div className="border-b px-6 py-4">
        <h1 className="text-lg font-semibold">Payment Queue</h1>
        <p className="text-sm text-muted-foreground">
          Lowest confidence first — most uncertain cases need attention first
        </p>
      </div>

      <div className="space-y-4 px-6 py-4">
        {/* Processing-failed banner */}
        {failedCount > 0 && !bannerDismissed && (
          <div className="flex items-center justify-between rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            <div className="flex items-center gap-2">
              <AlertTriangle className="size-4 shrink-0" />
              <span>
                {failedCount} payment{failedCount !== 1 ? "s" : ""} failed to process.
              </span>
              <button className="font-medium underline underline-offset-2 hover:no-underline">
                Reprocess all
              </button>
            </div>
            <button
              onClick={() => setBannerDismissed(true)}
              aria-label="Dismiss"
              className="text-amber-600 hover:text-amber-900"
            >
              <X className="size-4" />
            </button>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-medium text-muted-foreground">Scenario</span>
            {ALL_SCENARIOS.map(s => (
              <FilterChip
                key={s}
                active={scenarioFilter.has(s)}
                activeClass={SCENARIO_COLOR[s]}
                onClick={() => setScenarioFilter(toggle(scenarioFilter, s))}
              >
                {SCENARIO_LABEL[s]}
              </FilterChip>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-medium text-muted-foreground">Confidence</span>
            {ALL_BANDS.map(band => (
              <FilterChip
                key={band}
                active={bandFilter.has(band)}
                activeClass={
                  band === "Low"
                    ? "bg-red-100 text-red-800"
                    : band === "Medium"
                      ? "bg-amber-100 text-amber-800"
                      : "bg-emerald-100 text-emerald-800"
                }
                onClick={() => setBandFilter(toggle(bandFilter, band))}
              >
                {band}
              </FilterChip>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-medium text-muted-foreground">Method</span>
            {ALL_METHODS.map(method => (
              <FilterChip
                key={method}
                active={methodFilter.has(method)}
                activeClass="bg-primary text-primary-foreground"
                onClick={() => setMethodFilter(toggle(methodFilter, method))}
              >
                {method}
              </FilterChip>
            ))}
          </div>

          {hasFilters && (
            <button
              onClick={clearFilters}
              className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
            >
              Clear filters
            </button>
          )}
        </div>

        {/* Table / Empty state */}
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <p className="text-muted-foreground">No payments match your filters.</p>
            <Button variant="outline" size="sm" className="mt-3" onClick={clearFilters}>
              Clear filters
            </Button>
          </div>
        ) : (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Scenario</TableHead>
                  <TableHead>Sender Name</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Method</TableHead>
                  <TableHead>AI Recommendation</TableHead>
                  <TableHead>Confidence</TableHead>
                  <TableHead>Age</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map(({ payment, rec }) => {
                  const band = rec ? getBand(rec.confidence_score) : null
                  return (
                    <TableRow
                      key={payment.payment_id}
                      className="cursor-pointer"
                      onClick={() => router.push(`/payments/${payment.payment_id}`)}
                    >
                      {/* Scenario */}
                      <TableCell>
                        {rec ? (
                          <span
                            className={cn(
                              "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium",
                              SCENARIO_COLOR[rec.scenario_route],
                            )}
                          >
                            {SCENARIO_LABEL[rec.scenario_route]}
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </TableCell>

                      {/* Sender */}
                      <TableCell className="font-medium">{payment.sender_name}</TableCell>

                      {/* Amount */}
                      <TableCell>{formatUSD(payment.amount)}</TableCell>

                      {/* Method */}
                      <TableCell>{payment.payment_method}</TableCell>

                      {/* AI Recommendation */}
                      <TableCell>
                        {rec ? (
                          <Badge
                            variant={
                              rec.recommendation === "apply"
                                ? "success"
                                : rec.recommendation === "hold"
                                  ? "warning"
                                  : "destructive"
                            }
                          >
                            {rec.recommendation.toUpperCase()}
                          </Badge>
                        ) : (
                          <Badge variant="warning">FAILED</Badge>
                        )}
                      </TableCell>

                      {/* Confidence */}
                      <TableCell>
                        {rec && band ? (
                          <Badge
                            variant={
                              band === "Low"
                                ? "destructive"
                                : band === "Medium"
                                  ? "warning"
                                  : "success"
                            }
                          >
                            {band} · {rec.confidence_score}
                          </Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </TableCell>

                      {/* Age */}
                      <TableCell className="text-xs text-muted-foreground">
                        {formatAge(payment.created_timestamp)}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </div>
  )
}
