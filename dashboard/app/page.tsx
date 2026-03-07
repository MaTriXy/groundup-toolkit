"use client"

import { AppShell } from "@/components/layout/AppShell"
import { Greeting } from "@/components/dashboard/Greeting"
import { StatsBar } from "@/components/dashboard/StatsBar"
import { PipelineFunnel } from "@/components/dashboard/PipelineFunnel"
import { QuickActions } from "@/components/dashboard/QuickActions"
import { DealFlowChart } from "@/components/dashboard/DealFlowChart"
import { TeamHeatmap } from "@/components/dashboard/TeamHeatmap"
import { DealMovements } from "@/components/dashboard/DealMovements"
import { MeetingPrep } from "@/components/dashboard/MeetingPrep"
import { SignalFeed } from "@/components/dashboard/SignalFeed"
import { DealSources } from "@/components/dashboard/DealSources"
import { ResponseTime } from "@/components/dashboard/ResponseTime"
import { SignalConversion } from "@/components/dashboard/SignalConversion"
import { ServiceGrid } from "@/components/services/ServiceGrid"
import { ActivityFeed } from "@/components/dashboard/ActivityFeed"
import { KeyboardShortcuts } from "@/components/dashboard/KeyboardShortcuts"

export default function DashboardPage() {
  return (
    <AppShell>
      <KeyboardShortcuts />
      <Greeting />
      <StatsBar />
      <QuickActions />
      <PipelineFunnel />

      <div className="grid gap-6 lg:grid-cols-2 mb-8">
        <DealFlowChart />
        <TeamHeatmap />
      </div>

      <div className="grid gap-6 lg:grid-cols-2 mb-8">
        <DealMovements />
        <MeetingPrep />
      </div>

      <div className="grid gap-6 lg:grid-cols-3 mb-8">
        <DealSources />
        <ResponseTime />
        <SignalConversion />
      </div>

      <div className="mb-8">
        <SignalFeed />
      </div>

      <ServiceGrid />
      <ActivityFeed />
    </AppShell>
  )
}
