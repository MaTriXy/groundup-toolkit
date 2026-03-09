import { NextRequest, NextResponse } from "next/server"
import { auth } from "@/lib/auth"
import { rateLimit } from "@/lib/rate-limit"
import { execSync } from "child_process"

const limiter = rateLimit({ interval: 60_000, limit: 30 })

const DB_PATH = "/root/.openclaw/data/founder-scout.db"

interface ScoutPerson {
  id: number
  name: string
  linkedin_url: string | null
  headline: string | null
  source: string | null
  signal_tier: string | null
  priority_score: number
  last_signal: string | null
  last_scanned: string | null
  added_at: string
  status: string
  hubspot_contact_id: string | null
}

interface ScoutStats {
  active: number
  high: number
  medium: number
  low: number
  total_signals: number
  total_scans: number
  avg_score: number
}

interface ScoutSignal {
  id: number
  person_name: string
  linkedin_url: string | null
  signal_type: string
  signal_tier: string
  description: string | null
  detected_at: string
  priority_score: number
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

function queryDbScalar(sql: string): string {
  try {
    const script = `import sqlite3,sys;c=sqlite3.connect("${DB_PATH}");r=c.execute(sys.argv[1]).fetchone();print(r[0] if r else 0)`
    return execSync(
      `python3 -c ${JSON.stringify(script)} ${JSON.stringify(normSql(sql))}`,
      { encoding: "utf-8", timeout: 5000 }
    ).trim()
  } catch {
    return "0"
  }
}

export async function GET(req: NextRequest) {
  const { ok } = limiter.check(req)
  if (!ok) return NextResponse.json({ error: "Too Many Requests" }, { status: 429 })

  const session = await auth()
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 })

  // Get watchlist (active people, sorted by score)
  const peopleJson = queryDb(
    `SELECT id, name, linkedin_url, headline, source, signal_tier, priority_score,
            last_signal, last_scanned, added_at, status, hubspot_contact_id
     FROM tracked_people WHERE status = 'active'
     ORDER BY priority_score DESC, added_at DESC LIMIT 50`
  )
  let people: ScoutPerson[] = []
  try {
    people = JSON.parse(peopleJson || "[]")
  } catch { /* empty */ }

  // Get recent signals (last 14 days)
  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - 14)
  const signalsJson = queryDb(
    `SELECT sh.id, tp.name as person_name, tp.linkedin_url, tp.priority_score,
            sh.signal_type, sh.signal_tier, sh.description, sh.detected_at
     FROM signal_history sh
     JOIN tracked_people tp ON sh.person_id = tp.id
     WHERE sh.detected_at >= '${cutoff.toISOString()}'
     ORDER BY sh.detected_at DESC LIMIT 50`
  )
  let signals: ScoutSignal[] = []
  try {
    signals = JSON.parse(signalsJson || "[]")
  } catch { /* empty */ }

  // Get stats
  const active = parseInt(queryDbScalar("SELECT COUNT(*) FROM tracked_people WHERE status = 'active'")) || 0
  const high = parseInt(queryDbScalar("SELECT COUNT(*) FROM tracked_people WHERE status = 'active' AND signal_tier = 'high'")) || 0
  const medium = parseInt(queryDbScalar("SELECT COUNT(*) FROM tracked_people WHERE status = 'active' AND signal_tier = 'medium'")) || 0
  const low = parseInt(queryDbScalar("SELECT COUNT(*) FROM tracked_people WHERE status = 'active' AND signal_tier = 'low'")) || 0
  const totalSignals = parseInt(queryDbScalar("SELECT COUNT(*) FROM signal_history")) || 0
  const totalScans = parseInt(queryDbScalar("SELECT COUNT(*) FROM scan_log")) || 0
  const avgScore = parseInt(queryDbScalar("SELECT COALESCE(ROUND(AVG(priority_score)), 0) FROM tracked_people WHERE status = 'active'")) || 0

  const stats: ScoutStats = { active, high, medium, low, total_signals: totalSignals, total_scans: totalScans, avg_score: avgScore }

  // Last scan info
  const lastScanJson = queryDb(
    `SELECT scan_type, started_at, people_found, signals_detected
     FROM scan_log ORDER BY started_at DESC LIMIT 1`
  )
  let lastScan = null
  try {
    const parsed = JSON.parse(lastScanJson || "[]")
    lastScan = parsed[0] || null
  } catch { /* empty */ }

  return NextResponse.json({ people, signals, stats, lastScan })
}
