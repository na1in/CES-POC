import { cn } from "@/lib/utils"

function Skeleton({ className, style, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md", className)}
      style={{ background: "var(--pw-surface-elevated)", ...style }}
      {...props}
    />
  )
}

export { Skeleton }
