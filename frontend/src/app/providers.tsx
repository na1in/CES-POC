"use client"

import { SWRConfig } from "swr"
import { ToastProvider } from "@/contexts/ToastContext"
import { fetcher } from "@/lib/api"

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SWRConfig value={{ fetcher, revalidateOnFocus: false }}>
      <ToastProvider>{children}</ToastProvider>
    </SWRConfig>
  )
}
