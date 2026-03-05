"use client"

import { useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { useServicesStore } from "@/lib/store/servicesStore"
import { ServiceCard } from "./ServiceCard"
import { ServiceCategory, Service } from "@/lib/types"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const categories: (ServiceCategory | "all")[] = [
  "all",
  "Deal Sourcing",
  "Portfolio Monitoring",
  "Outreach",
  "Scheduling",
  "Content & Comms",
  "Internal Ops",
  "Alerts & Notifications",
]

export function ServiceGrid() {
  const { setServices, filteredServices, filterCategory, setFilterCategory } = useServicesStore()

  const { data } = useQuery<Service[]>({
    queryKey: ["services"],
    queryFn: () => fetch("/api/services").then((r) => r.json()),
  })

  useEffect(() => {
    if (data) setServices(data)
  }, [data, setServices])

  const services = filteredServices()

  return (
    <div>
      {/* Category filters */}
      <div className="flex flex-wrap gap-2 mb-6">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setFilterCategory(cat)}
            className={cn(
              "rounded-lg px-3 py-1.5 text-xs font-medium transition-all duration-150",
              filterCategory === cat
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-muted text-muted-foreground hover:text-foreground hover:bg-muted/80"
            )}
          >
            {cat === "all" ? "All Services" : cat}
          </button>
        ))}
      </div>

      {/* Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {services.map((service, i) => (
          <ServiceCard key={service.id} service={service} index={i} />
        ))}
      </div>

      {services.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
          <p className="text-sm">No services found</p>
        </div>
      )}
    </div>
  )
}
