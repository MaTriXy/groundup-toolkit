/**
 * Simple in-memory rate limiter for API routes.
 *
 * Usage:
 *   const limiter = rateLimit({ interval: 60_000, limit: 30 })
 *   export async function POST(req) {
 *     const { ok } = limiter.check(req)
 *     if (!ok) return new Response("Too Many Requests", { status: 429 })
 *     ...
 *   }
 */

interface RateLimitOptions {
  interval: number // Window in milliseconds
  limit: number    // Max requests per window per IP
}

interface TokenBucket {
  count: number
  resetAt: number
}

const buckets = new Map<string, TokenBucket>()

// Clean up stale entries every 5 minutes
setInterval(() => {
  const now = Date.now()
  for (const [key, bucket] of buckets) {
    if (bucket.resetAt < now) {
      buckets.delete(key)
    }
  }
}, 5 * 60 * 1000)

export function rateLimit(options: RateLimitOptions) {
  return {
    check(req: Request): { ok: boolean; remaining: number } {
      const ip =
        req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
        req.headers.get("x-real-ip") ||
        "unknown"

      const now = Date.now()
      const key = ip
      const bucket = buckets.get(key)

      if (!bucket || bucket.resetAt < now) {
        buckets.set(key, { count: 1, resetAt: now + options.interval })
        return { ok: true, remaining: options.limit - 1 }
      }

      bucket.count++
      if (bucket.count > options.limit) {
        return { ok: false, remaining: 0 }
      }
      return { ok: true, remaining: options.limit - bucket.count }
    },
  }
}
