"use client"

import { useEffect, useState } from "react"

export function useTheme() {
  const [theme, setThemeState] = useState<"dark" | "light">("dark")

  useEffect(() => {
    const stored = localStorage.getItem("christina-theme") as "dark" | "light" | null
    const initial = stored ?? "dark"
    setThemeState(initial)
    document.documentElement.classList.toggle("dark", initial === "dark")
  }, [])

  const setTheme = (t: "dark" | "light") => {
    setThemeState(t)
    localStorage.setItem("christina-theme", t)
    document.documentElement.classList.toggle("dark", t === "dark")
  }

  const toggleTheme = () => setTheme(theme === "dark" ? "light" : "dark")

  return { theme, setTheme, toggleTheme }
}
