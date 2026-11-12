"use client"

import { useCallback, useEffect, useState } from "react"

import { apiUrl } from "@/lib/api"
import type { Round } from "@/lib/rounds"

export const ROUNDS_REFRESH_MS = 5_000

export type RoundsState = {
  status: "loading" | "ready" | "unavailable"
  rounds: Round[]
  refresh: () => void
}

type Loaded = Omit<RoundsState, "refresh">

function sameRounds(a: readonly Round[], b: readonly Round[]): boolean {
  return JSON.stringify(a) === JSON.stringify(b)
}

export function useRounds(): RoundsState {
  const [state, setState] = useState<Loaded>({ status: "loading", rounds: [] })
  const [version, setVersion] = useState(0)
  const refresh = useCallback(() => setVersion((current) => current + 1), [])

  useEffect(() => {
    const controller = new AbortController()
    const load = async () => {
      try {
        const response = await fetch(apiUrl("/rounds"), {
          signal: controller.signal,
          cache: "no-store",
        })
        if (!response.ok) throw new Error(`rounds: HTTP ${response.status}`)
        const rounds = (await response.json()) as Round[]
        setState((previous) =>
          previous.status === "ready" && sameRounds(previous.rounds, rounds)
            ? previous
            : { status: "ready", rounds }
        )
      } catch {
        if (controller.signal.aborted) return
        setState((previous) => ({ ...previous, status: "unavailable" }))
      }
    }
    void load()
    const timer = setInterval(() => void load(), ROUNDS_REFRESH_MS)
    return () => {
      controller.abort()
      clearInterval(timer)
    }
  }, [version])

  return { ...state, refresh }
}
