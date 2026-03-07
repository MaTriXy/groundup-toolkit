"use client"

import { motion } from "framer-motion"
import { Calendar, Clock, Users } from "lucide-react"
import { useMeetings } from "@/lib/hooks/useDashboardData"

function formatTime(ts: string): string {
  const d = new Date(ts)
  return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: true, timeZone: "Asia/Jerusalem" })
}

function isToday(ts: string): boolean {
  const d = new Date(ts)
  const now = new Date()
  return d.toDateString() === now.toDateString()
}

export function MeetingPrep() {
  const { data, isLoading } = useMeetings()

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border bg-card/50 backdrop-blur-sm p-5">
        <div className="flex items-center gap-2 mb-4">
          <Calendar className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold">Upcoming Meetings</h2>
        </div>
        <div className="h-16 flex items-center justify-center text-xs text-muted-foreground">Loading...</div>
      </div>
    )
  }

  const meetings = data?.meetings || []

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.05 }}
      className="rounded-xl border border-border bg-card/50 backdrop-blur-sm p-5"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold">Upcoming Meetings</h2>
        </div>
        <span className="text-xs text-muted-foreground">{meetings.length} scheduled</span>
      </div>

      {meetings.length === 0 ? (
        <div className="text-center py-6 text-xs text-muted-foreground">
          No meetings coming up. Enjoy the focus time.
        </div>
      ) : (
        <div className="space-y-2">
          {meetings.map((m) => (
            <div
              key={m.id}
              className="flex items-start gap-3 p-2.5 rounded-lg hover:bg-muted/30 transition-colors"
            >
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-500/10">
                <Clock className="h-4 w-4 text-amber-400" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium truncate">{m.title}</span>
                  {isToday(m.start) && (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/20">Today</span>
                  )}
                </div>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-[10px] text-muted-foreground">{formatTime(m.start)}</span>
                  {m.company && (
                    <span className="text-[10px] text-primary">@ {m.company}</span>
                  )}
                  {m.attendees.length > 0 && (
                    <span className="text-[10px] text-muted-foreground flex items-center gap-0.5">
                      <Users className="h-2.5 w-2.5" />
                      {m.attendees.length}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  )
}
