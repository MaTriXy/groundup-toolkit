"use client"

import { motion } from "framer-motion"
import { PieChart } from "lucide-react"
import { useDealSources } from "@/lib/hooks/useDashboardData"
import { cn } from "@/lib/utils"

const sourceColors: Record<string, string> = {
  "Email Forward": "bg-blue-500",
  "Founder Scout": "bg-violet-500",
  "Manual": "bg-slate-400",
  "Referral": "bg-emerald-500",
  "Other": "bg-amber-500",
}

export function DealSources() {
  const { data, isLoading } = useDealSources()

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border bg-card/50 backdrop-blur-sm p-5">
        <div className="flex items-center gap-2 mb-4">
          <PieChart className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold">Deal Sources</h2>
        </div>
        <div className="h-24 flex items-center justify-center text-xs text-muted-foreground">Loading...</div>
      </div>
    )
  }

  const sources = data?.sources || []
  const total = data?.total || 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.15 }}
      className="rounded-xl border border-border bg-card/50 backdrop-blur-sm p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <PieChart className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold">Deal Sources</h2>
        </div>
        <span className="text-xs text-muted-foreground">Last 90 days</span>
      </div>

      {/* Horizontal stacked bar */}
      {total > 0 && (
        <div className="flex h-5 rounded-full overflow-hidden mb-4">
          {sources.map((s) => (
            <div
              key={s.name}
              className={cn("transition-all", sourceColors[s.name] || "bg-slate-500")}
              style={{ width: `${(s.count / total) * 100}%` }}
            />
          ))}
        </div>
      )}

      {total === 0 && (
        <div className="text-center py-4 text-xs text-muted-foreground">
          No deals in the last 90 days.
        </div>
      )}

      {/* Legend */}
      <div className="space-y-1.5">
        {sources.map((s) => (
          <div key={s.name} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className={cn("h-2.5 w-2.5 rounded-sm", sourceColors[s.name] || "bg-slate-500")} />
              <span className="text-xs text-muted-foreground">{s.name}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium">{s.count}</span>
              <span className="text-[10px] text-muted-foreground w-8 text-right">
                {total > 0 ? Math.round((s.count / total) * 100) : 0}%
              </span>
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  )
}
