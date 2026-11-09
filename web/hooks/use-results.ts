"use client"

import { useEffect, useReducer } from "react"

import { apiUrl } from "@/lib/api"
import type { Results } from "@/lib/results"

export type Connection = "connecting" | "live" | "reconnecting" | "unavailable"
export type Setup = "unknown" | "ready" | "pending"

export type ResultsState = {
  results: Results | null
  connection: Connection
  setup: Setup
}

type Action =
  | { type: "results"; results: Results }
  | { type: "not-set-up" }
  | { type: "open" }
  | { type: "error"; retrying: boolean }

const initialState: ResultsState = {
  results: null,
  connection: "connecting",
  setup: "unknown",
}

function reducer(state: ResultsState, action: Action): ResultsState {
  switch (action.type) {
    case "results":
      return { results: action.results, connection: "live", setup: "ready" }
    case "not-set-up":
      return state.setup === "ready" ? state : { ...state, setup: "pending" }
    case "open":
      return { ...state, connection: "live" }
    case "error": {
      const wasLive = state.connection === "live"
      const connection =
        action.retrying && wasLive ? "reconnecting" : "unavailable"
      return state.connection === "reconnecting" && action.retrying
        ? state
        : { ...state, connection }
    }
  }
}

async function fetchSnapshot(signal: AbortSignal): Promise<Action | null> {
  try {
    const response = await fetch(apiUrl("/results"), {
      signal,
      cache: "no-store",
    })
    if (response.status === 503) return { type: "not-set-up" }
    if (!response.ok) return null
    return { type: "results", results: (await response.json()) as Results }
  } catch {
    return null
  }
}

export function useResults(): ResultsState {
  const [state, dispatch] = useReducer(reducer, initialState)

  useEffect(() => {
    const controller = new AbortController()
    const source = new EventSource(apiUrl("/results/stream"))

    const loadSnapshot = () => {
      void fetchSnapshot(controller.signal).then((action) => {
        if (action && !controller.signal.aborted) dispatch(action)
      })
    }

    source.onopen = () => {
      dispatch({ type: "open" })
      loadSnapshot()
    }
    source.onerror = () => {
      dispatch({
        type: "error",
        retrying: source.readyState === EventSource.CONNECTING,
      })
    }
    source.addEventListener("results", (event: MessageEvent<string>) => {
      dispatch({ type: "results", results: JSON.parse(event.data) as Results })
    })

    loadSnapshot()

    return () => {
      controller.abort()
      source.close()
    }
  }, [])

  return state
}
