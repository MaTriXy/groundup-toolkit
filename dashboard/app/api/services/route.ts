import { NextRequest, NextResponse } from "next/server"
import { defaultServices } from "@/lib/data/services"

export async function GET() {
  return NextResponse.json(defaultServices)
}

export async function PATCH(req: NextRequest) {
  const body = await req.json()
  const { serviceId, enabled } = body

  const service = defaultServices.find((s) => s.id === serviceId)
  if (!service) {
    return NextResponse.json({ error: "Service not found" }, { status: 404 })
  }
  if (!service.canToggle) {
    return NextResponse.json({ error: "Service cannot be toggled" }, { status: 400 })
  }

  service.enabledForUser = enabled
  service.status = enabled ? "active" : "inactive"

  return NextResponse.json(service)
}
