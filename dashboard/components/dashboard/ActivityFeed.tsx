"use client"

import { motion } from "framer-motion"
import { defaultActivities } from "@/lib/data/services"
import { Clock, Bot, Timer } from "lucide-react"

export function ActivityFeed() {
  return (
    <div className="mt-8">
      <h2 className="text-sm font-semibold mb-4 flex items-center gap-2">
        <Clock className="h-4 w-4 text-muted-foreground" />
        Recent Activity
      </h2>
      <div className="rounded-xl border border-border bg-card/50 backdrop-blur-sm divide-y divide-border">
        {defaultActivities.map((activity, i) => (
          <motion.div
            key={activity.id}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.2, delay: i * 0.03 }}
            className="flex items-start gap-3 px-4 py-3 hover:bg-muted/30 transition-colors"
          >
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-muted mt-0.5">
              {activity.triggeredBy === "Cron" ? (
                <Timer className="h-3.5 w-3.5 text-muted-foreground" />
              ) : (
                <Bot className="h-3.5 w-3.5 text-primary" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs leading-relaxed">
                <span className="font-medium text-foreground">{activity.serviceName}</span>
                <span className="text-muted-foreground"> — {activity.action}</span>
              </p>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-[10px] text-muted-foreground">{activity.triggeredBy}</span>
                <span className="text-[10px] text-muted-foreground/50">·</span>
                <span className="text-[10px] text-muted-foreground">{activity.timestamp}</span>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
