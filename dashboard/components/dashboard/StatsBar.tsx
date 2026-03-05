"use client"

import { motion } from "framer-motion"
import { Activity, Zap, ToggleRight, UserCheck } from "lucide-react"
import { useServicesStore } from "@/lib/store/servicesStore"

export function StatsBar() {
  const services = useServicesStore((s) => s.services)
  const total = services.length
  const active = services.filter((s) => s.status === "active").length
  const optedIn = services.filter((s) => s.enabledForUser).length

  const stats = [
    {
      label: "Christina Status",
      value: "Online",
      icon: Zap,
      color: "text-green-500",
      bg: "bg-green-500/10",
    },
    {
      label: "Total Services",
      value: total.toString(),
      icon: Activity,
      color: "text-primary",
      bg: "bg-primary/10",
    },
    {
      label: "Active",
      value: active.toString(),
      icon: ToggleRight,
      color: "text-emerald-500",
      bg: "bg-emerald-500/10",
    },
    {
      label: "Opted In",
      value: optedIn.toString(),
      icon: UserCheck,
      color: "text-amber-500",
      bg: "bg-amber-500/10",
    },
  ]

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-8">
      {stats.map((stat, i) => (
        <motion.div
          key={stat.label}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: i * 0.05 }}
          className="flex items-center gap-4 rounded-xl border border-border bg-card/50 backdrop-blur-sm p-4"
        >
          <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${stat.bg}`}>
            <stat.icon className={`h-5 w-5 ${stat.color}`} />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{stat.label}</p>
            <p className={`text-xl font-semibold tracking-tight ${stat.label === "Christina Status" ? stat.color : ""}`}>
              {stat.value}
            </p>
          </div>
        </motion.div>
      ))}
    </div>
  )
}
