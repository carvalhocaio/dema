"use client"

import { useCallback, useEffect, useState } from "react"

import { apiUrl } from "@/lib/api"
import type { CurrentRun } from "@/lib/runs"

export type CurrentRunState = {
  current: CurrentRun | null
  refresh: () => void
}

export function useCurrentRun(): CurrentRunState {
  const [current, setCurrent] = useState<CurrentRun | null>(null)
  const [version, setVersion] = useState(0)
  const refresh = useCallback(() => setVersion((value) => value + 1), [])

  useEffect(() => {
    const controller = new AbortController()
    const load = async () => {
      try {
        const response = await fetch(apiUrl("/runs/current"), {
          signal: controller.signal,
          cache: "no-store",
        })
        if (response.ok) setCurrent((await response.json()) as CurrentRun)
      } catch {
        return
      }
    }
    void load()
    return () => controller.abort()
  }, [version])

  return { current, refresh }
}
