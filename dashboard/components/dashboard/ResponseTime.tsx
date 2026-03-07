"use client"

import { motion } from "framer-motion"
import { Timer } from "lucide-react"
import { useResponseTime } from "@/lib/hooks/useDashboardData"

export function ResponseTime() {
  const { data, isLoading } = useResponseTime()

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border bg-card/50 backdrop-blur-sm p-5">
        <div className="flex items-center gap-2 mb-4">
          <Timer className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold">Response Time</h2>
        </div>
        <div className="h-16 flex items-center justify-center text-xs text-muted-foreground">Loading...</div>
      </div>
    )
  }

  const avg = data?.avgMinutes || 0
  const median = data?.medianMinutes || 0
  const total = data?.totalProcessed || 0
  const trend = data?.trend || []

  // Simple sparkline from trend data
  const maxVal = Math.max(...trend, 1)
  const sparkPoints = trend.map((v: number, i: number) => {
    const x = (i / Math.max(trend.length - 1, 1)) * 80
    const y = 24 - (v / maxVal) * 20
    return `${x},${y}`
  }).join(" ")

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.2 }}
      className="rounded-xl border border-border bg-card/50 backdrop-blur-sm p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Timer className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold">Email Response Time</h2>
        </div>
        <span className="text-xs text-muted-foreground">Last 30 days</span>
      </div>

      {total === 0 ? (
        <div className="text-center py-4 text-xs text-muted-foreground">
          No emails processed recently. The automation runs every 2 hours.
        </div>
      ) : (
        <div className="flex items-end gap-6">
          <div>
            <div className="text-2xl font-bold tracking-tight">
              {avg > 0 ? `${avg}m` : "--"}
            </div>
            <div className="text-[10px] text-muted-foreground mt-0.5">avg processing</div>
          </div>
          <div>
            <div className="text-lg font-semibold text-muted-foreground">
              {median > 0 ? `${median}m` : "--"}
            </div>
            <div className="text-[10px] text-muted-foreground mt-0.5">median</div>
          </div>
          <div>
            <div className="text-lg font-semibold text-muted-foreground">{total}</div>
            <div className="text-[10px] text-muted-foreground mt-0.5">processed</div>
          </div>

          {/* Mini sparkline */}
          {trend.length > 1 && (
            <div className="ml-auto">
              <svg width="80" height="28" className="overflow-visible">
                <polyline
                  points={sparkPoints}
                  fill="none"
                  stroke="#818cf8"
                  strokeWidth="1.5"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
          )}
        </div>
      )}
    </motion.div>
  )
}
