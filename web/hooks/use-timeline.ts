"use client"

import { useEffect, useRef, useState } from "react"

import { apiUrl } from "@/lib/api"
import type { Timeline } from "@/lib/timeline"

export const TIMELINE_THROTTLE_MS = 2_000

export function useTimeline(
  round: number,
  revision: number | null
): Timeline | null {
  const [timeline, setTimeline] = useState<Timeline | null>(null)
  const controller = useRef(new AbortController())
  const lastFetch = useRef(-Infinity)

  useEffect(() => {
    const current = new AbortController()
    controller.current = current
    return () => current.abort()
  }, [round])

  useEffect(() => {
    const load = async () => {
      lastFetch.current = Date.now()
      try {
        const response = await fetch(apiUrl(`/rounds/${round}/timeline`), {
          signal: controller.current.signal,
          cache: "no-store",
        })
        if (response.ok) setTimeline((await response.json()) as Timeline)
      } catch {
        return
      }
    }
    const wait = Math.max(
      0,
      lastFetch.current + TIMELINE_THROTTLE_MS - Date.now()
    )
    const timer = setTimeout(() => void load(), wait)
    return () => clearTimeout(timer)
  }, [round, revision])

  return timeline
}
