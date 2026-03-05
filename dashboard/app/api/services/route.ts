import { NextRequest, NextResponse } from "next/server"
import { auth } from "@/lib/auth"
import { rateLimit } from "@/lib/rate-limit"
import { defaultServices } from "@/lib/data/services"

// Security: rate limit services API to 60 requests per minute per IP
const limiter = rateLimit({ interval: 60_000, limit: 60 })

export async function GET(req: NextRequest) {
  // Security: rate limiting
  const { ok } = limiter.check(req)
  if (!ok) {
    return NextResponse.json({ error: "Too Many Requests" }, { status: 429 })
  }

  // Security: explicit auth check (defense-in-depth beyond middleware)
  const session = await auth()
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  return NextResponse.json(defaultServices)
}

export async function PATCH(req: NextRequest) {
  // Security: rate limiting
  const { ok: rl } = limiter.check(req)
  if (!rl) {
    return NextResponse.json({ error: "Too Many Requests" }, { status: 429 })
  }

  // Security: explicit auth check (defense-in-depth beyond middleware)
  const session = await auth()
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  // Security: validate input
  let body
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: "Bad Request" }, { status: 400 })
  }

  const { serviceId, enabled } = body
  if (typeof serviceId !== "string" || typeof enabled !== "boolean") {
    return NextResponse.json({ error: "Invalid input" }, { status: 400 })
  }

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
