"use client"

import { Switch } from "@/components/ui/switch"
import { useServicesStore } from "@/lib/store/servicesStore"

export function ServiceToggle({
  serviceId,
  enabled,
  canToggle,
}: {
  serviceId: string
  enabled: boolean
  canToggle: boolean
}) {
  const toggleService = useServicesStore((s) => s.toggleService)

  if (!canToggle) return null

  return (
    <Switch
      checked={enabled}
      onCheckedChange={(checked) => {
        toggleService(serviceId, checked)
        fetch("/api/services", {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ serviceId, enabled: checked }),
        })
      }}
      className="data-[state=checked]:bg-primary"
    />
  )
}
