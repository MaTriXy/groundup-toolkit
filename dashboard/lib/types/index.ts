export type ServiceStatus = "active" | "inactive" | "degraded"

export type ServiceCategory =
  | "Deal Sourcing"
  | "Portfolio Monitoring"
  | "Outreach"
  | "Scheduling"
  | "Content & Comms"
  | "Internal Ops"
  | "Alerts & Notifications"

export interface Service {
  id: string
  name: string
  description: string
  category: ServiceCategory
  icon: string
  status: ServiceStatus
  lastRun: string
  canToggle: boolean
  enabledForUser?: boolean
}

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
  serviceContext?: string
}

export interface TeamMember {
  id: string
  name: string
  avatar?: string
}

export interface ActivityEntry {
  id: string
  serviceName: string
  action: string
  triggeredBy: string
  timestamp: string
}
