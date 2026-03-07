"use client"

import { motion } from "framer-motion"
import { Target } from "lucide-react"
import { useSignalConversion } from "@/lib/hooks/useDashboardData"

export function SignalConversion() {
  const { data, isLoading } = useSignalConversion()

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border bg-card/50 backdrop-blur-sm p-5">
        <div className="flex items-center gap-2 mb-4">
          <Target className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold">Signal Conversion</h2>
        </div>
        <div className="h-16 flex items-center justify-center text-xs text-muted-foreground">Loading...</div>
      </div>
    )
  }

  const signals = data?.signalsDetected || 0
  const deals = data?.dealsCreated || 0
  const rate = data?.conversionRate || 0

  // Visual funnel bar
  const signalWidth = 100
  const dealWidth = signals > 0 ? Math.max((deals / signals) * 100, 8) : 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.25 }}
      className="rounded-xl border border-border bg-card/50 backdrop-blur-sm p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Target className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold">Signal-to-Deal</h2>
        </div>
        <span className="text-xs text-muted-foreground">Last 30 days</span>
      </div>

      {signals === 0 && deals === 0 ? (
        <div className="text-center py-4 text-xs text-muted-foreground">
          No scout signals this month. Founder Scout scans daily at 7 AM.
        </div>
      ) : (
        <>
          <div className="flex items-end gap-6 mb-4">
            <div>
              <div className="text-2xl font-bold tracking-tight">{rate}%</div>
              <div className="text-[10px] text-muted-foreground mt-0.5">conversion rate</div>
            </div>
            <div>
              <div className="text-lg font-semibold text-muted-foreground">{signals}</div>
              <div className="text-[10px] text-muted-foreground mt-0.5">signals</div>
            </div>
            <div>
              <div className="text-lg font-semibold text-emerald-400">{deals}</div>
              <div className="text-[10px] text-muted-foreground mt-0.5">deals</div>
            </div>
          </div>

          {/* Funnel visualization */}
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <div className="h-3 rounded-full bg-violet-500/30" style={{ width: `${signalWidth}%` }}>
                <div className="h-full rounded-full bg-violet-500" style={{ width: "100%" }} />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 rounded-full bg-emerald-500/30" style={{ width: `${dealWidth}%` }}>
                <div className="h-full rounded-full bg-emerald-500" style={{ width: "100%" }} />
              </div>
            </div>
          </div>
        </>
      )}
    </motion.div>
  )
}
