"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"

export function KeyboardShortcuts() {
  const router = useRouter()

  useEffect(() => {
    let gPressed = false
    let gTimer: ReturnType<typeof setTimeout> | null = null

    function handleKeyDown(e: KeyboardEvent) {
      // Don't trigger in inputs/textareas
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return
      if ((e.target as HTMLElement)?.isContentEditable) return

      const key = e.key.toLowerCase()

      // "g" chord: g+d = dashboard, g+s = settings
      if (key === "g" && !e.metaKey && !e.ctrlKey) {
        gPressed = true
        if (gTimer) clearTimeout(gTimer)
        gTimer = setTimeout(() => { gPressed = false }, 500)
        return
      }

      if (gPressed) {
        gPressed = false
        if (gTimer) clearTimeout(gTimer)
        if (key === "d") {
          e.preventDefault()
          router.push("/")
        } else if (key === "s") {
          e.preventDefault()
          router.push("/settings")
        }
        return
      }

      // "?" = show shortcuts hint (could be expanded)
      if (key === "?" && !e.metaKey && !e.ctrlKey) {
        // Toggle visibility of shortcuts hint could go here
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => {
      window.removeEventListener("keydown", handleKeyDown)
      if (gTimer) clearTimeout(gTimer)
    }
  }, [router])

  return null
}
