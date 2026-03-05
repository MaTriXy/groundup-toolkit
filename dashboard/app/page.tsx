"use client"

import { AppShell } from "@/components/layout/AppShell"
import { StatsBar } from "@/components/dashboard/StatsBar"
import { ServiceGrid } from "@/components/services/ServiceGrid"
import { ActivityFeed } from "@/components/dashboard/ActivityFeed"

export default function DashboardPage() {
  return (
    <AppShell>
      <StatsBar />
      <ServiceGrid />
      <ActivityFeed />
    </AppShell>
  )
}
