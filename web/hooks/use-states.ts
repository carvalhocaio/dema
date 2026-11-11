"use client"

import { useEffect, useRef, useState } from "react"

import { apiUrl } from "@/lib/api"
import type { States } from "@/lib/states"
import { TIMELINE_THROTTLE_MS } from "@/hooks/use-timeline"

export function useStates(
  round: number,
  revision: number | null
): States | null {
  const [states, setStates] = useState<States | null>(null)
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
        const response = await fetch(apiUrl(`/rounds/${round}/states`), {
          signal: controller.current.signal,
          cache: "no-store",
        })
        if (response.ok) setStates((await response.json()) as States)
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

  return states
}
