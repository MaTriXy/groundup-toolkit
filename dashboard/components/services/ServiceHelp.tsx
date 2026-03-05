"use client"

import { motion, AnimatePresence } from "framer-motion"
import { X, Terminal, Zap } from "lucide-react"
import { Service } from "@/lib/types"
import { getIcon } from "@/lib/icons"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { StatusBadge } from "@/components/layout/StatusBadge"
import { cn } from "@/lib/utils"

const categoryColors: Record<string, string> = {
  "Deal Sourcing": "bg-violet-500/15 text-violet-400 border-violet-500/20",
  "Portfolio Monitoring": "bg-blue-500/15 text-blue-400 border-blue-500/20",
  "Scheduling": "bg-amber-500/15 text-amber-400 border-amber-500/20",
  "Content & Comms": "bg-pink-500/15 text-pink-400 border-pink-500/20",
  "Internal Ops": "bg-slate-500/15 text-slate-400 border-slate-500/20",
}

export function ServiceHelp({
  service,
  onClose,
}: {
  service: Service | null
  onClose: () => void
}) {
  if (!service) return null

  const Icon = getIcon(service.icon)

  return (
    <AnimatePresence>
      {service && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", damping: 25, stiffness: 350 }}
            className="fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2 w-[90vw] max-w-lg max-h-[80vh] overflow-y-auto rounded-2xl border border-border bg-card/95 backdrop-blur-xl shadow-2xl"
          >
            {/* Header */}
            <div className="sticky top-0 z-10 flex items-start justify-between border-b border-border bg-card/95 backdrop-blur-xl p-5">
              <div className="flex items-center gap-3">
                <div className={cn(
                  "flex h-11 w-11 shrink-0 items-center justify-center rounded-xl",
                  service.status === "active" ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
                )}>
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-base font-semibold">{service.name}</h2>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge
                      variant="outline"
                      className={cn("text-[10px] px-1.5 py-0 border", categoryColors[service.category])}
                    >
                      {service.category}
                    </Badge>
                    <StatusBadge status={service.status} />
                  </div>
                </div>
              </div>
              <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8 -mt-1 -mr-1">
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* Content */}
            <div className="p-5 space-y-5">
              {/* Description */}
              <div>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {service.helpText}
                </p>
              </div>

              {/* Trigger */}
              <div className="flex items-start gap-3 rounded-lg border border-border bg-muted/30 p-3">
                <Zap className="h-4 w-4 text-amber-400 mt-0.5 shrink-0" />
                <div>
                  <p className="text-xs font-medium text-foreground mb-0.5">How it runs</p>
                  <p className="text-xs text-muted-foreground">{service.trigger}</p>
                </div>
              </div>

              {/* Commands */}
              {service.commands && service.commands.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <Terminal className="h-4 w-4 text-primary" />
                    <h3 className="text-sm font-medium">Commands & Usage</h3>
                  </div>
                  <div className="space-y-1.5">
                    {service.commands.map((cmd, i) => (
                      <div
                        key={i}
                        className="rounded-md bg-muted/40 border border-border/50 px-3 py-2"
                      >
                        <code className="text-xs text-foreground/90 font-mono">{cmd}</code>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Last run */}
              <div className="pt-2 border-t border-border">
                <p className="text-[10px] text-muted-foreground">
                  Schedule: {service.lastRun}
                </p>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
