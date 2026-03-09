"use client"

import { motion } from "framer-motion"
import { ArrowRight, AlertTriangle, ExternalLink } from "lucide-react"
import { useStageMovements } from "@/lib/hooks/useDashboardData"
import { cn } from "@/lib/utils"

function timeAgo(ts: string | null): string {
  if (!ts) return ""
  const diff = Date.now() - new Date(ts).getTime()
  const hours = Math.floor(diff / (1000 * 60 * 60))
  if (hours < 1) return "just now"
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

function DealLink({ id, name }: { id: string; name: string }) {
  return (
    <a
      href={`https://app.hubspot.com/contacts/49139382/deal/${id}`}
      target="_blank"
      rel="noopener noreferrer"
      className="text-xs font-medium hover:text-primary transition-colors inline-flex items-center gap-1"
    >
      {name}
      <ExternalLink className="h-2.5 w-2.5 opacity-50" />
    </a>
  )
}

export function DealMovements() {
  const { data, isLoading } = useStageMovements()

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border bg-card/50 backdrop-blur-sm p-5">
        <div className="flex items-center gap-2 mb-4">
          <ArrowRight className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold">Deal Activity</h2>
        </div>
        <div className="h-32 flex items-center justify-center text-xs text-muted-foreground">Loading...</div>
      </div>
    )
  }

  const movements = data?.movements || []
  const staleDeals = data?.staleDeals || []

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.05 }}
      className="rounded-xl border border-border bg-card/50 backdrop-blur-sm p-5"
    >
      {/* Recent movements */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <ArrowRight className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold">Recent Deal Activity</h2>
        </div>
        <span className="text-xs text-muted-foreground">Last 7 days</span>
      </div>

      {movements.length === 0 ? (
        <div className="text-center py-6 text-xs text-muted-foreground">
          No deals moved stages this week. Activity appears here when deals advance in the pipeline.
        </div>
      ) : (
        <div className="space-y-1.5 max-h-48 overflow-y-auto">
          {movements.map((m) => (
            <div key={m.id} className="flex items-center justify-between gap-2 py-1.5 px-2 rounded-lg hover:bg-muted/30 transition-colors">
              <div className="flex items-center gap-2 min-w-0">
                <DealLink id={m.id} name={m.name} />
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary shrink-0">{m.stage}</span>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {m.owner && <span className="text-[10px] text-muted-foreground">{m.owner}</span>}
                <span className="text-[9px] text-muted-foreground">{timeAgo(m.lastModified)}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Stale deals */}
      {staleDeals.length > 0 && (
        <div className="mt-4 pt-3 border-t border-border">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
            <h3 className="text-xs font-semibold text-amber-400">Needs Attention</h3>
            <span className="text-[10px] text-muted-foreground">({staleDeals.length} stale)</span>
          </div>
          <div className="space-y-1">
            {staleDeals.slice(0, 5).map((d) => (
              <div key={d.id} className="flex items-center justify-between gap-2 py-1 px-2 rounded-lg bg-amber-500/5">
                <div className="flex items-center gap-2 min-w-0">
                  <DealLink id={d.id} name={d.name} />
                  <span className="text-[10px] text-muted-foreground">{d.stage}</span>
                </div>
                <span className={cn(
                  "text-[10px] font-medium shrink-0",
                  d.daysStale > 60 ? "text-red-400" : "text-amber-400"
                )}>
                  {d.daysStale}d stale
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  )
}
