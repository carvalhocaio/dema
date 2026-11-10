"use client"

import { useEffect, useState } from "react"

import { apiUrl } from "@/lib/api"
import type { Replay } from "@/lib/replay"

export type ReplayData =
  | { status: "idle" | "loading" | "error"; replay: null }
  | { status: "ready"; replay: Replay }

type Loaded = { round: number; replay: Replay | null }

export function useReplayData(round: number, wanted: boolean): ReplayData {
  const [loaded, setLoaded] = useState<Loaded | null>(null)

  useEffect(() => {
    if (!wanted) return
    const controller = new AbortController()
    const load = async () => {
      try {
        const response = await fetch(apiUrl(`/rounds/${round}/replay`), {
          signal: controller.signal,
          cache: "no-store",
        })
        if (!response.ok) throw new Error(`replay: HTTP ${response.status}`)
        setLoaded({ round, replay: (await response.json()) as Replay })
      } catch {
        if (!controller.signal.aborted) setLoaded({ round, replay: null })
      }
    }
    void load()
    return () => controller.abort()
  }, [round, wanted])

  if (!wanted) return { status: "idle", replay: null }
  if (!loaded || loaded.round !== round)
    return { status: "loading", replay: null }
  if (!loaded.replay) return { status: "error", replay: null }
  return { status: "ready", replay: loaded.replay }
}
