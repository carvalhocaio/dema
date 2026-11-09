"use client"

import { useEffect, useReducer } from "react"

import { apiUrl } from "@/lib/api"
import type { Results } from "@/lib/results"

export type Connection =
  "connecting" | "live" | "reconnecting" | "unavailable" | "final"
export type Setup = "unknown" | "ready" | "pending"

export type ResultsState = {
  results: Results | null
  connection: Connection
  setup: Setup
}

type Action =
  | { type: "results"; results: Results; connection: "live" | "final" }
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
      return {
        results: action.results,
        connection: action.connection,
        setup: "ready",
      }
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

async function fetchSnapshot(
  round: number,
  connection: "live" | "final",
  signal: AbortSignal
): Promise<Action | null> {
  try {
    const response = await fetch(apiUrl(`/rounds/${round}/results`), {
      signal,
      cache: "no-store",
    })
    if (response.status === 503) return { type: "not-set-up" }
    if (!response.ok) return null
    const results = (await response.json()) as Results
    return { type: "results", results, connection }
  } catch {
    return null
  }
}

const UNREACHABLE: Action = { type: "error", retrying: false }

export function useRoundResults(round: number, live: boolean): ResultsState {
  const [state, dispatch] = useReducer(reducer, initialState)

  useEffect(() => {
    const controller = new AbortController()
    const loadSnapshot = (connection: "live" | "final") => {
      void fetchSnapshot(round, connection, controller.signal).then(
        (action) => {
          if (controller.signal.aborted) return
          if (action) dispatch(action)
          else if (connection === "final") dispatch(UNREACHABLE)
        }
      )
    }

    if (!live) {
      loadSnapshot("final")
      return () => controller.abort()
    }

    const source = new EventSource(apiUrl(`/rounds/${round}/stream`))
    source.onopen = () => {
      dispatch({ type: "open" })
      loadSnapshot("live")
    }
    source.onerror = () => {
      dispatch({
        type: "error",
        retrying: source.readyState === EventSource.CONNECTING,
      })
    }
    source.addEventListener("results", (event: MessageEvent<string>) => {
      const results = JSON.parse(event.data) as Results
      dispatch({ type: "results", results, connection: "live" })
    })
    loadSnapshot("live")

    return () => {
      controller.abort()
      source.close()
    }
  }, [round, live])

  return state
}
