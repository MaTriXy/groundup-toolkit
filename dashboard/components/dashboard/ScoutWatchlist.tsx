"use client"

import { motion } from "framer-motion"
import { Search, ExternalLink, Building2, TrendingUp, Clock } from "lucide-react"
import { useScout } from "@/lib/hooks/useDashboardData"
import { cn } from "@/lib/utils"

const tierConfig = {
  high: { label: "High", color: "text-red-400 bg-red-500/15 border-red-500/20" },
  medium: { label: "Med", color: "text-amber-400 bg-amber-500/15 border-amber-500/20" },
  low: { label: "Low", color: "text-blue-400 bg-blue-500/15 border-blue-500/20" },
}

function scoreColor(score: number): string {
  if (score >= 70) return "text-green-400"
  if (score >= 40) return "text-amber-400"
  return "text-zinc-500"
}

function scoreBg(score: number): string {
  if (score >= 70) return "bg-green-500/15 border-green-500/20"
  if (score >= 40) return "bg-amber-500/15 border-amber-500/20"
  return "bg-zinc-500/10 border-zinc-500/20"
}

function timeAgo(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime()
  const hours = Math.floor(diff / (1000 * 60 * 60))
  if (hours < 1) return "just now"
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export function ScoutWatchlist() {
  const { data, isLoading } = useScout()

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border bg-card/50 backdrop-blur-sm p-5">
        <div className="flex items-center gap-2 mb-4">
          <Search className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold">Founder Scout</h2>
        </div>
        <div className="h-40 flex items-center justify-center text-xs text-muted-foreground">Loading scout data...</div>
      </div>
    )
  }

  const people = data?.people || []
  const stats = data?.stats || { active: 0, high: 0, medium: 0, low: 0, avg_score: 0, total_scans: 0, total_signals: 0 }
  const lastScan = data?.lastScan
  const signals = data?.signals || []

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.15 }}
      className="rounded-xl border border-border bg-card/50 backdrop-blur-sm p-5"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Search className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold">Founder Scout</h2>
        </div>
        <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
          {lastScan && (
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {timeAgo(lastScan.started_at)}
            </span>
          )}
          <span>{stats.active} tracked</span>
        </div>
      </div>

      {/* Stats bar */}
      <div className="flex gap-3 mb-4">
        <div className="flex-1 rounded-lg border border-border bg-muted/20 px-3 py-2 text-center">
          <div className="text-lg font-bold">{stats.active}</div>
          <div className="text-[10px] text-muted-foreground">Active</div>
        </div>
        <div className="flex-1 rounded-lg border border-red-500/20 bg-red-500/5 px-3 py-2 text-center">
          <div className="text-lg font-bold text-red-400">{stats.high}</div>
          <div className="text-[10px] text-muted-foreground">High</div>
        </div>
        <div className="flex-1 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-center">
          <div className="text-lg font-bold text-amber-400">{stats.medium}</div>
          <div className="text-[10px] text-muted-foreground">Medium</div>
        </div>
        <div className="flex-1 rounded-lg border border-border bg-muted/20 px-3 py-2 text-center">
          <div className="text-lg font-bold">{stats.avg_score}</div>
          <div className="text-[10px] text-muted-foreground">Avg Score</div>
        </div>
      </div>

      {/* Watchlist */}
      {people.length === 0 ? (
        <div className="text-center py-8 text-xs text-muted-foreground">
          No founders tracked yet. Scout runs daily at 7 AM UTC.
        </div>
      ) : (
        <div className="space-y-1.5 max-h-[420px] overflow-y-auto">
          {people.map((person) => {
            const tier = person.signal_tier as keyof typeof tierConfig
            const config = tierConfig[tier] || tierConfig.low

            const Wrapper = person.linkedin_url ? "a" : "div"
            const wrapperProps = person.linkedin_url
              ? { href: person.linkedin_url, target: "_blank", rel: "noopener noreferrer" }
              : {}

            return (
              <Wrapper
                key={person.id}
                {...wrapperProps}
                className={cn(
                  "flex items-start gap-3 p-2.5 rounded-lg hover:bg-muted/30 transition-colors group no-underline",
                  person.linkedin_url && "cursor-pointer"
                )}
              >
                {/* Score badge */}
                <div className={cn(
                  "flex h-8 w-8 shrink-0 items-center justify-center rounded-md border text-xs font-bold",
                  scoreBg(person.priority_score),
                  scoreColor(person.priority_score)
                )}>
                  {person.priority_score}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium truncate">{person.name}</span>
                    {person.signal_tier && (
                      <span className={cn("text-[9px] px-1.5 py-0.5 rounded border font-medium", config.color)}>
                        {config.label}
                      </span>
                    )}
                    {person.hubspot_contact_id && (
                      <Building2 className="h-3 w-3 text-orange-400" />
                    )}
                  </div>
                  {person.headline && (
                    <p className="text-[10px] text-muted-foreground mt-0.5 line-clamp-1">{person.headline}</p>
                  )}
                  {person.last_signal && !person.headline && (
                    <p className="text-[10px] text-muted-foreground mt-0.5 line-clamp-1">{person.last_signal}</p>
                  )}
                  <div className="flex items-center gap-2 mt-1">
                    {person.source && (
                      <span className="text-[9px] text-muted-foreground/70">{person.source}</span>
                    )}
                    {person.added_at && (
                      <span className="text-[9px] text-muted-foreground/50">{timeAgo(person.added_at)}</span>
                    )}
                  </div>
                </div>

                {/* LinkedIn icon */}
                {person.linkedin_url && (
                  <ExternalLink className="h-3.5 w-3.5 text-muted-foreground group-hover:text-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0 mt-1" />
                )}
              </Wrapper>
            )
          })}
        </div>
      )}

      {/* Recent signals */}
      {signals.length > 0 && (
        <div className="mt-4 pt-4 border-t border-border">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="h-3 w-3 text-muted-foreground" />
            <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Recent Signals</span>
          </div>
          <div className="space-y-1.5 max-h-32 overflow-y-auto">
            {signals.slice(0, 5).map((signal) => (
              <div key={signal.id} className="flex items-center gap-2 text-[10px]">
                <span className={cn(
                  "w-1.5 h-1.5 rounded-full shrink-0",
                  signal.signal_tier === "high" ? "bg-red-400" :
                  signal.signal_tier === "medium" ? "bg-amber-400" : "bg-blue-400"
                )} />
                <span className="font-medium truncate">{signal.person_name}</span>
                <span className="text-muted-foreground truncate flex-1">{signal.description?.slice(0, 60)}</span>
                <span className="text-muted-foreground/50 shrink-0">{timeAgo(signal.detected_at)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  )
}
