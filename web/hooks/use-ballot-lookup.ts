"use client"

import { useCallback, useRef, useState } from "react"

import { fetchBallot, normalizeSectionKey, type BallotAudit } from "@/lib/audit"

export type LookupState =
  | { status: "idle" | "loading" | "invalid" | "error" }
  | { status: "missing"; section: string | null }
  | { status: "found"; ballot: BallotAudit }

export type BallotLookup = {
  state: LookupState
  search: (raw: string) => void
  draw: () => void
}

/** Looks a counted ballot up by section key, or draws a random one. Only the
 * latest request updates the state. */
export function useBallotLookup(round: number): BallotLookup {
  const [state, setState] = useState<LookupState>({ status: "idle" })
  const latest = useRef(0)

  const load = useCallback(
    async (section: string | null) => {
      const request = ++latest.current
      setState({ status: "loading" })
      const result = await fetchBallot(round, section)
      if (request !== latest.current) return
      if (result.status === "found") setState(result)
      else if (result.status === "missing")
        setState({ status: "missing", section })
      else setState({ status: "error" })
    },
    [round]
  )

  const search = useCallback(
    (raw: string) => {
      const section = normalizeSectionKey(raw)
      if (section === null) {
        latest.current++
        setState({ status: "invalid" })
        return
      }
      void load(section)
    },
    [load]
  )

  const draw = useCallback(() => void load(null), [load])

  return { state, search, draw }
}
