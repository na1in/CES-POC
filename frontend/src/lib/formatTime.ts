/**
 * Relative age of an ISO timestamp, e.g. "12m ago", "5h ago", "3d ago".
 *
 * Single source of truth for relative timestamps. Resolves to minutes under
 * the hour so a case opened moments ago never reads as a misleading "0h ago".
 */
export function formatAge(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const minutes = Math.floor(diff / 60_000)
  const hours = Math.floor(diff / 3_600_000)
  const days = Math.floor(diff / 86_400_000)
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  return `${days}d ago`
}
