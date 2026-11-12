"use client"

import { useCallback, useState, useSyncExternalStore } from "react"

import {
  initialRound,
  parseRoundParam,
  ROUND_PARAM,
  type Round,
} from "@/lib/rounds"

function subscribe(onChange: () => void): () => void {
  window.addEventListener("popstate", onChange)
  return () => window.removeEventListener("popstate", onChange)
}

function readSearch(): string {
  return window.location.search
}

function serverSearch(): string {
  return ""
}

export type RoundSelection = {
  selected: Round | undefined
  select: (round: number) => void
  follow: () => void
}

export function useSelectedRound(rounds: readonly Round[]): RoundSelection {
  const search = useSyncExternalStore(subscribe, readSearch, serverSearch)
  const [chosen, setChosen] = useState<number | null>(null)

  const select = useCallback((round: number) => {
    setChosen(round)
    const url = new URL(window.location.href)
    url.searchParams.set(ROUND_PARAM, String(round))
    window.history.replaceState(window.history.state, "", url)
  }, [])

  const follow = useCallback(() => {
    setChosen(null)
    const url = new URL(window.location.href)
    url.searchParams.delete(ROUND_PARAM)
    window.history.replaceState(window.history.state, "", url)
    window.dispatchEvent(new PopStateEvent("popstate"))
  }, [])

  return {
    selected: initialRound(rounds, chosen ?? parseRoundParam(search)),
    select,
    follow,
  }
}
