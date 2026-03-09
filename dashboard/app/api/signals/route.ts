import { NextRequest, NextResponse } from "next/server"
import { auth } from "@/lib/auth"
import { rateLimit } from "@/lib/rate-limit"
import { execSync } from "child_process"

const limiter = rateLimit({ interval: 60_000, limit: 30 })

const DB_PATH = "/root/.openclaw/data/founder-scout.db"

interface Signal {
  id: string
  name: string
  company: string
  signal: string
  strength: "high" | "medium" | "low"
  timestamp: string
  source: string
}

function normSql(sql: string): string {
  return sql.replace(/\s+/g, " ").trim()
}

function queryDb(sql: string): string {
  try {
    const script = `import sqlite3,json,sys;c=sqlite3.connect("${DB_PATH}");c.row_factory=sqlite3.Row;rows=[dict(r) for r in c.execute(sys.argv[1]).fetchall()];print(json.dumps(rows))`
    return execSync(
      `python3 -c ${JSON.stringify(script)} ${JSON.stringify(normSql(sql))}`,
      { encoding: "utf-8", timeout: 5000 }
    ).trim()
  } catch {
    return "[]"
  }
}

function extractCompany(text: string): string {
  const match = text?.match(/(?:at|of|@)\s+(?:a\s+)?([A-Z][A-Za-z0-9.]+(?:\s+[A-Z][A-Za-z0-9.]+)?)/i)
  if (match) return match[1].trim()
  if (/stealth/i.test(text || "")) return "Stealth"
  return ""
}

export async function GET(req: NextRequest) {
  const { ok } = limiter.check(req)
  if (!ok) return NextResponse.json({ error: "Too Many Requests" }, { status: 429 })

  const session = await auth()
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 })

  // Read signals from scout v2 SQLite DB
  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - 30)

  const rows = queryDb(
    `SELECT sh.id, tp.name, tp.headline, sh.signal_type, sh.signal_tier,
            sh.description, sh.detected_at, sh.source_url, tp.source
     FROM signal_history sh
     JOIN tracked_people tp ON sh.person_id = tp.id
     WHERE sh.detected_at >= '${cutoff.toISOString()}'
     ORDER BY sh.detected_at DESC LIMIT 20`
  )

  let dbSignals: Array<{
    id: number; name: string; headline: string | null
    signal_type: string; signal_tier: string; description: string | null
    detected_at: string; source_url: string | null; source: string | null
  }> = []
  try {
    dbSignals = JSON.parse(rows || "[]")
  } catch { /* empty */ }

  const signals: Signal[] = dbSignals.map((s) => ({
    id: String(s.id),
    name: s.name,
    company: extractCompany(s.description || s.headline || ""),
    signal: (s.description || s.headline || "").slice(0, 200),
    strength: (s.signal_tier === "high" ? "high" : s.signal_tier === "medium" ? "medium" : "low") as Signal["strength"],
    timestamp: s.detected_at,
    source: s.source?.includes("brave") ? "News" : "LinkedIn",
  }))

  // Deduplicate by name
  const byName = new Map<string, Signal>()
  for (const s of signals) {
    const existing = byName.get(s.name)
    if (!existing || s.timestamp > existing.timestamp) {
      byName.set(s.name, s)
    }
  }

  return NextResponse.json({
    signals: Array.from(byName.values())
      .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
      .slice(0, 20)
  })
}
